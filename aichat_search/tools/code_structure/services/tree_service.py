# aichat_search/tools/code_structure/services/tree_service.py

from typing import Dict, Any
import logging

from aichat_search.tools.code_structure.core.tree_builder import TreeBuilder
from aichat_search.tools.code_structure.models.containers import Container

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class TreeService:
    def __init__(self):
        self.tree_builder = TreeBuilder()
        self.display_root = None
