"""Collect inflect with its Python source files on disk, not only in the archive.

XTTS spells out numbers with inflect, whose functions are wrapped by typeguard's
@typechecked; typeguard reads each function's source when the module is imported.
"""

module_collection_mode = "pyz+py"
