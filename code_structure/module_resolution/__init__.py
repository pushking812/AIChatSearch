# code_structure/module_resolution/__init__.py

"""
Модуль разрешения модулей и версионирования.
"""

from .core.module_identifier import ModuleIdentifier
from .services.versioned_tree_builder import VersionedTreeBuilder

__all__ = ['ModuleIdentifier', 'VersionedTreeBuilder']