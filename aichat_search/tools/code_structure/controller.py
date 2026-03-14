# aichat_search/tools/code_structure/controller.py

import logging
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict

from aichat_search.model import Chat, MessagePair
from aichat_search.services.block_parser import BlockParser
from .view import CodeStructureWindow
from .parser import PARSERS
from .services.block_manager import BlockManager
from .models.block_info import MessageBlockInfo
from .models.containers import (
    Container, ModuleContainer, ClassContainer, FunctionContainer,
    MethodContainer, CodeBlockContainer, Version
)
from .models.node import Node, ClassNode, FunctionNode, MethodNode, CodeBlockNode

logger = logging.getLogger(__name__)


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

        # Текущие данные для отображения в левой панели
        self.current_lang: Optional[str] = None
        self.current_block_index: int = -1

        # Данные для слияния по модулям
        self.module_groups: Dict[str, List[MessageBlockInfo]] = {}
        self.module_base_blocks: Dict[str, MessageBlockInfo] = {}
        self.module_containers: Dict[str, Container] = {}

        # Корень отображаемого дерева
        self.display_root: Optional[Dict[str, Any]] = None

        # Загружаем все блоки из сообщений
        self._load_all_blocks()

        # Если есть неизвестные модули, вызываем диалог
        self._resolve_unknown_modules()

        # Выбираем базовые блоки для каждого модуля
        self._select_base_blocks()

        # Строим начальные структуры из базовых блоков
        self._build_initial_structures()

        # Сливаем остальные блоки в структуры
        self._merge_remaining_blocks()

        # Строим дерево для отображения
        self._build_display_tree()

        # Отображаем сводное дерево в правой панели
        if self.display_root:
            self.view.display_merged_tree(self.display_root)

        if self.block_manager.get_languages():
            self._fill_language_combo()
            # Выбираем первый язык и загружаем его блоки
            self.current_lang = self.block_manager.get_languages()[0]
            self._switch_language(self.current_lang)
            self.view.show_button.config(command=self.on_show_structure)
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
            self.view.set_current_block_index(0)  # выбираем первый по алфавиту
        # Очищаем дерево и текстовое поле
        self.view.clear_tree()
        self.view.display_code("")

    def _generate_block_names(self, blocks: List[MessageBlockInfo]) -> List[str]:
        """Генерирует список имён для отображения во втором комбобоксе (отсортирован по алфавиту)."""
        names = []
        for block_info in blocks:
            desc = self._get_block_description(block_info)
            full_name = f"{block_info.block_id} – {desc}"
            names.append(full_name)
        names.sort()
        return names

    def _get_block_description(self, block_info: MessageBlockInfo) -> str:
        """Возвращает описание блока на основе его содержимого."""
        if block_info.module_hint:
            return block_info.module_hint

        if block_info.tree is None or block_info.syntax_error:
            return "блок_кода (ошибка)" if block_info.syntax_error else "блок_кода"

        # Рекурсивный поиск первого определения
        def find_first_definition(node):
            for child in node.children:
                if child.node_type == "class":
                    # Ищем первый метод внутри класса
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
        if desc:
            return desc
        return "блок_кода"

    def _extract_block_name(self, block_info: MessageBlockInfo) -> str:
        """Извлекает имя блока для отображения в комбобоксе (используется только для совместимости)."""
        if block_info.syntax_error:
            return "блок_кода (ошибка)"

        lines = block_info.content.splitlines()
        if not lines:
            return "блок_кода"

        start_idx = 0
        while start_idx < len(lines) and not lines[start_idx].strip():
            start_idx += 1
        if start_idx >= len(lines):
            return "блок_кода"

        # Поиск комментариев
        comment_lines = []
        i = start_idx
        while i < len(lines) and i - start_idx < 10:
            stripped = lines[i].strip()
            if stripped.startswith('#'):
                comment_lines.append(stripped[1:].strip())
                i += 1
            else:
                break
        if comment_lines:
            return " ".join(comment_lines)

        # Поиск class или def
        i = start_idx
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped.startswith('class '):
                parts = stripped[6:].split()
                if parts:
                    return parts[0].split('(')[0]
            elif stripped.startswith('def '):
                parts = stripped[4:].split()
                if parts:
                    return parts[0].split('(')[0]
            elif stripped.startswith('@'):
                i += 1
                continue
            elif stripped:
                break
            i += 1

        return "блок_кода"

    def on_type_selected(self, event):
        """Обработчик выбора языка в первом комбобоксе."""
        selected_index = self.view.type_combo.current()
        languages = self.block_manager.get_languages()
        if 0 <= selected_index < len(languages):
            lang = languages[selected_index]
            if lang != self.current_lang:
                self._switch_language(lang)

    def on_show_structure(self):
        """Показывает структуру выбранного блока."""
        index = self.view.get_selected_block_index()
        if index < 0:
            return

        blocks = self.block_manager.get_blocks_by_lang(self.current_lang)
        if index >= len(blocks):
            return

        # Индекс в отсортированном списке соответствует блоку в blocks
        # Найдём соответствующий block_info по имени
        selected_name = self.view.block_combo.get()
        block_info = None
        for b in blocks:
            if f"{b.block_id} – {self._get_block_description(b)}" == selected_name:
                block_info = b
                break
        if not block_info:
            return

        if block_info.syntax_error:
            self.view.show_error(f"Выбранный блок содержит ошибку парсинга: {block_info.syntax_error}")
            return

        if block_info.tree is None:
            self.view.show_error("Дерево блока не построено.")
            return

        # Отображаем структуру
        self.view.display_structure(block_info.tree)

    def on_node_selected(self):
        """Обработчик выбора узла в дереве (без изменений)."""
        selected = self.view.tree.selection()
        if not selected:
            return
        item = selected[0]
        node = self.view.get_node_by_item(item)
        if node and node.lineno_start and node.lineno_end:
            # Определяем текущий блок
            index = self.view.get_selected_block_index()
            if index < 0:
                return
            blocks = self.block_manager.get_blocks_by_lang(self.current_lang)
            if index >= len(blocks):
                return
            # Получаем block_info по индексу
            selected_name = self.view.block_combo.get()
            block_info = None
            for b in blocks:
                if f"{b.block_id} – {self._get_block_description(b)}" == selected_name:
                    block_info = b
                    break
            if not block_info:
                return
            code_lines = block_info.content.splitlines()
            start = node.lineno_start - 1
            end = node.lineno_end
            if start < 0:
                start = 0
            if end > len(code_lines):
                end = len(code_lines)
            if start < end:
                selected_code = "\n".join(code_lines[start:end])
                self.view.display_code(selected_code)
            else:
                self.view.display_code("")

    # ---------- Методы для работы с модулями и слиянием ----------

    def _reset_module_assignments(self):
        """Сбрасывает все назначения модулей и перезапускает процесс слияния."""
        # Очищаем module_hint у всех блоков
        for block_info in self.block_manager.get_all_blocks():
            block_info.module_hint = None

        # Заново запускаем весь конвейер
        self._resolve_unknown_modules()
        self._select_base_blocks()
        self._build_initial_structures()
        self._merge_remaining_blocks()
        self._build_display_tree()

        # Обновляем отображение правого дерева
        if self.display_root:
            self.view.display_merged_tree(self.display_root)

    def _resolve_unknown_modules(self):
        """Вызывает диалог для назначения модулей блокам без подсказки."""
        # Собираем блоки без module_hint
        unknown_blocks = []  # список MessageBlockInfo
        known_modules = set()
        for block_info in self.block_manager.get_all_blocks():
            if block_info.module_hint:
                known_modules.add(block_info.module_hint)
            else:
                unknown_blocks.append(block_info)

        if not unknown_blocks:
            return

        # Подготавливаем данные для диалога: список словарей с id, display_name, content
        dialog_data = []
        for block_info in unknown_blocks:
            display_name = self._get_block_description(block_info)
            dialog_data.append({
                'id': block_info.block_id,
                'display_name': f"{block_info.block_id} – {display_name}",
                'content': block_info.content
            })

        # Передаём также карту кодов для известных модулей (для отображения в правом поле)
        module_code_map = {}
        for module in known_modules:
            # Берём первый попавшийся блок этого модуля (например, базовый)
            base = self.module_base_blocks.get(module)
            if base:
                module_code_map[module] = base.content
            else:
                # Если нет базового, ищем любой блок
                for bi in self.block_manager.get_all_blocks():
                    if bi.module_hint == module and bi.content:
                        module_code_map[module] = bi.content
                        break

        from .ui.dialogs import ModuleAssignmentDialog
        dialog = ModuleAssignmentDialog(self.view, dialog_data, sorted(known_modules), module_code_map)
        self.view.wait_window(dialog)

        if dialog.result:
            for block_info in self.block_manager.get_all_blocks():
                if block_info.block_id in dialog.result:
                    block_info.module_hint = dialog.result[block_info.block_id]

    def _group_blocks_by_module(self) -> Dict[str, List[MessageBlockInfo]]:
        """Группирует блоки по module_hint (только для блоков с назначенным модулем)."""
        groups = defaultdict(list)
        for block_info in self.block_manager.get_all_blocks():
            if block_info.module_hint:
                groups[block_info.module_hint].append(block_info)
        return dict(groups)

    def _select_most_complete_block(self, blocks: List[MessageBlockInfo]) -> Optional[MessageBlockInfo]:
        """Выбирает блок с максимальным числом узлов. При равенстве — с минимальным global_index."""
        if not blocks:
            return None
        best = None
        best_count = -1
        best_index = float('inf')
        for block in blocks:
            if block.tree is None or block.syntax_error:
                continue
            if not hasattr(block.tree, 'count_nodes'):
                print(f"ВНИМАНИЕ: У узла {type(block.tree)} нет метода count_nodes!")
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
        self.module_base_blocks = {}
        for module, blocks in self.module_groups.items():
            base = self._select_most_complete_block(blocks)
            if base:
                self.module_base_blocks[module] = base
                logger.debug(f"Модуль {module}: базовый блок {base.block_id} (индекс {base.global_index}) с {base.tree.count_nodes()} узлами")

    def _build_initial_structures(self):
        """Для каждого модуля строит начальную структуру из базового блока."""
        for module_name, base_block in self.module_base_blocks.items():
            container = self._build_initial_structure(module_name, base_block)
            self.module_containers[module_name] = container
            logger.debug(f"Построена начальная структура для модуля {module_name}")

    def _build_initial_structure(self, module_name: str, base_block: MessageBlockInfo) -> ModuleContainer:
        """
        Строит начальную структуру модуля на основе дерева базового блока.
        """
        module_container = ModuleContainer(module_name)
        if base_block.tree is None:
            return module_container

        # Рекурсивно обходим дерево узлов
        self._build_container_from_node(base_block.tree, module_container, base_block)
        return module_container

    def _build_container_from_node(self, node: Node, parent_container: Container, block_info: MessageBlockInfo):
        """
        Рекурсивно строит контейнеры и версии из узла AST и добавляет их в parent_container.
        """
        if isinstance(node, ClassNode):
            class_container = ClassContainer(node.name)
            parent_container.add_child(class_container)
            for child in node.children:
                self._build_container_from_node(child, class_container, block_info)

        elif isinstance(node, FunctionNode):
            func_container = FunctionContainer(node.name)
            version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
            func_container.add_version(version)
            parent_container.add_child(func_container)

        elif isinstance(node, MethodNode):
            method_container = MethodContainer(node.name)
            version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
            method_container.add_version(version)
            parent_container.add_child(method_container)

        elif isinstance(node, CodeBlockNode):
            block_container = CodeBlockContainer(f"CodeBlock_{len(parent_container.children)}")
            version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
            block_container.add_version(version)
            parent_container.add_child(block_container)

        else:
            for child in node.children:
                self._build_container_from_node(child, parent_container, block_info)

    def _merge_remaining_blocks(self):
        """Для каждого модуля сливает все остальные блоки в существующую структуру."""
        for module_name, container in self.module_containers.items():
            base_block = self.module_base_blocks.get(module_name)
            if not base_block:
                continue
            # Все блоки этого модуля, кроме базового
            other_blocks = [b for b in self.module_groups.get(module_name, []) if b is not base_block]
            # Сортируем по глобальному индексу для сохранения хронологии
            other_blocks.sort(key=lambda b: b.global_index)
            for block_info in other_blocks:
                if block_info.tree is None or block_info.syntax_error:
                    continue
                self._merge_node_into_container(block_info.tree, container, block_info)
                logger.debug(f"Модуль {module_name}: слит блок {block_info.block_id}")

    def _merge_node_into_container(self, node: Node, container: Container, block_info: MessageBlockInfo):
        """
        Рекурсивно обходит узел и сливает его содержимое в контейнер.
        """
        if isinstance(node, ClassNode):
            # Ищем или создаём контейнер класса
            class_container = container.find_child_container(node.name, "class")
            if class_container is None:
                class_container = ClassContainer(node.name)
                container.add_child(class_container)
            # Рекурсивно обрабатываем детей (методы, внутренние классы, блоки кода)
            for child in node.children:
                self._merge_node_into_container(child, class_container, block_info)

        elif isinstance(node, FunctionNode):
            # Ищем контейнер функции по имени
            func_container = container.find_child_container(node.name, "function")
            if func_container is None:
                func_container = FunctionContainer(node.name)
                container.add_child(func_container)
            # Проверяем наличие версии с таким же очищенным содержимым
            version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
            existing_version = self._find_version_by_content(func_container.versions, version.cleaned_content)
            if existing_version:
                existing_version.add_source(block_info.block_id, node.lineno_start, node.lineno_end, block_info.global_index)
            else:
                func_container.add_version(version)

        elif isinstance(node, MethodNode):
            # Аналогично функции, но ищем среди детей класса
            method_container = container.find_child_container(node.name, "method")
            if method_container is None:
                method_container = MethodContainer(node.name)
                container.add_child(method_container)
            version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
            existing_version = self._find_version_by_content(method_container.versions, version.cleaned_content)
            if existing_version:
                existing_version.add_source(block_info.block_id, node.lineno_start, node.lineno_end, block_info.global_index)
            else:
                method_container.add_version(version)

        elif isinstance(node, CodeBlockNode):
            # Для блоков кода ищем существующий контейнер с версией того же содержимого
            version = Version(node, block_info.block_id, block_info.global_index, block_info.content)
            found = False
            for child in container.children:
                if child.node_type == "code_block":
                    for ver in child.versions:
                        if ver.cleaned_content == version.cleaned_content:
                            ver.add_source(block_info.block_id, node.lineno_start, node.lineno_end, block_info.global_index)
                            found = True
                            break
                    if found:
                        break
            if not found:
                # Создаём новый контейнер с уникальным именем
                block_container = CodeBlockContainer(f"CodeBlock_{len(container.children)}")
                block_container.add_version(version)
                container.add_child(block_container)

        else:
            # Для неизвестных типов (например, ModuleNode) просто рекурсивно обрабатываем детей
            for child in node.children:
                self._merge_node_into_container(child, container, block_info)

    def _find_version_by_content(self, versions: List[Version], cleaned_content: str) -> Optional[Version]:
        """Ищет версию с указанным очищенным содержимым."""
        for v in versions:
            if v.cleaned_content == cleaned_content:
                return v
        return None

    # ---------- Построение отображаемого дерева ----------

    def _build_display_tree(self):
        """
        Строит древовидную структуру для отображения в правой панели.
        Результат сохраняется в self.display_root в формате, пригодном для заполнения Treeview.
        """
        # Корневой узел "Все модули"
        root = {
            'text': 'Все модули',
            'type': 'root',
            'signature': '',
            'sources': '',
            'children': []
        }

        # Для каждого модуля создаём узел
        for module_name, container in self.module_containers.items():
            module_node = self._container_to_display_node(container)
            root['children'].append(module_node)

        self.display_root = root
        logger.debug("Построено дерево для отображения")

    def _container_to_display_node(self, container: Container) -> Dict[str, Any]:
        """
        Преобразует контейнер в узел для отображения.
        Возвращает словарь с полями: text, type, signature, sources, children.
        """
        node = {
            'text': container.name,
            'type': container.node_type,
            'signature': '',
            'sources': '',
            'children': []
        }

        if container.node_type == 'module':
            for child in container.children:
                node['children'].append(self._container_to_display_node(child))
        elif container.node_type == 'class':
            for child in container.children:
                node['children'].append(self._container_to_display_node(child))
        elif container.node_type in ('function', 'method', 'code_block'):
            for i, version in enumerate(container.versions):
                sources_str = ', '.join(src[0] for src in version.sources)
                version_node = {
                    'text': f"Версия {i+1} ({sources_str})",
                    'type': 'version',
                    'signature': version.node.signature,
                    'sources': sources_str,
                    'children': [],
                    '_version_data': version  # сохраняем ссылку на объект Version
                }
                node['children'].append(version_node)
        else:
            pass

        return node

    def on_merged_node_selected(self, node_data: Dict[str, Any]):
        """Обработчик выбора узла в сводном дереве."""
        if node_data['type'] == 'version':
            # Для версии показываем код из первого источника
            version_data = node_data.get('_version_data')
            if version_data and version_data.sources:
                # Получаем первый источник
                block_id, start, end, _ = version_data.sources[0]
                # Находим блок по block_id
                for block_info in self.block_manager.get_all_blocks():
                    if block_info.block_id == block_id:
                        lines = block_info.content.splitlines()
                        if start and end:
                            code = '\n'.join(lines[start-1:end])
                        else:
                            code = block_info.content
                        self.view.display_merged_code(code, block_info.language)
                        return
        elif node_data['type'] in ('class', 'module', 'root'):
            # Для контейнеров без версии ничего не показываем
            self.view.display_merged_code("")