# code_structure/dialogs/module_assignment/module_assignment_presenter.py

import re
import logging
from typing import Dict, Optional

from code_structure.dialogs.dialog_interfaces import ModuleAssignmentView
from code_structure.dialogs.dto import (
    KnownModuleInfo, TreeDisplayNode,
    ModuleAssignmentInput, ModuleAssignmentOutput
)

from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level = logging.WARNING)


class ModuleAssignmentPresenter:
    def __init__(self, view: ModuleAssignmentView):
        self.view = view
        self.input: Optional[ModuleAssignmentInput] = None
        self.assignments: Dict[str, str] = {}
        self.current_block_index = 0
        self.current_block_id: Optional[str] = None
        self.current_applied = ""
        self.changed = False

    def initialize(self, input_data: ModuleAssignmentInput):
        self.input = input_data
        self._refresh_view()

    def _refresh_view(self):
        self.view.set_blocks(self.input.unknown_blocks)
        self.view.set_modules(self.input.known_modules)
        self.view.set_tree_data(self.input.module_tree)
        self._update_current_block_display()

    def _update_current_block_display(self):
        if not self.input or not self.input.unknown_blocks or self.current_block_index >= len(self.input.unknown_blocks):
            return
        block = self.input.unknown_blocks[self.current_block_index]
        self.view.show_block_code(block.content)
        if self.current_block_id in self.assignments:
            assigned = self.assignments[self.current_block_id]
            self.view.update_assignment_label(assigned)
            self.current_applied = assigned
        else:
            self.view.update_assignment_label("")
            self.current_applied = ""
        self.view.enable_apply_button(False)

    def on_block_selected(self, block_id: str):
        for idx, block in enumerate(self.input.unknown_blocks):
            if block.id == block_id:
                self.current_block_index = idx
                self.current_block_id = block_id
                self._update_current_block_display()
                break

    def on_module_selected(self, module_name: str):
        for mod in self.input.known_modules:
            if mod.name == module_name:
                self.view.show_module_code(mod.code)
                break
        else:
            self.view.show_module_code("")

    def on_action_changed(self, mode: str):
        self.view.set_action_mode(mode)
        self._check_changes()

    def on_new_module_name_changed(self, name: str):
        self._check_changes()

    def _check_changes(self):
        current_value = self._get_current_value()
        self.view.enable_apply_button(current_value != self.current_applied)

    def _get_current_value(self) -> str:
        if self.view.get_action_mode() == "create_new":
            return self.view.get_new_module_name().strip()
        else:
            selected = self.view.get_selected_module()
            if ' (из ' in selected:
                return selected.split(' (из ')[0]
            return selected

    def on_apply(self):
        if not self.current_block_id:
            return

        action = self.view.get_action_mode()
        if action == "create_new":
            new_name = self.view.get_new_module_name().strip()
            if not new_name or not re.match(r'^[a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)*$', new_name):
                return

            # Проверяем существование
            if any(m.name == new_name for m in self.input.known_modules):
                self.view.show_error(f"Модуль {new_name} уже существует.")
                return

            # Создаём новый модуль в DTO
            current_block = self.input.unknown_blocks[self.current_block_index]
            new_mod = KnownModuleInfo(
                name=new_name,
                source=f"{current_block.id} – {current_block.display_name.split(' – ')[-1] if ' – ' in current_block.display_name else current_block.display_name}",
                code=current_block.content
            )
            self.input.known_modules.append(new_mod)
            self.input.known_modules.sort(key=lambda m: m.name)

            # Добавляем узел в дерево (обновляем module_tree)
            self.input.module_tree = self._add_module_to_tree(self.input.module_tree, new_name)

            self.assignments[self.current_block_id] = new_name
            self.changed = True
            self._refresh_view()

        else:  # assign_existing
            selected = self.view.get_selected_module()
            if not selected:
                return
            selected_module = selected.split(' (из ')[0] if ' (из ' in selected else selected
            self.assignments[self.current_block_id] = selected_module
            self.changed = True

        self.current_applied = self.assignments[self.current_block_id]
        self.view.enable_apply_button(False)
        self.view.enable_ok_button(True)
        self.view.update_assignment_label(self.current_applied)

        # Переход к следующему блоку
        if self.current_block_index + 1 < len(self.input.unknown_blocks):
            self.current_block_index += 1
            self.current_block_id = self.input.unknown_blocks[self.current_block_index].id
            self._update_current_block_display()

    def _add_module_to_tree(self, node: TreeDisplayNode, new_module_name: str) -> TreeDisplayNode:
        """Добавляет новый модуль в дерево (создаёт пакеты при необходимости)."""
        parts = new_module_name.split('.')
        current = node
        # Ищем/создаём путь
        for i, part in enumerate(parts):
            is_last = (i == len(parts) - 1)
            # Ищем среди детей текущего узла
            found = None
            for child in current.children:
                if child.text == part:
                    found = child
                    break
            if found:
                current = found
            else:
                # Создаём новый узел
                new_node = TreeDisplayNode(
                    text=part,
                    type="module" if is_last else "package",
                    signature="",
                    version="",
                    sources=""
                )
                current.children.append(new_node)
                # Сортируем детей по имени
                current.children.sort(key=lambda x: x.text)
                current = new_node
        return node

    def on_ok(self) -> ModuleAssignmentOutput:
        return ModuleAssignmentOutput(
            assignments=self.assignments,
            updated_module_tree=self.input.module_tree
        )

    def on_cancel(self):
        return None

    def on_close(self):
        return self.changed