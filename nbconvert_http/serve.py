import argparse
import asyncio
import concurrent.futures

import nbconvert
import rfc6266
from quart import Quart, request, make_response, render_template

app = Quart(__name__)

pool = None


def convert_notebook_sync(data, exporter_name: str):
    from . import worker
    return worker.convert_notebook(data, exporter_name)


async def convert_notebook(notebook_data, exporter_type: str, disposition: str):
    loop = asyncio.get_running_loop()

    result = await loop.run_in_executor(pool, convert_notebook_sync, notebook_data, exporter_type)

    body = result['body']
    extension = result['extension']
    mime_type = result['mime-type']

    response = await make_response(body)
    response.headers['Content-Disposition'] = rfc6266.build_header(f"result{extension}",
                                                                   disposition=disposition)
    response.headers['Content-Type'] = mime_type
    return response


@app.route('/render', methods=['post'])
async def render():
    files = await request.files
    try:
        file_storage = files['notebook']
    except KeyError:
        return await render_template("error.html", message="No file selected")

    if not file_storage:
        return await render_template("error.html", message="Empty file submitted")

    form = await request.form

    exporter_type = form['exporter']
    exporter_names = nbconvert.get_export_names()
    if exporter_type not in exporter_names:
        return await render_template("error.html", message=f"Invalid exporter {exporter_type!r}, must be one of "
                                                           f"{exporter_names}")

    notebook_data = file_storage.stream.read()
    return await convert_notebook(notebook_data, exporter_type, form['mode'])


@app.route('/', methods=['GET'])
async def index():
    exporters_set = set(nbconvert.get_export_names()) - {'pdf'}
    exporters = ['pdf', *exporters_set]
    return await render_template("index.html", exporters=exporters)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-hh', '--host', default="0.0.0.0")
    parser.add_argument('-p', '--port', default=8000)
    args = parser.parse_args()

    global pool

    with concurrent.futures.ProcessPoolExecutor() as pool:
        app.run(host=args.host, port=args.port)

    pool = None


if __name__ == "__main__":
    main()
