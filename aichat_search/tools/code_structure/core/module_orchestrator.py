# aichat_search/tools/code_structure/core/module_orchestrator.py

"""Оркестратор процесса определения модулей и слияния."""

import logging
import re
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.models.containers import Container
from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier
from aichat_search.tools.code_structure.core.module_resolver import ModuleResolver
from aichat_search.tools.code_structure.core.structure_builder import StructureBuilder

logger = logging.getLogger(__name__)


class ModuleOrchestrator:
    def __init__(self):
        self.module_identifier = ModuleIdentifier()
        self.module_resolver = None
        self.structure_builder = StructureBuilder()
        self.module_groups: Dict[str, List[MessageBlockInfo]] = {}
        self.module_base_blocks: Dict[str, MessageBlockInfo] = {}
        self.module_containers: Dict[str, Container] = {}
        self.assignment_stats: Dict[str, Tuple[str, None]] = {}
        self.temp_modules: List[str] = []
        self.error_blocks: List[MessageBlockInfo] = []

    def process_blocks(self, blocks: List[MessageBlockInfo]) -> Tuple[Dict[str, Container], List[MessageBlockInfo]]:
        logger.info("=== process_blocks: НАЧАЛО ===")
        self._reset_state()
        valid_blocks, error_blocks = self._separate_error_blocks(blocks)
        self.error_blocks = error_blocks
        logger.info(f"Блоков с ошибками: {len(error_blocks)}")

        self._collect_initial_identifiers(valid_blocks)
        unknown_blocks = self._resolve_modules_iteratively(valid_blocks)
        self.module_groups = self._group_blocks_by_module(valid_blocks)
        self._select_base_blocks()
        self._build_initial_structures()
        self._merge_remaining_blocks()
        self._merge_temp_modules()

        # Сохраняем unknown_blocks для логирования
        self.unknown_blocks = unknown_blocks
        # Логируем результат
        self.log_analysis_result()

        return self.module_containers, unknown_blocks + error_blocks

    def _reset_state(self):
        self.module_groups.clear()
        self.module_base_blocks.clear()
        self.module_containers.clear()
        self.assignment_stats.clear()
        self.temp_modules.clear()
        self.error_blocks.clear()

    def _separate_error_blocks(self, blocks):
        valid, errors = [], []
        for b in blocks:
            if b.syntax_error or b.tree is None:
                errors.append(b)
            else:
                valid.append(b)
        return valid, errors

    def _collect_initial_identifiers(self, blocks):
        for b in blocks:
            if b.module_hint and b.tree and not b.syntax_error:
                self.module_identifier.collect_from_tree(b.tree, b.module_hint)

    def _block_has_imports(self, content):
        import_patterns = [
            r'^import\s+\w+',
            r'^from\s+\w+\s+import',
        ]
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            for pattern in import_patterns:
                if re.match(pattern, line):
                    return True
        return False

    def _get_block_priority(self, block: MessageBlockInfo) -> int:
        """
        Возвращает приоритет блока для сортировки внутри модуля.
        Чем меньше число, тем раньше должен обрабатываться блок.
        """
        if not block.tree or block.syntax_error:
            return 999  # ошибочные блоки в конец

        has_classes = self._block_has_classes(block)
        has_imports = self._block_has_imports(block.content)

        if has_classes:
            return 1  # классы - наивысший приоритет
        elif has_imports:
            return 2  # импорты - следующий приоритет
        elif block.module_hint:
            return 3  # module_hint без классов/импортов
        else:
            return 4  # всё остальное

    def _sort_blocks_for_module(self, blocks: List[MessageBlockInfo]) -> List[MessageBlockInfo]:
        """
        Сортирует блоки внутри модуля по приоритету, а внутри одинакового приоритета - по global_index.
        Возвращает отсортированный список и присваивает каждому блоку module_order.
        """
        sorted_blocks = sorted(blocks,
                              key=lambda b: (self._get_block_priority(b), b.global_index))

        for order, block in enumerate(sorted_blocks, 1):
            if block.metadata is None:
                block.metadata = {}
            block.metadata['module_order'] = order

        return sorted_blocks

    def _resolve_modules_iteratively(self, blocks):
        for b in blocks:
            if b.module_hint and b.tree and not b.syntax_error:
                self.module_identifier.collect_from_tree(b.tree, b.module_hint)

        self.module_resolver = ModuleResolver(self.module_identifier)

        # Разделяем блоки на категории
        group_classes_with_hint = []   # есть классы и module_hint
        group_imports_with_hint = []   # нет классов, есть импорты и module_hint
        group_classes_only = []         # есть классы, нет module_hint
        group_imports_only = []         # нет классов, есть импорты, нет module_hint
        group_neither = []              # нет ничего

        for b in blocks:
            if not b.tree or b.syntax_error:
                continue
            has_classes = self._block_has_classes(b)
            has_imports = self._block_has_imports(b.content)

            if has_classes and b.module_hint:
                group_classes_with_hint.append(b)
            elif not has_classes and has_imports and b.module_hint:
                group_imports_with_hint.append(b)
            elif has_classes and not b.module_hint:
                group_classes_only.append(b)
            elif not has_classes and has_imports and not b.module_hint:
                group_imports_only.append(b)
            else:
                group_neither.append(b)

        self.assignment_stats.clear()
        self.temp_modules.clear()

        def process_group(group):
            unknown = group[:]
            iteration = 1
            while unknown:
                newly = []
                still = []
                for block in unknown:
                    resolved, module, _ = self.module_resolver.resolve_block(block)
                    if resolved:
                        block.module_hint = module
                        self.module_identifier.collect_from_tree(block.tree, module)
                        newly.append(block)
                        self.assignment_stats[block.block_id] = (module, None)
                    else:
                        still.append(block)
                if not newly:
                    break
                unknown = still
                iteration += 1
            return unknown

        # 1. Блоки с классами и module_hint
        logger.debug("Обработка группы 1 (классы + module_hint)")
        unknown1 = process_group(group_classes_with_hint)

        # 2. Блоки с импортами и module_hint
        logger.debug("Обработка группы 2 (импорты + module_hint)")
        unknown2 = process_group(group_imports_with_hint)

        # 3. Блоки только с классами
        logger.debug("Обработка группы 3 (только классы)")
        unknown3 = process_group(group_classes_only)

        # 4. Создаём временные модули для неразрешённых блоков с классами
        for block in unknown1 + unknown3:
            if self._block_has_classes(block):
                temp = f"temp_{block.block_id}"
                block.module_hint = temp
                self.module_identifier.collect_from_tree(block.tree, temp)
                self.temp_modules.append(temp)

        # 5. Блоки только с импортами
        logger.debug("Обработка группы 4 (только импорты)")
        unknown4 = process_group(group_imports_only)

        # 6. Блоки без всего
        logger.debug("Обработка группы 5 (без информации)")
        unknown5 = process_group(group_neither)

        final_unknown = unknown2 + unknown4 + unknown5

        logger.info(f"Определено модулей: {len(self.assignment_stats)}")
        logger.info(f"Временных модулей: {len(self.temp_modules)}")
        logger.info(f"Неопределено: {len(final_unknown)}")
        return final_unknown

    def _block_has_classes(self, block):
        if not block.tree:
            return False
        for child in block.tree.children:
            if child.node_type == "class":
                return True
        return False

    def _group_blocks_by_module(self, blocks):
        groups = defaultdict(list)
        for b in blocks:
            if b.module_hint:
                groups[b.module_hint].append(b)
        return dict(groups)

    def _select_most_complete_block(self, blocks: List[MessageBlockInfo]) -> Optional[MessageBlockInfo]:
        if not blocks:
            return None
        best = None
        best_cnt = -1
        best_idx = float('inf')
        for block in blocks:
            if block.tree is None or block.syntax_error:
                continue
            count = block.tree.count_nodes()
            if count > best_cnt or (count == best_cnt and block.global_index < best_idx):
                best_cnt = count
                best_idx = block.global_index
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
        """Строит начальные структуры для каждого модуля, используя отсортированные блоки."""
        for module_name, base_block in self.module_base_blocks.items():
            # Получаем все блоки модуля и сортируем их
            all_blocks = self.module_groups.get(module_name, [])
            sorted_blocks = self._sort_blocks_for_module(all_blocks)

            # Строим структуру с учётом сортировки
            container = self.structure_builder.build_initial_structure(
                module_name, base_block, sorted_blocks
            )
            self.module_containers[module_name] = container

    def _merge_remaining_blocks(self):
        """Сливает оставшиеся блоки в существующие контейнеры."""
        for module_name, container in self.module_containers.items():
            base = self.module_base_blocks.get(module_name)
            if not base:
                continue

            # Получаем все блоки модуля (уже отсортированные)
            all_blocks = self.module_groups.get(module_name, [])
            # Блоки уже отсортированы в _build_initial_structures, но на всякий случай пересортируем
            sorted_blocks = self._sort_blocks_for_module(all_blocks)

            others = [b for b in sorted_blocks if b is not base]

            for block in others:
                if block.tree and not block.syntax_error:
                    try:
                        self.structure_builder.merge_node_into_container(
                            block.tree, container, block
                        )
                    except Exception as e:
                        logger.error(f"Ошибка при слиянии блока {block.block_id} в модуль {module_name}: {e}", exc_info=True)

    def _merge_temp_modules(self):
        """Объединяет временные модули с реальными на основе совпадающих имён классов."""
        logger.info("=== Объединение temp-модулей ===")
        temp_modules = self.module_identifier.get_temp_modules()
        if not temp_modules:
            return

        for temp in temp_modules:
            try:
                temp_info = self.module_identifier.get_module_info(temp)
                if not temp_info:
                    continue

                # Ищем целевой модуль по пересечению имён классов
                temp_classes = set(temp_info.classes.keys())
                target = None
                for mod_name in self.module_identifier.get_all_module_names():
                    if mod_name.startswith('temp_'):
                        continue
                    mod_info = self.module_identifier.get_module_info(mod_name)
                    if not mod_info:
                        continue
                    real_classes = set(mod_info.classes.keys())
                    if temp_classes & real_classes:
                        target = mod_name
                        break

                if target:
                    self.module_identifier.merge_temp_module(temp, target)
                else:
                    logger.warning(f"Не найден целевой модуль для временного {temp}, пропускаем")
            except Exception as e:
                logger.error(f"Ошибка при объединении {temp}: {e}")

    def _log_module_tree(self, module_name: str, container: Container, level: int = 0, order: int = 0):
        """Рекурсивно логирует структуру контейнера с порядковым номером обработки."""
        indent = "  " * level
        version_info = f" (версий: {len(container.versions)})" if container.versions else ""
        sources_info = ""
        if container.versions and container.versions[0].sources:
            sources = ", ".join([f"{src[0]}:{src[1]}-{src[2]}" for src in container.versions[0].sources[:2]])
            if len(container.versions[0].sources) > 2:
                sources += f" и ещё {len(container.versions[0].sources)-2}"
            sources_info = f" [{sources}]"

        # Добавляем порядковый номер обработки
        order_info = f"[#{order}]" if order else ""
        logger.info(f"{indent}• {container.name} {order_info}({container.node_type}){version_info}{sources_info}")

        for i, child in enumerate(container.children, 1):
            self._log_module_tree(module_name, child, level + 1, i)

    def log_analysis_result(self):
        """Выводит в лог итоговую структуру модулей с порядковыми номерами."""
        logger.info("=" * 60)
        logger.info("ИТОГОВАЯ СТРУКТУРА МОДУЛЕЙ (с порядком обработки)")
        logger.info("=" * 60)

        for module_name, container in self.module_containers.items():
            logger.info(f"\n📦 {module_name}")
            blocks = self.module_groups.get(module_name, [])
            logger.info(f"   Блоков: {len(blocks)}")
            self._log_module_tree(module_name, container, 1, 1)

        if self.temp_modules:
            logger.info(f"\n⚠️ Временные модули: {', '.join(self.temp_modules)}")

        total_blocks = len(self.assignment_stats) + sum(len(g) for g in self.module_groups.values())
        logger.info("=" * 60)
        logger.info(f"Всего модулей: {len(self.module_containers)}")
        logger.info(f"Всего блоков: {total_blocks}")
        logger.info(f"Неопределено: {len(getattr(self, 'unknown_blocks', []))}")
        logger.info("=" * 60)

    # Вспомогательные методы для получения информации
    def get_blocks_for_module(self, module_name: str) -> List[MessageBlockInfo]:
        return self.module_groups.get(module_name, [])

    def get_module_containers(self) -> Dict[str, Container]:
        return self.module_containers.copy()

    def get_temp_modules(self) -> List[str]:
        return self.temp_modules.copy()

    def get_error_blocks(self) -> List[MessageBlockInfo]:
        return self.error_blocks.copy()

    def clear_temp_data(self):
        self.temp_modules.clear()
        self.assignment_stats.clear()
        self.module_identifier.remove_temp_modules()