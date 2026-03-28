# aichat_search/tools/code_structure/controller.py

import logging
import pickle
import os
import textwrap
from tkinter import messagebox
from typing import List, Dict, Optional, Any, Tuple

from aichat_search.model import Chat, MessagePair
from aichat_search.tools.code_structure.ui.code_structure import CodeStructureView as CodeStructureWindow

from aichat_search.tools.code_structure.services.block_service import BlockService
from aichat_search.tools.code_structure.services.module_service import ModuleService
from aichat_search.tools.code_structure.services.import_service import ImportService


from aichat_search.tools.code_structure.core.tree_builder import TreeBuilder

from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo

from aichat_search.tools.code_structure.ui import ModuleAssignmentDialog

from aichat_search.tools.code_structure.ui import ErrorBlockDialog
from aichat_search.tools.code_structure.ui.dto_builder import DtoBuilder
from aichat_search.tools.code_structure.ui.dto import (
    ModuleAssignmentInput, UnknownBlockInfo, KnownModuleInfo, TreeDisplayNode, ErrorBlockInput
)

from aichat_search.tools.code_structure.utils.logger import get_logger
logger = get_logger(__name__)

if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


class CodeStructureController:
    def __init__(self, parent, items: List[Tuple[Chat, MessagePair]]):
        self.parent = parent
        self.items = items

        self.block_service = BlockService()
        self.module_service = ModuleService()
        self.tree_builder = TreeBuilder()
        self.import_service = ImportService()

        self.view = CodeStructureWindow(parent)
        self.view.set_controller(self)

        self.current_lang: Optional[str] = None
        self._flat_items: List[Dict[str, Any]] = []

        self._run_analysis()

    # ---------- Основной анализ ----------
    def _run_analysis(self):
        self.block_service.load_from_items(self.items)

        error_blocks = self.block_service.get_error_blocks()
        if error_blocks:
            self._handle_error_blocks(error_blocks)

        all_blocks = self.block_service.get_all_blocks()
        text_blocks_by_pair = self.block_service.get_text_blocks_by_pair()
        full_texts_by_pair = self.block_service.get_full_texts_by_pair()

        containers, unknown_blocks = self.module_service.process_blocks(
            all_blocks,
            text_blocks_by_pair=text_blocks_by_pair,
            full_texts_by_pair=full_texts_by_pair
        )
        self.module_service.module_containers = containers
        self.module_service.unknown_blocks = unknown_blocks

        self._build_and_display_tree()
        self._update_flat_list()
        self._update_module_button_state()
        self._setup_interface()

        if unknown_blocks:
            self._show_module_dialog(unknown_blocks)

    def _handle_error_blocks(self, error_blocks: List[MessageBlockInfo]):
        for block in error_blocks:
            input_data = ErrorBlockInput(
                block_id=block.block_id,
                original_code=block.content,
                language=block.language
            )
            dialog = ErrorBlockDialog(self.view, input_data)
            self.view.wait_window(dialog)
            if dialog.result is not None:
                self.block_service.fix_error_block(block, dialog.result)

    # ---------- Построение деревьев ----------
    def _build_and_display_tree(self, local_only: bool = None):
        if local_only is None:
            local_only = self.view.local_only_var.get()
        root, flat_items = self.tree_builder.build_display_tree(
            self.module_service.module_containers,
            local_only=local_only
        )
        if root:
            self.view.display_merged_tree(root)
            logger.info("Дерево с пакетами отображено")
        self._flat_items = flat_items

    def _update_flat_list(self):
        if not self._flat_items:
            return
        all_blocks = self.block_service.get_all_blocks()
        block_map = {b.block_id: b for b in all_blocks}
        enriched = []
        for item in self._flat_items:
            block_id = item['block_id']
            block = block_map.get(block_id)
            if block:
                module = block.module_hint or ''
                strategy = block.assignment_strategy or ''
                enriched_item = item.copy()
                enriched_item['module'] = module
                enriched_item['strategy'] = strategy
                if item['node_type'] == 'method' and item['parent_path']:
                    enriched_item['class'] = item['parent_path'].split('.')[-1]
                else:
                    enriched_item['class'] = '-'
                enriched.append(enriched_item)
            else:
                enriched.append(item)
        self.view.set_flat_list(enriched)

    def _update_module_button_state(self):
        enabled = len(self.module_service.unknown_blocks) > 0
        self.view.set_module_button_state(enabled)

    # ---------- Интерфейс ----------
    def _setup_interface(self):
        languages = self.block_service.get_languages()
        if not languages:
            self.view.show_error("Нет блоков с поддерживаемыми языками")
            self.view.destroy()
            return
        self.view.set_type_combo_values([lang.capitalize() for lang in languages])
        self.view.set_type_combo_state(len(languages) > 1)
        self.current_lang = languages[0]
        self._switch_language(self.current_lang)

    def _switch_language(self, lang: str):
        self.current_lang = lang
        self.view.display_code("")

    # ---------- Диалоги ----------
    def _show_module_dialog(self, unknown_blocks: List[MessageBlockInfo]):
        # Подготавливаем DTO
        input_dto = self._prepare_module_assignment_input()
        # Создаём диалог с DTO
        from aichat_search.tools.code_structure.ui import ModuleAssignmentDialog
        dialog = ModuleAssignmentDialog(self.view, input_dto)
        self.view.wait_window(dialog)
        if dialog.result:
            self._apply_dialog_result(dialog.result)

    def _apply_dialog_result(self, result):
        # result — это ModuleAssignmentOutput
        assignments = result.assignments
        all_blocks = self.block_service.get_all_blocks()

        for block in all_blocks:
            if block.block_id in assignments:
                block.module_hint = assignments[block.block_id]
                if block.tree and not block.syntax_error:
                    self.module_service.identifier.collect_from_tree(
                        block.tree, block.module_hint, block_info=block
                    )

        # Перестраиваем контейнеры (можно пересобрать заново)
        text_blocks_by_pair = self.block_service.get_text_blocks_by_pair()
        full_texts_by_pair = self.block_service.get_full_texts_by_pair()
        containers, unknown_blocks = self.module_service.process_blocks(
            all_blocks,
            text_blocks_by_pair=text_blocks_by_pair,
            full_texts_by_pair=full_texts_by_pair
        )
        self.module_service.module_containers = containers
        self.module_service.unknown_blocks = unknown_blocks

        self._build_and_display_tree()
        self._update_flat_list()
        self._update_module_button_state()

    def _reset_module_assignments(self):
        all_blocks = self.block_service.get_all_blocks()
        self.module_service.reset_assignments(all_blocks)
        text_blocks_by_pair = self.block_service.get_text_blocks_by_pair()
        full_texts_by_pair = self.block_service.get_full_texts_by_pair()
        containers, unknown_blocks = self.module_service.process_blocks(
            all_blocks,
            text_blocks_by_pair=text_blocks_by_pair,
            full_texts_by_pair=full_texts_by_pair
        )
        self.module_service.module_containers = containers
        self.module_service.unknown_blocks = unknown_blocks
        self._build_and_display_tree()
        self._update_flat_list()
        self._update_module_button_state()
        if unknown_blocks:
            self._show_module_dialog(unknown_blocks)

    # ---------- Сохранение/загрузка ----------
    def _save_structure(self):
        try:
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '.config')
            config_dir = os.path.abspath(config_dir)
            os.makedirs(config_dir, exist_ok=True)
            file_path = os.path.join(config_dir, 'project_structure.pkl')
            data = {
                'module_containers': self.module_service.module_containers,
                'imported_items': self.import_service.get_imported_items(self.block_service.get_all_blocks())
            }
            with open(file_path, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info(f"Структура сохранена в {file_path}")
            messagebox.showinfo("Сохранение структуры", f"Структура сохранена в {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении структуры: {e}", exc_info=True)
            self.view.show_error(f"Не удалось сохранить структуру: {e}")

    def _load_structure(self):
        try:
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '.config')
            config_dir = os.path.abspath(config_dir)
            file_path = os.path.join(config_dir, 'project_structure.pkl')
            if not os.path.exists(file_path):
                messagebox.showinfo("Загрузка структуры", "Файл сохранённой структуры не найден.")
                return
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            self.module_service.module_containers = data['module_containers']
            self._build_and_display_tree()
            self._update_flat_list()
            logger.info(f"Структура загружена из {file_path}")
            messagebox.showinfo("Загрузка структуры", f"Структура загружена из {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке структуры: {e}", exc_info=True)
            self.view.show_error(f"Не удалось загрузить структуру: {e}")

    def _create_project(self):
        messagebox.showinfo("Создание проекта", "Функция создания проекта будет реализована в следующей версии.")

    # ---------- Обработка выбора узлов ----------
    def on_merged_node_selected(self, node_data: Dict[str, Any]):
        code = self._render_code_from_node(node_data)
        if code:
            self.view.display_merged_code(code, "python")
        else:
            self.view.display_merged_code("")

    def on_type_selected(self, event):
        idx = self.view.type_combo.current()
        langs = self.block_service.get_languages()
        if 0 <= idx < len(langs):
            lang = langs[idx]
            if lang != self.current_lang:
                self._switch_language(lang)

    def on_local_only_toggled(self, local_only: bool):
        self._build_and_display_tree(local_only)
        self._update_flat_list()

    def on_flat_node_selected(self, block_id: str, lines: str):
        block = next((b for b in self.block_service.get_all_blocks() if b.block_id == block_id), None)
        if block:
            self.view.display_code(block.content, block.language)
        else:
            self.view.display_code("")

    # ---------- Вспомогательные методы ----------
    def _render_code_from_node(self, node_data: Dict[str, Any]) -> str:
        if node_data.get('type') == 'version':
            version = node_data.get('_version_data')
            if version and version.sources:
                block_id, start, end, _ = version.sources[0]
                for block in self.block_service.get_all_blocks():
                    if block.block_id == block_id:
                        lines = block.content.splitlines()
                        fragment = '\n'.join(lines[start-1:end]) if start and end else block.content
                        return textwrap.dedent(fragment)
        elif '_container' in node_data:
            container = node_data['_container']
            if container.node_type in ('method', 'function', 'code_block', 'import'):
                latest = container.get_latest_version()
                if latest and latest.sources:
                    block_id, start, end, _ = latest.sources[0]
                    for block in self.block_service.get_all_blocks():
                        if block.block_id == block_id:
                            lines = block.content.splitlines()
                            fragment = '\n'.join(lines[start-1:end]) if start and end else block.content
                            return textwrap.dedent(fragment)
            elif container.node_type == 'class':
                class_lines = [f"class {container.name}:"]
                for child_node in node_data.get('children', []):
                    child_code = self._render_code_from_node(child_node)
                    if child_code:
                        class_lines.extend("    " + line for line in child_code.splitlines())
                return '\n'.join(class_lines)
            elif container.node_type == 'module':
                lines = []
                for child_node in node_data.get('children', []):
                    child_code = self._render_code_from_node(child_node)
                    if child_code:
                        lines.append(child_code)
                return '\n\n'.join(lines)
            elif container.node_type == 'package':
                return "# Пакет (не содержит кода)"
        return ""
        
    def _prepare_module_assignment_input(self) -> ModuleAssignmentInput:
        """
        Подготавливает DTO для диалога назначения модулей.
        Преобразует внутренние данные в DTO без ссылок на реальные объекты.
        """
        # Получаем неопределённые блоки (MessageBlockInfo)
        unknown_blocks_info = []
        for block in self.module_service.unknown_blocks:
            display_name = f"{block.block_id} – {self.block_service.get_block_description(block)}"
            unknown_blocks_info.append(UnknownBlockInfo(
                id=block.block_id,
                display_name=display_name,
                content=block.content
            ))

        # Получаем известные модули
        known_modules_info = []
        for module_name in sorted(self.module_service.get_known_modules()):
            source = self.module_service.get_module_source(
                module_name,
                self.block_service.get_all_blocks()
            )
            code = self.module_service.get_module_code(
                module_name,
                self.block_service.get_all_blocks()
            ) or ""
            known_modules_info.append(KnownModuleInfo(
                name=module_name,
                source=source,
                code=code
            ))

        # Строим дерево для отображения
        root_dict, _ = self.tree_builder.build_display_tree(
            self.module_service.module_containers,
            local_only=self.view.local_only_var.get()
        )
        module_tree = DtoBuilder.tree_dict_to_dto(root_dict)

        return ModuleAssignmentInput(
            unknown_blocks=unknown_blocks_info,
            known_modules=known_modules_info,
            module_tree=module_tree
        )