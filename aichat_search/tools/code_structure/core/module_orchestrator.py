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
        # Шаг 1: Сбор идентификаторов из уже определённых модулей
        self._collect_initial_identifiers(blocks)

        # ОТЛАДКА: выводим содержимое module_ids после сбора
        logger.info("=== СОДЕРЖИМОЕ module_ids ПОСЛЕ СБОРА ===")
        module_ids = self.module_identifier.get_module_ids()
        for module_name, ids in module_ids.items():
            logger.info(f"  Модуль: {module_name}")
            logger.info(f"    Классы: {list(ids.get('classes', {}).keys())}")

            # Детально по каждому классу
            for class_name, class_info in ids.get('classes', {}).items():
                methods = [m['name'] for m in class_info.get('methods', [])]
                logger.info(f"      Класс {class_name}: методы {methods}")

            logger.info(f"    Функции: {list(ids.get('functions', {}).keys())}")

        # Шаг 2: Многопроходное определение модулей
        unknown_blocks = self._resolve_modules_iteratively(blocks)

        # Шаг 3: Группировка по модулям
        self.module_groups = self._group_blocks_by_module(blocks)

        # Шаг 4: Выбор базовых блоков
        self._select_base_blocks()

        # Шаг 5: Построение начальных структур
        self._build_initial_structures()

        # Шаг 6: Слияние остальных блоков
        self._merge_remaining_blocks()

        # Шаг 7: Объединение temp-модулей
        self._merge_temp_modules()

        return self.module_containers, unknown_blocks

    def _collect_initial_identifiers(self, blocks: List[MessageBlockInfo]):
        """Собирает идентификаторы из уже определённых модулей."""
        for block in blocks:
            if block.module_hint and block.tree and not block.syntax_error:
                self.module_identifier.collect_from_tree(block.tree, block.module_hint)

        logger.debug(f"Начальные модули: {list(self.module_identifier.get_known_modules())}")

    def _resolve_modules_iteratively(self, blocks: List[MessageBlockInfo]) -> List[MessageBlockInfo]:
        """Многопроходное определение модулей. Возвращает неопределённые блоки."""

        # ПРИНУДИТЕЛЬНО собираем идентификаторы из всех блоков, у которых уже есть module_hint
        for block in blocks:
            if block.module_hint and block.tree and not block.syntax_error:
                self.module_identifier.collect_from_tree(block.tree, block.module_hint)
                logger.info(f"Собран идентификатор из блока {block.block_id} с модулем {block.module_hint}")

        # Также собираем из блоков с классами, даже если у них нет module_hint
        for block in blocks:
            if not block.module_hint and block.tree and not block.syntax_error:
                # Проверяем наличие классов
                has_class = False
                for child in block.tree.children:
                    if child.node_type == "class":
                        has_class = True
                        break
                if has_class:
                    # Временно назначаем фиктивный модуль для сбора идентификаторов
                    temp_module = f"temp_{block.block_id}"
                    self.module_identifier.collect_from_tree(block.tree, temp_module)
                    logger.info(f"Собран идентификатор из блока {block.block_id} (временный модуль {temp_module})")

        self.module_resolver = ModuleResolver(self.module_identifier)

        # Теперь покажем, что собралось
        logger.info("=== СОДЕРЖИМОЕ module_ids ПОСЛЕ ПРИНУДИТЕЛЬНОГО СБОРА ===")
        module_ids = self.module_identifier.get_module_ids()
        for module_name, ids in module_ids.items():
            logger.info(f"  Модуль: {module_name}")
            logger.info(f"    Классы: {list(ids.get('classes', {}).keys())}")

        # Получаем все неопределённые блоки
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
        """Группирует блоки по module_hint."""
        groups = defaultdict(list)
        for block in blocks:
            if block.module_hint:
                groups[block.module_hint].append(block)
        return dict(groups)

    def _select_most_complete_block(self, blocks: List[MessageBlockInfo]) -> Optional[MessageBlockInfo]:
        """Выбирает блок с максимальным числом узлов."""
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
        """Выбирает самый полный блок для каждого модуля."""
        self.module_base_blocks = {}
        for module, blocks in self.module_groups.items():
            base = self._select_most_complete_block(blocks)
            if base:
                self.module_base_blocks[module] = base
                logger.debug(f"Базовый блок для {module}: {base.block_id}")

    def _build_initial_structures(self):
        """Строит начальные структуры из базовых блоков."""
        for module_name, base_block in self.module_base_blocks.items():
            container = self.structure_builder.build_initial_structure(module_name, base_block)
            self.module_containers[module_name] = container

    def _merge_remaining_blocks(self):
        """Сливает остальные блоки в структуры."""
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
        temp_modules = [m for m in module_ids.keys() if m.startswith('temp_')]

        if not temp_modules:
            logger.info("Нет temp-модулей для объединения")
            return

        # Для каждого temp-модуля ищем соответствующий реальный модуль
        for temp_module in temp_modules:
            # Получаем идентификаторы из temp-модуля
            temp_data = module_ids[temp_module]

            # Ищем реальный модуль с таким же классом
            target_module = None
            for class_name in temp_data.get('classes', {}).keys():
                for real_module, real_data in module_ids.items():
                    if real_module.startswith('temp_'):
                        continue
                    if class_name in real_data.get('classes', {}):
                        target_module = real_module
                        logger.info(f"Класс {class_name} из {temp_module} найден в {target_module}")
                        break
                if target_module:
                    break

            if not target_module:
                logger.warning(f"Не найден реальный модуль для {temp_module}, пропускаем")
                continue

            # Переносим методы из temp-модуля в реальный
            for method_key, method_list in temp_data.get('methods', {}).items():
                for method_info in method_list:
                    # Добавляем метод в реальный модуль
                    if method_info['name'] not in self.module_identifier.module_ids[target_module]['methods']:
                        self.module_identifier.module_ids[target_module]['methods'][method_info['name']] = []
                    self.module_identifier.module_ids[target_module]['methods'][method_info['name']].append(method_info)

                    # Также добавляем метод в класс
                    if method_info['class'] in self.module_identifier.module_ids[target_module]['classes']:
                        class_info = self.module_identifier.module_ids[target_module]['classes'][method_info['class']]
                        if 'methods' not in class_info:
                            class_info['methods'] = []
                        # Проверяем, нет ли уже такого метода
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

            logger.info(f"Перенесены методы из {temp_module} в {target_module}")

        # Удаляем temp-модули
        for temp_module in temp_modules:
            if temp_module in self.module_identifier.module_ids:
                del self.module_identifier.module_ids[temp_module]
                logger.info(f"Удалён temp-модуль {temp_module}")