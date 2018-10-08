import nbconvert
import nbformat
from traitlets.config import Config

MIME_RESPONSES = [(nbconvert.PDFExporter, 'application/pdf')]


def get_mime_response(exporter: nbconvert.Exporter) -> str:
    for cls, mime_type in MIME_RESPONSES:
        if isinstance(exporter, cls):
            return mime_type
    return exporter.output_mimetype


def create_exporter(exporter_type: str, config: dict=None) -> nbconvert.Exporter:
    if config is None:
        config = {}

    # Configure exporter to strip bibliography
    c = Config(**config)

    # Create exporter
    return nbconvert.get_exporter(exporter_type)(config=c)


def convert_notebook(notebook_data: dict, exporter_type: str, config: dict=None) -> dict:
    notebook = nbformat.from_dict(notebook_data)

    exporter = create_exporter(exporter_type, config)
    body, resources = exporter.from_notebook_node(notebook)

    return {'body': body,
            'mime-type': get_mime_response(exporter),
            'resources': resources}
