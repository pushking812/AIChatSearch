# aichat_search/tools/code_structure/services/import_service.py

from typing import List, Dict
import logging

from aichat_search.tools.code_structure.imports.core.import_analyzer import (
    build_imported_items,
    build_imported_items_by_module
)
from aichat_search.tools.code_structure.imports.models.import_models import ImportInfo
from aichat_search.tools.code_structure.module_resolution.models.block_info import MessageBlockInfo

from aichat_search.tools.code_structure.utils.logger import get_logger
logger = get_logger(__name__, level = logging.WARNING)


class ImportService:
    """Сервис для работы с импортами."""

    def __init__(self):
        pass

    def get_imported_items(self, blocks: List[MessageBlockInfo]) -> Dict[str, str]:
        if not blocks:
            return {}
        logger.info(f"Анализ импортов для {len(blocks)} блоков")
        items = build_imported_items(blocks)
        logger.info(f"Найдено {len(items)} импортированных объектов")
        return items

    def get_imported_items_by_module(self, blocks: List[MessageBlockInfo]) -> Dict[str, List[ImportInfo]]:
        if not blocks:
            return {}
        logger.info(f"Сбор импортов по модулям для {len(blocks)} блоков")
        items = build_imported_items_by_module(blocks)
        logger.info(f"Найдено {len(items)} модулей-источников с импортами")
        return items