import argparse
import asyncio
import base64
import concurrent.futures
from typing import Set, Dict, Any

import aiohttp_jinja2
import jinja2
import nbconvert
import nbformat
import rfc6266
from aiohttp import web
from multidict import CIMultiDict
from importlib.resources import path as resource_path
from contextlib import asynccontextmanager

app = web.Application()

aiohttp_jinja2.setup(app,
                     loader=jinja2.PackageLoader('nbconvert_http', 'jinja_templates'))

routes = web.RouteTableDef()

pool = None
TO_VERSION = 4
DISPOSITION_FIELDS = {'inline', 'attachment'}
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
TEMPLATE_PATH_FACTORY = lambda: resource_path('nbconvert_http.nbconvert_templates', 'latex_bib_template.tplx')


@asynccontextmanager
async def render_execution_context(exporter_type: str, config: dict):
    # For LaTeX exporters, we want to use the bibliography template, which needs to be written to a file
    if issubclass(nbconvert.get_exporter(exporter_type), nbconvert.LatexExporter):
        with TEMPLATE_PATH_FACTORY() as path:
            config['Exporter']['template_file'] = str(path)
            yield
    else:
        yield


def get_exporter_names() -> Set[str]:
    """Return set of valid exporter names"""
    names = set(nbconvert.get_export_names())
    names.remove('custom')
    return names


def convert_notebook_sync(data: dict, exporter_name: str, config: dict=None) -> dict:
    from . import worker
    return worker.convert_notebook(data, exporter_name, config)


def make_REST_error_response(title: str, detail: str) -> web.Response:
    """Return JSON `Response` object corresponding to an error with given title, status, and detail, according to RFC7807

    :param title: title of error
    :param detail: detailed error message
    """
    status: int = 400

    body = {
        'status': status,
        'title': title,
        'detail': detail
    }
    return web.json_response(body, status=400)


def make_web_error_response(request: web.Request, title: str, description: str) -> web.Response:
    """Return HTML `Response` object corresponding to an error with given title, and description

    :param title: title of error
    :param description: detailed error message
    """
    return aiohttp_jinja2.render_template("error.html", request, {'title': title, 'description': description})


@routes.post('/api/convert')
async def api_convert(request: web.Request) -> web.Response:
    """HTTP POST route at /api/convert for JSON nbconvert API.
    Return JSON Response with 'body', 'resources', and 'mime-type' fields.
    body field is Base64 encoded string if conversion method returned bytes
    """
    data = await request.json()

    try:
        notebook_data = data['notebook']
    except KeyError:
        return make_REST_error_response("Missing field", "Missing notebook field")

    try:
        exporter_type = data['exporter']
    except KeyError:
        return make_REST_error_response("Missing field", "Missing exporter field")

    exporter_names = get_exporter_names()
    if exporter_type not in exporter_names:
        return make_REST_error_response("Invalid field", f"Invalid exporter {exporter_type!r}, must be one of "
                                                         f"{exporter_names}")

    try:
        config = data['config']
    except KeyError:
        config = None
    else:
        if not isinstance(config, dict):
            return make_REST_error_response("Invalid field",
                                            f"Invalid config field value {config!r}, must be a dict")

    # Load notebook
    notebook = nbformat.from_dict(notebook_data)
    notebook = nbformat.convert(notebook, to_version=TO_VERSION)

    try:
        nbformat.validate(notebook)
    except nbformat.ValidationError as err:
        return make_REST_error_response("Invalid field", f"Notebook JSON invalid for version {TO_VERSION}: {err}")

    # Get notebook-json format of notebook
    major, minor = nbformat.reader.get_version(notebook)
    notebook_dict = nbformat.versions[major].to_notebook_json(notebook)

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(pool, convert_notebook_sync, notebook_dict, exporter_type, config)
    except Exception as err:
        return make_REST_error_response("Unknown error", str(err))

    json_result = result.copy()
    if isinstance(json_result['body'], bytes):
        json_result['body'] = base64.b64encode(json_result['body']).decode('utf-8')

    return web.json_response(json_result)


@routes.post('/render')
async def render(request: web.Request) -> web.Response:
    """HTTP POST route at /render for web nbconvert API.
    Return response of conversion with appropriate CONTENT-DISPOSITION
    """
    post_data = await request.post()

    try:
        notebook_field = post_data['notebook']
    except KeyError:
        return make_web_error_response(request, "Missing field", "Missing notebook [multipart file] field")

    if not notebook_field:
        return make_web_error_response(request, "Invalid field", "Notebook file multipart field empty")

    try:
        exporter_type = post_data['exporter']
    except KeyError:
        return make_web_error_response(request, "Missing field", "Missing exporter field")

    exporter_names = get_exporter_names()
    if exporter_type not in exporter_names:
        return make_web_error_response(request, "Invalid field", f"Invalid exporter {exporter_type!r}, must be one of "
                                                                 f"{exporter_names}")
    try:
        disposition = post_data['disposition']
    except KeyError:
        return make_web_error_response(request, "Missing field", "Missing disposition field")
    if disposition not in DISPOSITION_FIELDS:
        return make_web_error_response(request, "Invalid field",
                                       f"Invalid disposition {disposition!r}, must be one of {DISPOSITION_FIELDS}")

    notebook_string = notebook_field.file.read()
    notebook_data = nbformat.reads(notebook_string, TO_VERSION)

    config = {'Exporter': {'preprocessors': ['nbconvert_http.preprocessors.TagExtractPreprocessor']},
              'TagExtractPreprocessor': {'extract_cell_tags': ['bibliography']}}

    # Only need to intercept template for the HTML API
    async with render_execution_context(exporter_type, config):
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(pool, convert_notebook_sync, notebook_data, exporter_type, config)

    filename = f"result{result['resources']['output_extension']}"
    response = web.Response(body=result['body'],
                            headers=CIMultiDict({'CONTENT-DISPOSITION': rfc6266.build_header(filename, disposition)}))
    response.content_type = result['mime-type']
    return response


@routes.get('/')
@aiohttp_jinja2.template('index.html')
async def index(request: web.Request) -> Dict[str, Any]:
    """HTTP GET route at / for web nbconvert API.
    Return HTML form for conversion api.
    """
    exporters_set = set(get_exporter_names()) - {'pdf'}
    return {'exporters': ['pdf', *exporters_set]}


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, pool_context=None, **kwargs):
    """Start aiohttp server on given host and port, inside of ProcessPoolExectutor(**pool_context) context.
    """
    global pool

    if pool_context is None:
        pool_context = {}

    with concurrent.futures.ProcessPoolExecutor(**pool_context) as pool:
        web.run_app(app, host=host, port=port, **kwargs)

    pool = None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-hh', '--host', default=DEFAULT_HOST)
    parser.add_argument('-p', '--port', default=DEFAULT_PORT)
    args = parser.parse_args()

    serve(**vars(args))


app.router.add_routes(routes)

if __name__ == "__main__":
    main()
