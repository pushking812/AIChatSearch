# aichat_search/tools/code_structure/core/temp_module_merger.py

import logging
from typing import Set, Optional
from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier

logger = logging.getLogger(__name__)


class TempModuleMerger:
    """Объединяет временные модули с реальными на основе совпадающих имён классов."""

    @staticmethod
    def merge_temp_modules(identifier: ModuleIdentifier):
        """
        Находит все временные модули и пытается объединить их с реальными.
        """
        temp_modules = identifier.get_temp_modules()
        if not temp_modules:
            return

        for temp in temp_modules:
            try:
                temp_info = identifier.get_module_info(temp)
                if not temp_info:
                    continue

                # Ищем целевой модуль по пересечению имён классов
                temp_classes = set(temp_info.classes.keys())
                target = TempModuleMerger._find_target_module(identifier, temp_classes)

                if target:
                    identifier.merge_temp_module(temp, target)
                else:
                    logger.warning(f"Не найден целевой модуль для временного {temp}, пропускаем")
            except Exception as e:
                logger.error(f"Ошибка при объединении {temp}: {e}")

    @staticmethod
    def _find_target_module(identifier: ModuleIdentifier, temp_classes: Set[str]) -> Optional[str]:
        """Ищет реальный модуль, имеющий общие классы с временным."""
        for mod_name in identifier.get_all_module_names():
            if mod_name.startswith('temp_'):
                continue
            mod_info = identifier.get_module_info(mod_name)
            if not mod_info:
                continue
            real_classes = set(mod_info.classes.keys())
            if temp_classes & real_classes:
                return mod_name
        return None