import pathlib

import nbconvert
import nbformat
import rfc6266
from quart import Quart, request, make_response
from traitlets.config import Config

app = Quart(__name__)

MESSAGE_HTML_STYLE = """
<style>
@import url('//maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css');
 
.isa_info, .isa_success, .isa_warning, .isa_error {
margin: 10px 0px;
padding:12px;
 
}
.isa_info {
    color: #00529B;
    background-color: #BDE5F8;
}
.isa_success {
    color: #4F8A10;
    background-color: #DFF2BF;
}
.isa_warning {
    color: #9F6000;
    background-color: #FEEFB3;
}
.isa_error {
    color: #D8000C;
    background-color: #FFD2D2;
}
.isa_info i, .isa_success i, .isa_warning i, .isa_error i {
    margin:10px 22px;
    font-size:2em;
    vertical-align:middle;
}
</style>
"""

MESSAGE_HTML_ERROR_TEMPLATE = """
<div class="isa_error">
   <i class="fa fa-times-circle"></i>
   {error}
</div>
"""

MIME_RESPONSES = [(nbconvert.PDFExporter, 'application/pdf')]


def get_mime_response(exporter: nbconvert.Exporter) -> str:
    for cls, mime_type in MIME_RESPONSES:
        if isinstance(exporter, cls):
            return mime_type
    return exporter.output_mimetype


def error_response(error):
    return MESSAGE_HTML_STYLE + MESSAGE_HTML_ERROR_TEMPLATE.format(error=error)


async def convert_notebook(data, exporter):
    notebook = nbformat.reads(data, as_version=4)

    ep = nbconvert.preprocessors.ExecutePreprocessor(timeout=600, kernel_name='python3')
    ep.preprocess(notebook)

    body, resources = exporter.from_notebook_node(notebook)

    response = await make_response(body)
    response.headers['Content-Disposition'] = rfc6266.build_header(f"result{resources['output_extension']}",
                                                                   disposition='inline')
    response.headers['Content-Type'] = get_mime_response(exporter)
    return response


@app.route('/render', methods=['post', 'get'])
async def render():
    path = pathlib.Path("/home/angus/Documents/Jupyter Demo/ODEs.ipynb")
    data = path.read_text()

    output_type = request.args.get('output', 'pdf')
    try:
        exporter_cls = nbconvert.get_exporter(output_type)
    except ValueError:
        return error_response(
            f"Invalid exporter {output_type!r}, must be one of {nbconvert.exporters.get_export_names()}")

    # Configure exporter to strip bibliography
    c = Config()
    setattr(c, "f{exporter_cls.__name__}.preprocessors", ['nbconvert.preprocessors.TagRemovePreprocessor'])
    c.TagRemovePreprocessor.remove_cell_tags = {'bibliography'}

    exporter: nbconvert.Exporter = exporter_cls(config=c)

    if isinstance(exporter, nbconvert.LatexExporter):
        exporter.template_file = "/home/angus/PycharmProjects/api/template.tplx"#str(pathlib.Path(__file__).parent / "template.tplx")
        print("SET TEMPLATE",exporter.template_path)

    return await convert_notebook(data, exporter)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
