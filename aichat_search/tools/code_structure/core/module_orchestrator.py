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
from aichat_search.tools.code_structure.core.match_score import MatchScore

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
        
        # Статистика определений
        self.assignment_stats: Dict[str, Tuple[str, MatchScore]] = {}  # block_id -> (module_name, score)
        
        # Временные модули
        self.temp_modules: List[str] = []
        
        # Блоки с ошибками
        self.error_blocks: List[MessageBlockInfo] = []

    def process_blocks(self, blocks: List[MessageBlockInfo]) -> Tuple[Dict[str, Container], List[MessageBlockInfo]]:
        """
        Основной метод обработки блоков.
        Возвращает (контейнеры_модулей, неопределённые_блоки)
        """
        logger.info("=== process_blocks: НАЧАЛО ===")
        
        # Сбрасываем состояние
        self._reset_state()
        
        try:
            # Отделяем блоки с ошибками
            valid_blocks, error_blocks = self._separate_error_blocks(blocks)
            self.error_blocks = error_blocks
            logger.info(f"Блоков с ошибками: {len(error_blocks)}")

            logger.info("Шаг 1: _collect_initial_identifiers")
            self._collect_initial_identifiers(valid_blocks)

            logger.info("Шаг 2: _resolve_modules_iteratively")
            unknown_blocks = self._resolve_modules_iteratively(valid_blocks)

            logger.info("Шаг 3: _group_blocks_by_module")
            self.module_groups = self._group_blocks_by_module(valid_blocks)

            logger.info("Шаг 4: _select_base_blocks")
            self._select_base_blocks()

            logger.info("Шаг 5: _build_initial_structures")
            self._build_initial_structures()

            logger.info("Шаг 6: _merge_remaining_blocks")
            self._merge_remaining_blocks()

            logger.info("Шаг 7: _merge_temp_modules")
            self._merge_temp_modules()

            logger.info("Шаг 8: возврат результата")
            return self.module_containers, unknown_blocks + error_blocks

        except Exception as e:
            logger.exception(f"КРИТИЧЕСКАЯ ОШИБКА в process_blocks: {e}")
            raise

    def _reset_state(self):
        """Сбрасывает состояние оркестратора."""
        self.module_groups.clear()
        self.module_base_blocks.clear()
        self.module_containers.clear()
        self.assignment_stats.clear()
        self.temp_modules.clear()
        self.error_blocks.clear()

    def _separate_error_blocks(self, blocks: List[MessageBlockInfo]) -> Tuple[List[MessageBlockInfo], List[MessageBlockInfo]]:
        """Отделяет блоки с ошибками от валидных."""
        valid = []
        errors = []
        for block in blocks:
            if block.syntax_error or block.tree is None:
                errors.append(block)
            else:
                valid.append(block)
        return valid, errors

    def _collect_initial_identifiers(self, blocks: List[MessageBlockInfo]):
        """Собирает идентификаторы из уже определённых модулей."""
        for block in blocks:
            if block.module_hint and block.tree and not block.syntax_error:
                self.module_identifier.collect_from_tree(block.tree, block.module_hint)
        logger.debug(f"Начальные модули: {list(self.module_identifier.get_known_modules())}")

    def _resolve_modules_iteratively(self, blocks):
        for block in blocks:
            if block.module_hint and block.tree and not block.syntax_error:
                self.module_identifier.collect_from_tree(block.tree, block.module_hint)

        self.module_resolver = ModuleResolver(self.module_identifier)
        unknown = [b for b in blocks if not b.module_hint and b.tree and not b.syntax_error]
        iteration = 1
        self.assignment_stats.clear()
        self.temp_modules.clear()

        while unknown:
            newly = []
            still = []
            for block in unknown:
                resolved, module, score = self.module_resolver.resolve_block(block)
                if resolved:
                    block.module_hint = module
                    self.module_identifier.collect_from_tree(block.tree, module)
                    newly.append(block)
                    self.assignment_stats[block.block_id] = (module, score)
                else:
                    still.append(block)
            if not newly:
                break
            unknown = still
            iteration += 1

        for block in unknown:
            if self._block_has_classes(block):
                temp = f"temp_{block.block_id}"
                block.module_hint = temp
                self.module_identifier.collect_from_tree(block.tree, temp)
                self.temp_modules.append(temp)

        if self.temp_modules:
            unknown = [b for b in unknown if not b.module_hint]
            iteration2 = 1
            while unknown:
                newly = []
                still = []
                for block in unknown:
                    resolved, module, score = self.module_resolver.resolve_block(block)
                    if resolved:
                        block.module_hint = module
                        self.module_identifier.collect_from_tree(block.tree, module)
                        newly.append(block)
                        self.assignment_stats[block.block_id] = (module, score)
                    else:
                        still.append(block)
                if not newly:
                    break
                unknown = still
                iteration2 += 1
        else:
            unknown = [b for b in unknown if not b.module_hint]

        logger.info(f"Определено модулей: {len(self.assignment_stats)}")
        logger.info(f"Временных модулей: {len(self.temp_modules)}")
        logger.info(f"Неопределено: {len(unknown)}")
        return unknown
        
    def _block_has_classes(self, block: MessageBlockInfo) -> bool:
        """Проверяет, есть ли в блоке классы."""
        if not block.tree:
            return False
        
        for child in block.tree.children:
            if child.node_type == "class":
                return True
        return False

    def _group_blocks_by_module(self, blocks: List[MessageBlockInfo]) -> Dict[str, List[MessageBlockInfo]]:
        """Группирует блоки по именам модулей."""
        groups = defaultdict(list)
        for block in blocks:
            if block.module_hint:
                groups[block.module_hint].append(block)
        return dict(groups)

    def _select_most_complete_block(self, blocks: List[MessageBlockInfo]) -> Optional[MessageBlockInfo]:
        """Выбирает наиболее полный блок из группы."""
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
        """Выбирает базовые блоки для каждого модуля."""
        self.module_base_blocks = {}
        for module, blocks in self.module_groups.items():
            base = self._select_most_complete_block(blocks)
            if base:
                self.module_base_blocks[module] = base
                logger.debug(f"Базовый блок для {module}: {base.block_id}")

    def _build_initial_structures(self):
        """Строит начальные структуры для каждого модуля."""
        for module_name, base_block in self.module_base_blocks.items():
            container = self.structure_builder.build_initial_structure(module_name, base_block)
            self.module_containers[module_name] = container

    def _merge_remaining_blocks(self):
        """Сливает оставшиеся блоки в существующие контейнеры."""
        for module_name, container in self.module_containers.items():
            base = self.module_base_blocks.get(module_name)
            if not base:
                continue
            other = [b for b in self.module_groups.get(module_name, []) if b is not base]
            other.sort(key=lambda b: b.global_index)
            
            merged_count = 0
            skipped_count = 0
            
            for block in other:
                if block.tree and not block.syntax_error:
                    try:
                        self.structure_builder.merge_node_into_container(block.tree, container, block)
                        merged_count += 1
                    except Exception as e:
                        logger.error(f"Ошибка при слиянии блока {block.block_id}: {e}")
                        skipped_count += 1
                else:
                    skipped_count += 1
            
            logger.debug(f"Модуль {module_name}: слито {merged_count}, пропущено {skipped_count}")

    def _merge_temp_modules(self):
        """
        Переносит идентификаторы из temp-модулей в реальные модули.
        Исправленная версия с правильной обработкой составных ключей методов.
        """
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

            # Перенос методов с правильными составными ключами
            methods_transferred = 0
            
            # Обрабатываем методы из секции methods
            for method_key, method_list in temp_data.get('methods', {}).items():
                for method_info in method_list:
                    # Получаем информацию о методе
                    class_name = method_info.get('class', 'unknown_class')
                    method_name = method_info['name']
                    
                    # Создаем правильный составной ключ
                    composite_key = f"{class_name}.{method_name}"
                    
                    # Добавляем в общий список методов target_module
                    if 'methods' not in self.module_identifier.module_ids[target_module]:
                        self.module_identifier.module_ids[target_module]['methods'] = {}
                    
                    if composite_key not in self.module_identifier.module_ids[target_module]['methods']:
                        self.module_identifier.module_ids[target_module]['methods'][composite_key] = []
                    
                    # Проверяем дубликаты
                    method_exists = False
                    for existing in self.module_identifier.module_ids[target_module]['methods'][composite_key]:
                        if (existing['signature'][0] == method_info['signature'][0] and
                            existing['signature'][1] == method_info['signature'][1]):
                            method_exists = True
                            break
                    
                    if not method_exists:
                        self.module_identifier.module_ids[target_module]['methods'][composite_key].append(method_info)
                        methods_transferred += 1

            # Обрабатываем методы из классов
            for class_name, class_info in temp_data.get('classes', {}).items():
                for method_info in class_info.get('methods', []):
                    composite_key = f"{class_name}.{method_info['name']}"
                    
                    # Находим соответствующий класс в целевом модуле
                    found_class = None
                    for real_class in self.module_identifier.module_ids[target_module]['classes']:
                        if real_class.strip().lower() == class_name.strip().lower():
                            found_class = real_class
                            break
                    
                    if found_class:
                        # Добавляем метод в класс
                        class_info_target = self.module_identifier.module_ids[target_module]['classes'][found_class]
                        if 'methods' not in class_info_target:
                            class_info_target['methods'] = []
                        
                        method_exists = False
                        for m in class_info_target['methods']:
                            if m['name'] == method_info['name']:
                                method_exists = True
                                break
                        
                        if not method_exists:
                            class_info_target['methods'].append({
                                'name': method_info['name'],
                                'signature': method_info['signature']
                            })

            logger.info(f"  Перенесено {methods_transferred} методов из {temp_module} в {target_module}")

        # Удаляем temp-модули
        for temp_module in temp_modules:
            if temp_module in self.module_identifier.module_ids:
                del self.module_identifier.module_ids[temp_module]
                logger.info(f"  Удалён temp-модуль {temp_module}")

    def get_assignment_summary(self) -> Dict[str, Any]:
        """
        Возвращает сводку по назначениям модулей для отображения пользователю.
        """
        summary = {
            'total_blocks': len(self.assignment_stats) + len(self.module_groups) + len(self.error_blocks),
            'assigned': len(self.assignment_stats),
            'temp_modules': len(self.temp_modules),
            'errors': len(self.error_blocks),
            'assignments': []
        }
        
        for block_id, (module, score) in self.assignment_stats.items():
            summary['assignments'].append({
                'block_id': block_id,
                'module': module,
                'confidence': score.total() if score else 0,
                'confidence_level': self._get_confidence_level(score.total() if score else 0),
                'details': str(score) if score else ''
            })
        
        return summary

    def _get_confidence_level(self, score: int) -> str:
        """Возвращает текстовый уровень уверенности."""
        if score >= 100:
            return "очень высокая"
        elif score >= 70:
            return "высокая"
        elif score >= 40:
            return "средняя"
        elif score >= 20:
            return "низкая"
        else:
            return "очень низкая"

    def get_module_statistics(self) -> Dict[str, Any]:
        """
        Возвращает статистику по модулям.
        """
        stats = {
            'total_modules': len(self.module_containers),
            'total_temp_modules': len(self.temp_modules),
            'modules': []
        }
        
        for module_name, container in self.module_containers.items():
            module_stats = {
                'name': module_name,
                'is_temp': module_name.startswith('temp_'),
                'classes': 0,
                'functions': 0,
                'methods': 0,
                'total_versions': 0,
                'blocks_count': len(self.module_groups.get(module_name, []))
            }
            
            def count_elements(cont):
                if cont.node_type == 'class':
                    module_stats['classes'] += 1
                elif cont.node_type == 'function':
                    module_stats['functions'] += 1
                elif cont.node_type == 'method':
                    module_stats['methods'] += 1
                
                module_stats['total_versions'] += len(cont.versions)
                
                for child in cont.children:
                    count_elements(child)
            
            count_elements(container)
            stats['modules'].append(module_stats)
        
        return stats

    def get_blocks_for_module(self, module_name: str) -> List[MessageBlockInfo]:
        """Возвращает все блоки, принадлежащие указанному модулю."""
        return self.module_groups.get(module_name, [])

    def get_module_containers(self) -> Dict[str, Container]:
        """Возвращает все контейнеры модулей."""
        return self.module_containers.copy()

    def get_temp_modules(self) -> List[str]:
        """Возвращает список временных модулей."""
        return self.temp_modules.copy()

    def get_error_blocks(self) -> List[MessageBlockInfo]:
        """Возвращает блоки с ошибками."""
        return self.error_blocks.copy()

    def clear_temp_data(self):
        """Очищает временные данные."""
        self.temp_modules.clear()
        self.assignment_stats.clear()
        self.module_identifier.remove_temp_modules()