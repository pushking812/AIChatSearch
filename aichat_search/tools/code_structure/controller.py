# aichat_search/tools/code_structure/controller.py

import logging
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict

from aichat_search.model import Chat, MessagePair
from aichat_search.tools.code_structure.view import CodeStructureWindow
from aichat_search.tools.code_structure.parser import PARSERS
from aichat_search.tools.code_structure.services.block_manager import BlockManager
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.models.containers import Container, Version
from aichat_search.tools.code_structure.models.node import Node
from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier
from aichat_search.tools.code_structure.core.module_resolver import ModuleResolver
from aichat_search.tools.code_structure.core.structure_builder import StructureBuilder
from aichat_search.tools.code_structure.core.signature_utils import extract_function_signature, compare_signatures

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='code_structure_debug.log',
    filemode='w'
)
logger = logging.getLogger(__name__)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)


class CodeStructureController:
    def __init__(self, parent, items: List[Tuple[Chat, MessagePair]]):
        """
        :param parent: родительское окно
        :param items: список кортежей (Chat, MessagePair) для анализа
        """
        self.parent = parent
        self.items = items
        self.view = CodeStructureWindow(parent)
        self.view.set_controller(self)

        # Менеджер блоков
        self.block_manager = BlockManager()

        # Компоненты для работы с модулями
        self.module_identifier = ModuleIdentifier()
        self.module_resolver = None
        self.structure_builder = StructureBuilder()

        # Текущие данные
        self.current_lang: Optional[str] = None
        self.module_groups: Dict[str, List[MessageBlockInfo]] = {}
        self.module_base_blocks: Dict[str, MessageBlockInfo] = {}
        self.module_containers: Dict[str, Container] = {}
        self.display_root: Optional[Dict[str, Any]] = None

        # Загружаем блоки
        self._load_all_blocks()

        # Определяем модули
        self._resolve_unknown_modules()

        # Строим структуры
        self._select_base_blocks()
        self._build_initial_structures()
        self._merge_remaining_blocks()
        self._build_display_tree()

        if self.display_root:
            self.view.display_merged_tree(self.display_root)

        if self.block_manager.get_languages():
            self._fill_language_combo()
            self.current_lang = self.block_manager.get_languages()[0]
            self._switch_language(self.current_lang)
        else:
            self.view.show_error("В сообщениях нет блоков с поддерживаемыми языками.")
            self.view.destroy()

    def _load_all_blocks(self):
        """Загружает все блоки из списка элементов через BlockManager."""
        self.block_manager.load_from_items(self.items)

    def _fill_language_combo(self):
        """Заполняет комбобокс языков."""
        display_names = [lang.capitalize() for lang in self.block_manager.get_languages()]
        self.view.set_type_combo_values(display_names)

    def _switch_language(self, lang: str):
        """Переключает текущий язык, обновляет второй комбобокс."""
        self.current_lang = lang
        blocks = self.block_manager.get_blocks_by_lang(lang)
        block_names = self._generate_block_names(blocks)
        self.view.set_block_combo_values(block_names)
        if block_names:
            self.view.set_current_block_index(0)
        self.view.clear_tree()
        self.view.display_code("")

    def _generate_block_names(self, blocks: List[MessageBlockInfo]) -> List[str]:
        """Генерирует список имён для отображения во втором комбобоксе."""
        names = []
        for block_info in blocks:
            desc = self._get_block_description(block_info)
            names.append(f"{block_info.block_id} – {desc}")
        names.sort()
        return names

    def _get_block_description(self, block_info: MessageBlockInfo) -> str:
        """Возвращает описание блока на основе его содержимого."""
        if block_info.module_hint:
            return block_info.module_hint
        if block_info.tree is None or block_info.syntax_error:
            return "блок_кода (ошибка)" if block_info.syntax_error else "блок_кода"
        
        def find_first_definition(node):
            for child in node.children:
                if child.node_type == "class":
                    for method in child.children:
                        if method.node_type == "method":
                            return f"class_{child.name}_def_{method.name}"
                    return f"class_{child.name}"
                elif child.node_type == "function":
                    return f"def_{child.name}"
                else:
                    res = find_first_definition(child)
                    if res:
                        return res
            return None
        
        desc = find_first_definition(block_info.tree)
        return desc or "блок_кода"

    def on_type_selected(self, event):
        """Обработчик выбора языка в первом комбобоксе."""
        selected_index = self.view.type_combo.current()
        languages = self.block_manager.get_languages()
        if 0 <= selected_index < len(languages):
            lang = languages[selected_index]
            if lang != self.current_lang:
                self._switch_language(lang)

    def on_block_selected(self, event=None):
        """Автоматически показывает структуру при выборе блока."""
        self.on_show_structure()

    def on_show_structure(self):
        """Показывает структуру выбранного блока."""
        index = self.view.get_selected_block_index()
        if index < 0:
            return

        blocks = self.block_manager.get_blocks_by_lang(self.current_lang)
        if index >= len(blocks):
            return

        selected_name = self.view.block_combo.get()
        block_info = None
        for b in blocks:
            if f"{b.block_id} – {self._get_block_description(b)}" == selected_name:
                block_info = b
                break
        
        if block_info and block_info.tree and not block_info.syntax_error:
            self.view.display_structure(block_info.tree)

    def on_node_selected(self):
        """Обработчик выбора узла в левом дереве."""
        selected = self.view.tree.selection()
        if not selected:
            return
        item = selected[0]
        node = self.view.get_node_by_item(item)
        if node and node.lineno_start and node.lineno_end:
            index = self.view.get_selected_block_index()
            if index < 0:
                return
            blocks = self.block_manager.get_blocks_by_lang(self.current_lang)
            if index >= len(blocks):
                return
            
            selected_name = self.view.block_combo.get()
            block_info = None
            for b in blocks:
                if f"{b.block_id} – {self._get_block_description(b)}" == selected_name:
                    block_info = b
                    break
            
            if block_info:
                lines = block_info.content.splitlines()
                start = max(0, node.lineno_start - 1)
                end = min(len(lines), node.lineno_end)
                if start < end:
                    self.view.display_code("\n".join(lines[start:end]))

    # ---------- Методы для работы с модулями и слиянием ----------

    def _reset_module_assignments(self):
        """Сбрасывает все назначения модулей и перезапускает процесс слияния."""
        for block_info in self.block_manager.get_all_blocks():
            block_info.module_hint = None
        self._resolve_unknown_modules()
        self._select_base_blocks()
        self._build_initial_structures()
        self._merge_remaining_blocks()
        self._build_display_tree()
        if self.display_root:
            self.view.display_merged_tree(self.display_root)

    def _resolve_unknown_modules(self):
        """Определяет модули для блоков без явной подсказки."""
        logger.info("=" * 60)
        logger.info("НАЧАЛО _resolve_unknown_modules")
        
        # Собираем идентификаторы из уже определённых модулей
        known_before = set()
        for block_info in self.block_manager.get_all_blocks():
            if block_info.module_hint:
                known_before.add(block_info.block_id)
        
        logger.info(f"Блоки с уже назначенными модулями до обработки: {known_before}")
        
        for block_info in self.block_manager.get_all_blocks():
            if block_info.module_hint and block_info.tree and not block_info.syntax_error:
                self.module_identifier.collect_from_tree(block_info.tree, block_info.module_hint)
        
        logger.info(f"Собраны идентификаторы для модулей: {list(self.module_identifier.get_known_modules())}")
        
        self.module_resolver = ModuleResolver(self.module_identifier)
        
        # Анализируем блоки
        auto_assign = {}
        need_dialog = []
        
        for block_info in self.block_manager.get_all_blocks():
            if block_info.module_hint:
                logger.debug(f"Блок {block_info.block_id} уже имеет модуль {block_info.module_hint}")
                continue
                
            logger.info(f"Анализ блока {block_info.block_id}")
            logger.debug(f"  Язык: {block_info.language}")
            logger.debug(f"  Содержимое (первые 100 символов): {block_info.content[:100]}...")
            
            resolved, module_name = self.module_resolver.resolve_block(block_info)
            if resolved:
                auto_assign[block_info.block_id] = module_name
                logger.info(f"  -> АВТОМАТИЧЕСКОЕ НАЗНАЧЕНИЕ: {block_info.block_id} -> {module_name}")
            else:
                need_dialog.append(block_info)
                logger.info(f"  -> ТРЕБУЕТСЯ ДИАЛОГ для {block_info.block_id}")
        
        logger.info(f"Автоматические назначения: {auto_assign}")
        logger.info(f"Блоки для диалога: {[b.block_id for b in need_dialog]}")
        
        # Применяем автоматические назначения
        for block_id, module_name in auto_assign.items():
            for block_info in self.block_manager.get_all_blocks():
                if block_info.block_id == block_id:
                    block_info.module_hint = module_name
                    logger.info(f"Применено назначение: {block_id} -> {module_name}")
                    if block_info.tree and not block_info.syntax_error:
                        self.module_identifier.collect_from_tree(block_info.tree, module_name)
        
        # Обновляем группы после автоматических назначений
        self.module_groups = self._group_blocks_by_module()
        logger.info(f"Группы после автоматических назначений: { {k: len(v) for k, v in self.module_groups.items()} }")
        
        # Показываем диалог для оставшихся
        if need_dialog:
            logger.info(f"Показываем диалог для {len(need_dialog)} блоков")
            self._show_module_dialog(need_dialog)
            # После диалога тоже обновляем группы
            self.module_groups = self._group_blocks_by_module()
            logger.info(f"Группы после диалога: { {k: len(v) for k, v in self.module_groups.items()} }")
        else:
            logger.info("Нет блоков для диалога")
        
        # Проверяем результат
        after_assign = {}
        for block_info in self.block_manager.get_all_blocks():
            if block_info.module_hint:
                after_assign[block_info.block_id] = block_info.module_hint
        
        logger.info(f"Итоговые назначения: {after_assign}")
        logger.info("=" * 60)

    def _show_module_dialog(self, unknown_blocks: List[MessageBlockInfo]):
        """Показывает диалог для ручного назначения модулей."""
        dialog_data = []
        for block_info in unknown_blocks:
            dialog_data.append({
                'id': block_info.block_id,
                'display_name': f"{block_info.block_id} – {self._get_block_description(block_info)}",
                'content': block_info.content
            })
        
        known_modules = self.module_identifier.get_known_modules()
        
        # Собираем информацию об источниках для модулей
        module_info = []
        for module in sorted(known_modules):
            source = None
            for bi in self.block_manager.get_all_blocks():
                if bi.module_hint == module and bi.tree:
                    source = f"{bi.block_id} – {self._get_block_description(bi)}"
                    break
            module_info.append({'name': module, 'source': source})
        
        module_code_map = {}
        for module in known_modules:
            for bi in self.block_manager.get_all_blocks():
                if bi.module_hint == module and bi.content:
                    module_code_map[module] = bi.content
                    break
        
        from aichat_search.tools.code_structure.ui.dialogs import ModuleAssignmentDialog
        dialog = ModuleAssignmentDialog(self.view, dialog_data, module_info, module_code_map)
        dialog.controller = self
        self.view.wait_window(dialog)
        
        if dialog.result:
            for block_info in self.block_manager.get_all_blocks():
                if block_info.block_id in dialog.result:
                    block_info.module_hint = dialog.result[block_info.block_id]

    def _group_blocks_by_module(self) -> Dict[str, List[MessageBlockInfo]]:
        """Группирует блоки по module_hint."""
        groups = defaultdict(list)
        for block_info in self.block_manager.get_all_blocks():
            if block_info.module_hint:
                groups[block_info.module_hint].append(block_info)
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
        """После назначения модулей для каждой группы выбирает самый полный блок."""
        self.module_groups = self._group_blocks_by_module()
        logger.info("-" * 40)
        logger.info("Группировка блоков по модулям:")
        for module, blocks in self.module_groups.items():
            logger.info(f"  {module}: {len(blocks)} блоков")
            for b in blocks:
                logger.debug(f"    {b.block_id}")
        
        self.module_base_blocks = {}
        for module, blocks in self.module_groups.items():
            base = self._select_most_complete_block(blocks)
            if base:
                self.module_base_blocks[module] = base
                logger.info(f"  Базовый блок для {module}: {base.block_id} (узлов: {base.tree.count_nodes() if base.tree else 0})")

    def _build_initial_structures(self):
        """Для каждого модуля строит начальную структуру из базового блока."""
        logger.info("-" * 40)
        logger.info("НАЧАЛО _build_initial_structures")
        
        for module_name, base_block in self.module_base_blocks.items():
            logger.info(f"Строим структуру для модуля {module_name} из блока {base_block.block_id}")
            container = self.structure_builder.build_initial_structure(module_name, base_block)
            self.module_containers[module_name] = container
            
            # Подсчитываем элементы в структуре
            versions = self._count_versions(container)
            logger.info(f"  Создано версий: {versions}")
        
        logger.info("КОНЕЦ _build_initial_structures")
        logger.info("-" * 40)

    def _merge_remaining_blocks(self):
        """Для каждого модуля сливает все остальные блоки в существующую структуру."""
        logger.info("-" * 40)
        logger.info("НАЧАЛО _merge_remaining_blocks")
        
        for module_name, container in self.module_containers.items():
            base_block = self.module_base_blocks.get(module_name)
            if not base_block:
                logger.warning(f"Модуль {module_name} не имеет базового блока")
                continue
                
            logger.info(f"Модуль {module_name}: базовый блок {base_block.block_id}")
            
            other_blocks = [b for b in self.module_groups.get(module_name, []) if b is not base_block]
            logger.info(f"  Других блоков: {len(other_blocks)}")
            
            other_blocks.sort(key=lambda b: b.global_index)
            
            for i, block_info in enumerate(other_blocks):
                logger.info(f"  Слияние блока {i+1}/{len(other_blocks)}: {block_info.block_id}")
                if block_info.tree is None or block_info.syntax_error:
                    logger.warning(f"    Блок имеет ошибку - пропускаем")
                    continue
                    
                # Подсчитываем версии до слияния
                versions_before = self._count_versions(container)
                logger.debug(f"    Версий до слияния: {versions_before}")
                
                self.structure_builder.merge_node_into_container(block_info.tree, container, block_info)
                
                # Подсчитываем версии после слияния
                versions_after = self._count_versions(container)
                logger.debug(f"    Версий после слияния: {versions_after}")
        
        logger.info("КОНЕЦ _merge_remaining_blocks")
        logger.info("-" * 40)

    def _count_versions(self, container: Container) -> Dict[str, int]:
        """Подсчитывает количество версий в контейнере и его потомках."""
        result = {}
        if container.versions:
            result[container.name] = len(container.versions)
        for child in container.children:
            child_counts = self._count_versions(child)
            result.update(child_counts)
        return result

    def _build_display_tree(self):
        """Строит древовидную структуру для отображения в правой панели."""
        # Находим максимальную версию среди всех модулей
        max_global_version = 0
        for container in self.module_containers.values():
            container_node = self._container_to_display_node(container)
            if 'max_version' in container_node:
                max_global_version = max(max_global_version, container_node['max_version'])
        
        root = {
            'text': 'Все модули',
            'type': 'root',
            'signature': '',
            'version': f"v{max_global_version}" if max_global_version > 0 else '',
            'sources': '',
            'children': []
        }
        for module_name, container in self.module_containers.items():
            root['children'].append(self._container_to_display_node(container))
        self.display_root = root

    def _container_to_display_node(self, container: Container) -> Dict[str, Any]:
        """Преобразует контейнер в узел для отображения."""
        # Определяем максимальную версию для контейнера
        max_version = 0
        if container.versions:
            max_version = len(container.versions)
            logger.debug(f"Контейнер {container.name} имеет {max_version} версий")
        
        # Также проверяем дочерние контейнеры
        child_max = 0
        for child in container.children:
            child_node = self._container_to_display_node(child)
            if 'max_version' in child_node:
                child_max = max(child_max, child_node['max_version'])
        
        max_version = max(max_version, child_max)
        
        node = {
            'text': container.name,
            'type': container.node_type,
            'signature': '',
            'version': f"v{max_version}" if max_version > 0 else '',
            'sources': '',
            'children': [],
            'max_version': max_version
        }
        
        if container.node_type in ('module', 'class'):
            for child in container.children:
                node['children'].append(self._container_to_display_node(child))
        elif container.node_type in ('function', 'method', 'code_block'):
            for i, version in enumerate(container.versions):
                sources = ', '.join(src[0] for src in version.sources)
                version_node = {
                    'text': version.node.name,
                    'type': 'version',
                    'signature': version.node.signature,
                    'version': f"v{i+1}",
                    'sources': sources,
                    'children': [],
                    '_version_data': version
                }
                node['children'].append(version_node)
        
        return node

    def on_merged_node_selected(self, node_data: Dict[str, Any]):
        """Обработчик выбора узла в сводном дереве."""
        if node_data['type'] == 'version':
            version_data = node_data.get('_version_data')
            if version_data and version_data.sources:
                block_id, start, end, _ = version_data.sources[0]
                for block_info in self.block_manager.get_all_blocks():
                    if block_info.block_id == block_id:
                        lines = block_info.content.splitlines()
                        if start and end:
                            code = '\n'.join(lines[start-1:end])
                        else:
                            code = block_info.content
                        self.view.display_merged_code(code, block_info.language)
                        return
        else:
            self.view.display_merged_code("")