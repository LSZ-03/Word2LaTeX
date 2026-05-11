"""Scientific Manuscript AST — core data models for the entire pipeline.

Every node carries:
  - source_ref: traceability back to the original OOXML node
  - confidence: parsing confidence 0.0-1.0
  - warnings: known issues at this node
"""

from .manuscript import Manuscript, ManuscriptMetadata, Author
from .section import Section, Paragraph, SemanticRole, ListBlock, ListItem
from .figure import Figure
from .table import Table, TableCell, TableRow
from .equation import Equation
from .citation import Citation

__all__ = [
    "Manuscript",
    "ManuscriptMetadata",
    "Author",
    "Section",
    "Paragraph",
    "SemanticRole",
    "ListBlock",
    "ListItem",
    "Figure",
    "Table",
    "TableCell",
    "TableRow",
    "Equation",
    "Citation",
]
