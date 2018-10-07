import nbconvert
from traitlets import Set, Unicode


class TagExtractPreprocessor(nbconvert.preprocessors.Preprocessor):

    extract_cell_tags = Set(Unicode(), default_value=[],
                            help=("Tags indicating which cells are to be removed,"
                                 "matches tags in `cell.metadata.tags`.")).tag(config=True)

    def find_matching_tags(self, cell):
        return self.extract_cell_tags.intersection(
            cell.get('metadata', {}).get('tags', []))

    def preprocess(self, nb, resources):
        if not self.extract_cell_tags:
            return nb, resources

        # Filter out cells that meet the conditions
        new_cells = []
        extracted_by_tag = resources.setdefault('extracted_by_tag', {})

        for cell in nb.cells:
            tags = self.find_matching_tags(cell)
            if tags:
                for tag in tags:
                    extracted_by_tag.setdefault(tag, []).append(cell['source'])
            else:
                new_cells.append(cell)

        nb.cells = new_cells
        return nb, resources