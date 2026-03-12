# aichat_search/tools/code_structure/services/__init__.py

from .block_manager import BlockManager
from ..parser import PythonParser, PARSERS
# block_parser остаётся на месте, его не перемещаем

__all__ = ['BlockManager', 'PythonParser', 'PARSERS']