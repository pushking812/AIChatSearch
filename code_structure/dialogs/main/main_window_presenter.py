# code_structure/ui/code_structure/main_window_presenter.py


from code_structure.dialogs.dialog_interfaces import CodeStructureView
from code_structure.facades import (
    StructureDataProvider, ModuleAssignmentManager, PersistenceManager
)
from code_structure.dialogs.dto import (
    CodeStructureInitDTO, TreeDisplayNode
)

import logging
from code_structure.utils.logger import get_logger
logger = get_logger(__name__, level=logging.WARNING)


class CodeStructurePresenter:
    def __init__(
        self,
        view: CodeStructureView,
        data_provider: StructureDataProvider,
        module_manager: ModuleAssignmentManager,
        persistence_manager: PersistenceManager
    ):
        self.view = view
        self.data_provider = data_provider
        self.module_manager = module_manager
        self.persistence_manager = persistence_manager

        # Загрузка блоков и инициализация
        self.data_provider.load_blocks()
        # Обработка ошибок (диалоги исправления)
        self._handle_error_blocks()
        # Обновление интерфейса после загрузки
        self._update_view(self.data_provider.get_initial_data())
        # Автоматическое открытие диалога назначения модулей, если есть неопределённые блоки
        self._maybe_show_module_dialog()

    # ---------- Обновление UI ----------
    def _update_view(self, data: CodeStructureInitDTO):
        self.view.display_merged_tree(data.tree)
        self.view.set_flat_list(data.flat_items)
        self.view.set_type_combo_values(data.languages)
        self.view.set_type_combo_state(len(data.languages) > 1)
        self.view.set_module_button_state(data.has_unknown_blocks)

    # ---------- Обработка синтаксических ошибок ----------
    def _handle_error_blocks(self):
        error_blocks = self.data_provider.get_error_blocks()
        if not error_blocks:
            return

        from code_structure.dialogs import ErrorBlockDialog
        from code_structure.dialogs.dto import ErrorBlockInput

        for block in error_blocks:
            input_data = ErrorBlockInput(
                block_id=block.block_id,
                original_code=block.content,
                language=block.language
            )
            dialog = ErrorBlockDialog(self.view, input_data)
            self.view.wait_window(dialog)
            if dialog.result is not None:
                self.data_provider.fix_error_block(block.block_id, dialog.result)

        # После исправления всех ошибок перестраиваем структуру и обновляем отображение
        self.data_provider.rebuild_structure()
        self._update_view(self.data_provider.get_initial_data())

    # ---------- Автоматическое открытие диалога назначения модулей ----------
    def _maybe_show_module_dialog(self):
        if self.data_provider.has_unknown_blocks():
            self._show_module_dialog()

    # ---------- Обработка выбора узлов ----------
    def on_merged_node_selected(self, node_data: TreeDisplayNode):
        code = self.data_provider.get_code_for_node(node_data)
        self.view.display_merged_code(code or "")

    def on_flat_node_selected(self, block_id: str):
        code = self.data_provider.get_code_for_block(block_id)
        self.view.display_code(code or "")

    # ---------- Фильтр "Только локальные импорты" ----------
    def on_local_only_toggled(self, local_only: bool):
        refresh_data = self.data_provider.refresh(local_only)
        self.view.display_merged_tree(refresh_data.tree)
        self.view.set_flat_list(refresh_data.flat_items)

    # ---------- Выбор языка ----------
    def on_type_selected(self, event):
        # Язык пока не влияет на отображение, просто сбрасываем код
        self.view.display_code("")

    # ---------- Управление модулями ----------
    def on_reset_module_assignments(self):
        self.module_manager.reset_assignments()
        refresh_data = self.data_provider.refresh(self.view.get_local_only())
        self.view.display_merged_tree(refresh_data.tree)
        self.view.set_flat_list(refresh_data.flat_items)
        # После сброса могут появиться неопределённые блоки, показываем диалог
        if self.data_provider.has_unknown_blocks():
            self._show_module_dialog()

    def _show_module_dialog(self):
        from code_structure.dialogs import ModuleAssignmentDialog

        input_dto = self.module_manager.get_module_assignment_input(self.view.get_local_only())
        dialog = ModuleAssignmentDialog(self.view, input_dto)
        self.view.wait_window(dialog)
        if dialog.result:
            self.module_manager.apply_assignments(dialog.result.assignments)
            refresh_data = self.data_provider.refresh(self.view.get_local_only())
            self.view.display_merged_tree(refresh_data.tree)
            self.view.set_flat_list(refresh_data.flat_items)

    def on_save_structure(self):
        """Сохранение структуры модулей."""
        roots = self.data_provider.get_versioned_roots()
        self.persistence_manager.save_structure(roots, self.view)

    def on_load_structure(self):
        roots, _ = self.persistence_manager.load_structure(self.view)
        if roots is not None:
            self.data_provider.set_versioned_roots(roots)
            self._refresh_display()

    # ---------- Создание проекта (заглушка) ----------
    def on_create_project(self):
        from tkinter import messagebox
        messagebox.showinfo("Создание проекта", "Функция создания проекта будет реализована в следующей версии.")
        
    def _refresh_display(self):
        """Обновляет отображение дерева и плоского списка."""
        refresh_data = self.data_provider.refresh(self.view.get_local_only())
        self.view.display_merged_tree(refresh_data.tree)
        self.view.set_flat_list(refresh_data.flat_items)