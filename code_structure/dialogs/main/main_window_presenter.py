# code_structure/dialogs/main/main_window_presenter.py

from code_structure.dialogs.dialog_interfaces import CodeStructureView
from code_structure.facades import (
    StructureDataProvider, ModuleAssignmentManager, PersistenceManager
)
from code_structure.dialogs.dto import (
    CodeStructureInitDTO, TreeDisplayNode, AmbiguityInfo
)

import logging
from code_structure.utils.logger import get_logger
logger = get_logger(__name__, level=logging.INFO)


class CodeStructurePresenter:
    def __init__(
        self,
        view: CodeStructureView,
        data_provider: StructureDataProvider,
        module_manager: ModuleAssignmentManager,
        persistence_manager: PersistenceManager,
        dialog_factory
    ):
        self.view = view
        self.data_provider = data_provider
        self.module_manager = module_manager
        self.persistence_manager = persistence_manager
        self.dialog_factory = dialog_factory
        self._dialog_opened = False

        # Загрузка блоков с возможным разрешением неоднозначностей
        ambiguities = self.data_provider.load_blocks()
        if ambiguities:
            resolved = self._resolve_ambiguities(ambiguities)
            if resolved is None:
                # Пользователь отменил, закрываем окно
                self.view.destroy()
                return
            # Повторная загрузка с разрешёнными путями
            self.data_provider.load_blocks(resolved)

        self._handle_error_blocks()
        self._update_view(self.data_provider.get_initial_data())
        self._maybe_show_module_dialog()

    def _resolve_ambiguities(self, ambiguities: list[AmbiguityInfo]):
        """Показывает диалог разрешения неоднозначностей и возвращает выбранные пути."""
        dialog = self.dialog_factory.create_ambiguity_dialog(self.view, ambiguities)
        self.view.wait_window(dialog)
        return dialog.result

    def _update_view(self, data: CodeStructureInitDTO):
        self.view.display_merged_tree(data.tree)
        self.view.set_flat_list(data.flat_items)
        self.view.set_type_combo_values(data.languages)
        self.view.set_type_combo_state(len(data.languages) > 1)
        self.view.set_module_button_state(data.has_unknown_blocks)
        self.view.set_fix_errors_button_state(data.has_error_blocks)
        logger.info(f"_update_view: has_error_blocks={data.has_error_blocks}")

    def _handle_error_blocks(self):
        error_blocks = self.data_provider.get_error_blocks()
        if not error_blocks:
            logger.info("Нет блоков с ошибками для исправления")
            return

        from code_structure.dialogs.dto import ErrorBlockInput

        for block in error_blocks:
            input_data = ErrorBlockInput(
                block_id=block.id,
                original_code=block.content,
                language=block.language,
                chat=block.chat,
                message_pair=block.message_pair
            )
            dialog = self.dialog_factory.create_error_block_dialog(self.view, input_data)
            self.view.wait_window(dialog)
            if dialog.result is not None:
                self.data_provider.fix_error_block(block.id, dialog.result)
                logger.info(f"Блок {block.id} исправлен")

        current_data = self.data_provider.get_initial_data()
        logger.info(f"После исправления ошибок: has_unknown_blocks={current_data.has_unknown_blocks}, has_error_blocks={current_data.has_error_blocks}")
        self._update_view(current_data)

    def _maybe_show_module_dialog(self):
        if self.data_provider.has_unknown_blocks() and not self._dialog_opened:
            self._dialog_opened = True
            self._show_module_dialog()

    def on_merged_node_selected(self, node_data: TreeDisplayNode, item_to_data: dict = None):
        code = self.data_provider.get_code_for_node(node_data)
        self.view.display_merged_code(code or "")

        filter_name = None
        if node_data.type in ('function', 'method'):
            filter_name = node_data.text
        elif node_data.type == 'version' and item_to_data:
            for item, nd in item_to_data.items():
                if nd == node_data:
                    parent_item = self.view.merged_tree.parent(item)
                    if parent_item and parent_item in item_to_data:
                        parent_node = item_to_data[parent_item]
                        if parent_node.type in ('function', 'method'):
                            filter_name = parent_node.text
                    break

        if filter_name:
            self.view.set_flat_filter("Узел", filter_name)
        else:
            self.view.clear_flat_filter()

    def on_flat_node_selected(self, block_id: str, lines_str: str):
        block = self.data_provider.block_service.get_new_block(block_id)
        if block is None:
            self.view.display_code("", "python", None, None)
            return

        code = block.content
        start_line = None
        end_line = None
        if lines_str and '-' in lines_str:
            parts = lines_str.split('-')
            try:
                start_line = int(parts[0])
                end_line = int(parts[1]) if len(parts) > 1 else start_line
            except ValueError:
                pass
        self.view.display_code(code or "", block.language, start_line, end_line)

    def on_local_only_toggled(self, local_only: bool):
        refresh_data = self.data_provider.refresh(local_only)
        self.view.display_merged_tree(refresh_data.tree)
        self.view.set_flat_list(refresh_data.flat_items)

    def on_type_selected(self, event):
        self.view.display_code("", "python", None, None)

    def on_reset_module_assignments(self):
        self.module_manager.reset_assignments()
        refresh_data = self.data_provider.refresh(self.view.get_local_only())
        self.view.display_merged_tree(refresh_data.tree)
        self.view.set_flat_list(refresh_data.flat_items)
        if self.data_provider.has_unknown_blocks():
            self._show_module_dialog()

    def _show_module_dialog(self):
        input_dto = self.module_manager.get_module_assignment_input(self.view.get_local_only())
        dialog = self.dialog_factory.create_module_assignment_dialog(self.view, input_dto)
        self.view.wait_window(dialog)
        if dialog.result:
            self.module_manager.apply_assignments(
                dialog.result.assignments,
                dialog.result.deleted_block_ids
            )
            refresh_data = self.data_provider.refresh(self.view.get_local_only())
            self.view.display_merged_tree(refresh_data.tree)
            self.view.set_flat_list(refresh_data.flat_items)

    def on_fix_errors(self):
        error_blocks = self.data_provider.get_error_blocks()
        if not error_blocks:
            self.view.show_error("Нет блоков с синтаксическими ошибками.")
            return
        self._handle_error_blocks()
        self._refresh_display()

    def on_save_structure(self):
        roots = self.data_provider.get_versioned_roots()
        self.persistence_manager.save_structure(roots, self.view)

    def on_load_structure(self):
        roots, _ = self.persistence_manager.load_structure(self.view)
        if roots is not None:
            self.data_provider.set_versioned_roots(roots)
            self._refresh_display()

    def on_create_project(self):
        from tkinter import messagebox
        messagebox.showinfo("Создание проекта", "Функция создания проекта будет реализована в следующей версии.")

    def _refresh_display(self):
        refresh_data = self.data_provider.refresh(self.view.get_local_only())
        self.view.display_merged_tree(refresh_data.tree)
        self.view.set_flat_list(refresh_data.flat_items)

    def on_open_module_dialog(self):
        self._show_module_dialog()