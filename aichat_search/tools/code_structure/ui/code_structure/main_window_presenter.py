# aichat_search/tools/code_structure/ui/code_structure/main_window_presenter.py

import logging
import textwrap
from typing import List, Dict, Optional, Any, Tuple

from aichat_search.model import Chat, MessagePair
from aichat_search.tools.code_structure.ui.dialog_interfaces import CodeStructureView
from aichat_search.tools.code_structure.services.block_service import BlockService
from aichat_search.tools.code_structure.services.module_service import ModuleService
from aichat_search.tools.code_structure.core.tree_builder import TreeBuilder
from aichat_search.tools.code_structure.services.import_service import ImportService
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.ui.dto import TreeDisplayNode
from aichat_search.tools.code_structure.ui.dto_builder import DtoBuilder
from aichat_search.tools.code_structure.utils.logger import get_logger

logger = get_logger(__name__)


class CodeStructurePresenter:
    def __init__(self, view: CodeStructureView, items: List[Tuple[Chat, MessagePair]]):
        self.view = view
        self.items = items

        self.block_service = BlockService()
        self.module_service = ModuleService()
        self.tree_builder = TreeBuilder()
        self.import_service = ImportService()

        self.current_lang: Optional[str] = None
        self._flat_items: List[Dict[str, Any]] = []

        # Инициализация
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
        from aichat_search.tools.code_structure.ui import ErrorBlockDialog
        from aichat_search.tools.code_structure.ui.dto import ErrorBlockInput

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
            local_only = self.view.get_local_only()
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
        from aichat_search.tools.code_structure.ui import ModuleAssignmentDialog
        input_dto = self._prepare_module_assignment_input()
        dialog = ModuleAssignmentDialog(self.view, input_dto)
        self.view.wait_window(dialog)
        if dialog.result:
            self._apply_dialog_result(dialog.result)

    def _prepare_module_assignment_input(self):
        # (код из controller, но теперь внутри презентера)
        # нужно будет использовать DtoBuilder и т.д.
        # Временно копируем из controller, но потом переиспользуем
        pass

    def _apply_dialog_result(self, result):
        # (код из controller)
        pass

    # ---------- Сохранение/загрузка ----------
    def _save_structure(self):
        # (код из controller)
        pass

    def _load_structure(self):
        # (код из controller)
        pass

    def _create_project(self):
        # (код из controller)
        pass

    # ---------- Обработка выбора узлов ----------
    def on_merged_node_selected(self, node_data: Dict[str, Any]):
        code = self._render_code_from_node(node_data)
        if code:
            self.view.display_merged_code(code, "python")
        else:
            self.view.display_merged_code("")

    def on_type_selected(self, event):
        # нужно получить выбранный язык из view; пока оставим заглушку
        pass

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
        # (код из controller)
        pass