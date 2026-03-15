# aichat_search/tools/code_structure/core/module_orchestrator.py

"""Оркестратор процесса определения модулей и слияния."""

import logging
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict

from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.models.containers import Container
from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier
from aichat_search.tools.code_structure.core.module_resolver import ModuleResolver
from aichat_search.tools.code_structure.core.structure_builder import StructureBuilder

logger = logging.getLogger(__name__)


class ModuleOrchestrator:
    """
    Координирует процесс определения модулей, построения структур и слияния.
    """

    def __init__(self):
        self.module_identifier = ModuleIdentifier()
        self.module_resolver = None
        self.structure_builder = StructureBuilder()

        # Результаты работы
        self.module_groups: Dict[str, List[MessageBlockInfo]] = {}
        self.module_base_blocks: Dict[str, MessageBlockInfo] = {}
        self.module_containers: Dict[str, Container] = {}

    def process_blocks(self, blocks: List[MessageBlockInfo]) -> Tuple[Dict[str, Container], List[MessageBlockInfo]]:
        """
        Основной метод обработки блоков.
        Возвращает (контейнеры_модулей, неопределённые_блоки)
        """
        logger.info("=== process_blocks: НАЧАЛО ===")
        try:
            logger.info("Шаг 1: _collect_initial_identifiers")
            self._collect_initial_identifiers(blocks)

            logger.info("Шаг 2: _resolve_modules_iteratively")
            unknown_blocks = self._resolve_modules_iteratively(blocks)

            logger.info("Шаг 3: _group_blocks_by_module")
            self.module_groups = self._group_blocks_by_module(blocks)

            logger.info("Шаг 4: _select_base_blocks")
            self._select_base_blocks()

            logger.info("Шаг 5: _build_initial_structures")
            self._build_initial_structures()

            logger.info("Шаг 6: _merge_remaining_blocks")
            self._merge_remaining_blocks()

            logger.info("Шаг 7: _merge_temp_modules")
            self._merge_temp_modules()

            logger.info("Шаг 8: возврат результата")
            return self.module_containers, unknown_blocks

        except Exception as e:
            logger.exception(f"КРИТИЧЕСКАЯ ОШИБКА в process_blocks: {e}")
            raise

    def resolve_blocks(self, blocks: List[MessageBlockInfo]) -> List[MessageBlockInfo]:
        """
        Пытается определить модули для заданного списка блоков.
        Возвращает неопределённые блоки.
        """
        if not blocks:
            return []

        self.module_resolver = ModuleResolver(self.module_identifier)
        unknown = blocks.copy()
        iteration = 1
        while unknown:
            logger.info(f"resolve_blocks проход #{iteration}, осталось: {len(unknown)}")
            newly = []
            still = []
            for block in unknown:
                resolved, name = self.module_resolver.resolve_block(block)
                if resolved:
                    block.module_hint = name
                    self.module_identifier.collect_from_tree(block.tree, name)
                    newly.append(block)
                else:
                    still.append(block)
            if not newly:
                break
            unknown = still
            iteration += 1
        return unknown

    def _collect_initial_identifiers(self, blocks: List[MessageBlockInfo]):
        """Собирает идентификаторы из уже определённых модулей."""
        for block in blocks:
            if block.module_hint and block.tree and not block.syntax_error:
                self.module_identifier.collect_from_tree(block.tree, block.module_hint)
        logger.debug(f"Начальные модули: {list(self.module_identifier.get_known_modules())}")

    def _resolve_modules_iteratively(self, blocks: List[MessageBlockInfo]) -> List[MessageBlockInfo]:
        """Многопроходное определение модулей. Возвращает неопределённые блоки."""
        # Принудительно собираем идентификаторы из уже определённых модулей
        for block in blocks:
            if block.module_hint and block.tree and not block.syntax_error:
                self.module_identifier.collect_from_tree(block.tree, block.module_hint)
                logger.info(f"Собран идентификатор из блока {block.block_id} с модулем {block.module_hint}")

        # Собираем из блоков с классами (временно)
        for block in blocks:
            if not block.module_hint and block.tree and not block.syntax_error:
                has_class = False
                for child in block.tree.children:
                    if child.node_type == "class":
                        has_class = True
                        break
                if has_class:
                    temp_module = f"temp_{block.block_id}"
                    self.module_identifier.collect_from_tree(block.tree, temp_module)
                    logger.info(f"Собран идентификатор из блока {block.block_id} (временный модуль {temp_module})")

        self.module_resolver = ModuleResolver(self.module_identifier)

        unknown = [b for b in blocks if not b.module_hint and b.tree and not b.syntax_error]
        iteration = 1

        while unknown:
            logger.info(f"Проход определения модулей #{iteration}, осталось: {len(unknown)}")
            newly_assigned = []
            still_unknown = []

            for block in unknown:
                resolved, module_name = self.module_resolver.resolve_block(block)
                if resolved:
                    block.module_hint = module_name
                    self.module_identifier.collect_from_tree(block.tree, module_name)
                    newly_assigned.append(block)
                    logger.debug(f"  {block.block_id} -> {module_name}")
                else:
                    still_unknown.append(block)

            if not newly_assigned:
                logger.info("Новых назначений нет, завершаем")
                break

            unknown = still_unknown
            iteration += 1

        return unknown

    def _group_blocks_by_module(self, blocks: List[MessageBlockInfo]) -> Dict[str, List[MessageBlockInfo]]:
        groups = defaultdict(list)
        for block in blocks:
            if block.module_hint:
                groups[block.module_hint].append(block)
        return dict(groups)

    def _select_most_complete_block(self, blocks: List[MessageBlockInfo]) -> Optional[MessageBlockInfo]:
        if not blocks:
            return None
        best = None
        best_count = -1
        best_index = float('inf')
        for block in blocks:
            if block.tree is None or block.syntax_error:
                continue
            count = block.tree.count_nodes()
            if count > best_count or (count == best_count and block.global_index < best_index):
                best_count = count
                best_index = block.global_index
                best = block
        return best

    def _select_base_blocks(self):
        self.module_base_blocks = {}
        for module, blocks in self.module_groups.items():
            base = self._select_most_complete_block(blocks)
            if base:
                self.module_base_blocks[module] = base
                logger.debug(f"Базовый блок для {module}: {base.block_id}")

    def _build_initial_structures(self):
        for module_name, base_block in self.module_base_blocks.items():
            container = self.structure_builder.build_initial_structure(module_name, base_block)
            self.module_containers[module_name] = container

    def _merge_remaining_blocks(self):
        for module_name, container in self.module_containers.items():
            base = self.module_base_blocks.get(module_name)
            if not base:
                continue
            other = [b for b in self.module_groups.get(module_name, []) if b is not base]
            other.sort(key=lambda b: b.global_index)
            for block in other:
                if block.tree and not block.syntax_error:
                    self.structure_builder.merge_node_into_container(block.tree, container, block)

    def _merge_temp_modules(self):
        """Переносит идентификаторы из temp-модулей в реальные модули."""
        logger.info("=== Объединение temp-модулей ===")

        module_ids = self.module_identifier.get_module_ids()
        logger.info(f"Все модули перед объединением: {list(module_ids.keys())}")

        temp_modules = [m for m in module_ids.keys() if m.startswith('temp_')]
        logger.info(f"Найдено temp-модулей: {temp_modules}")

        if not temp_modules:
            logger.info("Нет temp-модулей для объединения")
            return

        for temp_module in temp_modules:
            logger.info(f"Обработка temp-модуля: {temp_module}")
            temp_data = module_ids[temp_module]

            temp_classes = list(temp_data.get('classes', {}).keys())
            logger.info(f"  Классы в temp-модуле: {temp_classes}")

            # Нормализуем имена классов
            temp_classes_norm = [c.strip().lower() for c in temp_classes]

            target_module = None
            for real_module, real_data in module_ids.items():
                if real_module.startswith('temp_'):
                    continue
                real_classes = list(real_data.get('classes', {}).keys())
                real_classes_norm = [c.strip().lower() for c in real_classes]
                common = set(temp_classes_norm) & set(real_classes_norm)
                if common:
                    target_module = real_module
                    logger.info(f"  Найден реальный модуль {target_module} с общими классами {common}")
                    break

            if not target_module:
                logger.warning(f"  Не найден реальный модуль для {temp_module}, пропускаем")
                continue

            # Перенос методов
            for method_key, method_list in temp_data.get('methods', {}).items():
                for method_info in method_list:
                    # Добавляем в общий список методов
                    if method_info['name'] not in self.module_identifier.module_ids[target_module]['methods']:
                        self.module_identifier.module_ids[target_module]['methods'][method_info['name']] = []
                    self.module_identifier.module_ids[target_module]['methods'][method_info['name']].append(method_info)

                    # Добавляем в класс
                    class_name = method_info['class']
                    found_class = None
                    for real_class in self.module_identifier.module_ids[target_module]['classes']:
                        if real_class.strip().lower() == class_name.strip().lower():
                            found_class = real_class
                            break
                    if found_class:
                        class_info = self.module_identifier.module_ids[target_module]['classes'][found_class]
                        if 'methods' not in class_info:
                            class_info['methods'] = []
                        method_exists = False
                        for m in class_info['methods']:
                            if m['name'] == method_info['name']:
                                method_exists = True
                                break
                        if not method_exists:
                            class_info['methods'].append({
                                'name': method_info['name'],
                                'signature': method_info['signature']
                            })
                    else:
                        logger.warning(f"    Класс {class_name} не найден в реальном модуле {target_module}")

            logger.info(f"  Перенесены методы из {temp_module} в {target_module}")

        # Удаляем temp-модули
        for temp_module in temp_modules:
            if temp_module in self.module_identifier.module_ids:
                del self.module_identifier.module_ids[temp_module]
                logger.info(f"  Удалён temp-модуль {temp_module}")