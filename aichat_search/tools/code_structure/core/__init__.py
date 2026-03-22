# aichat_search/tools/code_structure/core/__init__.py

"""Core modules for code structure analysis and merging."""

from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier
from aichat_search.tools.code_structure.core.module_resolver import ModuleResolver
from aichat_search.tools.code_structure.core.structure_builder import StructureBuilder
from aichat_search.tools.code_structure.core.signature_utils import (
    extract_function_signature,
    compare_signatures,
    are_signatures_similar,
    detect_method_likelihood,
    get_param_count,
    has_self_param,
    signature_to_string,
    normalize_signature
)
from aichat_search.tools.code_structure.core.import_analyzer import (
    extract_imports_from_block,
    build_imported_items,
    build_imported_items_by_module
)
from aichat_search.tools.code_structure.core.project_tree_builder import ProjectTreeBuilder

__all__ = [
    'ModuleIdentifier',
    'ModuleResolver',
    'StructureBuilder',
    'extract_function_signature',
    'compare_signatures',
    'are_signatures_similar',
    'detect_method_likelihood',
    'get_param_count',
    'has_self_param',
    'signature_to_string',
    'normalize_signature',
    'extract_imports_from_block',
    'build_imported_items',
    'build_imported_items_by_module',
    'ProjectTreeBuilder'
]