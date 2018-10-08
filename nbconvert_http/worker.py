import nbconvert
import nbformat
from traitlets.config import Config
from importlib.resources import path as resource_path
import contextlib

MIME_RESPONSES = [(nbconvert.PDFExporter, 'application/pdf')]
TEMPLATE_PATH = resource_path('nbconvert_http.nbconvert_templates', 'latex_bib_template.tplx')


def get_mime_response(exporter: nbconvert.Exporter) -> str:
    for cls, mime_type in MIME_RESPONSES:
        if isinstance(exporter, cls):
            return mime_type
    return exporter.output_mimetype


@contextlib.contextmanager
def create_exporter(exporter_type: str) -> nbconvert.Exporter:
    # Configure exporter to strip bibliography
    c = Config()
    c.Exporter.preprocessors = ['nbconvert_http.preprocessors.TagExtractPreprocessor']
    c.TagExtractPreprocessor.extract_cell_tags = {'bibliography'}

    # Create exporter
    exporter: nbconvert.Exporter = nbconvert.get_exporter(exporter_type)(config=c)
    with TEMPLATE_PATH as path:
        if isinstance(exporter, nbconvert.LatexExporter):
            exporter.template_file = str(path)
        yield exporter


def convert_notebook(notebook_data: dict, exporter_type: str) -> dict:
    notebook = nbformat.from_dict(notebook_data)

    with create_exporter(exporter_type) as exporter:
        body, resources = exporter.from_notebook_node(notebook)
    return {'body': body,
            'mime-type': get_mime_response(exporter),
            'resources': resources}
