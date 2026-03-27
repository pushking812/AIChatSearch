# aichat_search/tools/code_structure/ui/module_assignment_presenter.py

import re
import logging
from typing import List, Dict, Any, Optional

from aichat_search.tools.code_structure.ui.dialog_interfaces import ModuleAssignmentView
from aichat_search.tools.code_structure.core.tree_builder import TreeBuilder
from aichat_search.tools.code_structure.models.containers import ModuleContainer, PackageContainer

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class ModuleAssignmentPresenter:
    def __init__(self, view: ModuleAssignmentView):
        self.view = view
        # self.controller = controller  # больше не нужно
        
        # Данные
        self.unknown_blocks: List[Dict[str, Any]] = []
        self.module_info: List[Dict[str, Any]] = []
        self.module_code_map: Dict[str, str] = {}
        self.module_containers: Dict[str, Any] = {}
        self.assignments: Dict[str, str] = {}
        self.known_modules: List[str] = []
        
        # Состояние
        self.current_block_index = 0
        self.current_block_id: Optional[str] = None
        self.current_applied = ""
        self.changed = False
        
        # Сервисы
        self.tree_builder = TreeBuilder()
    
    def initialize(self, unknown_blocks: List[Dict[str, Any]], 
                   module_info: List[Dict[str, Any]],
                   module_code_map: Dict[str, str],
                   module_containers: Dict[str, Any]):
        self.unknown_blocks = unknown_blocks
        self.module_info = module_info
        self.module_code_map = module_code_map
        self.module_containers = module_containers
        self.known_modules = [info['name'] for info in module_info]
        
        if unknown_blocks:
            self.current_block_id = unknown_blocks[0]['id']
        
        self._refresh_view()
    
    def _refresh_view(self):
        self.view.set_blocks([{'id': b['id'], 'display_name': b['display_name']} 
                              for b in self.unknown_blocks])
        self.view.set_modules(self.module_info, self.module_code_map)
        
        if self.module_containers:
            root_node, _ = self.tree_builder.build_display_tree(self.module_containers)
            self.view.set_tree_data(root_node)
        
        self._update_current_block_display()
    
    def _update_current_block_display(self):
        if not self.unknown_blocks or self.current_block_index >= len(self.unknown_blocks):
            return
        
        block = self.unknown_blocks[self.current_block_index]
        self.view.show_block_code(block['content'])
        
        if self.current_block_id in self.assignments:
            assigned_module = self.assignments[self.current_block_id]
            self.view.update_assignment_label(assigned_module)
            self.current_applied = assigned_module
        else:
            self.view.update_assignment_label("")
            self.current_applied = ""
        
        self.view.enable_apply_button(False)
    
    def on_block_selected(self, block_id: str):
        for idx, block in enumerate(self.unknown_blocks):
            if block['id'] == block_id:
                self.current_block_index = idx
                self.current_block_id = block_id
                self._update_current_block_display()
                break
    
    def on_module_selected(self, module_name: str):
        if module_name in self.module_code_map:
            self.view.show_module_code(self.module_code_map[module_name])
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
            if not new_name:
                return
            if not re.match(r'^[a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)*$', new_name):
                return

            # Проверяем, существует ли уже такой модуль
            if new_name in self.known_modules:
                self.view.show_error(f"Модуль {new_name} уже существует. Пожалуйста, выберите его из списка.")
                return

            # Создаём новый модуль-плейсхолдер в контейнерах
            self._add_new_module_to_containers(new_name)

            # Обновляем локальные списки
            self.known_modules.append(new_name)
            self.known_modules.sort()

            current_block = self.unknown_blocks[self.current_block_index]
            source_text = f"{current_block['id']} – {current_block['display_name'].split(' – ')[-1] if ' – ' in current_block['display_name'] else current_block['display_name']}"
            self.module_info.append({'name': new_name, 'source': source_text})
            self.module_code_map[new_name] = current_block['content']

            self.assignments[self.current_block_id] = new_name
            self.changed = True

            # Обновляем дерево и списки в представлении
            self.view.set_modules(self.module_info, self.module_code_map)
            if self.module_containers:
                root_node, _ = self.tree_builder.build_display_tree(self.module_containers)
                self.view.set_tree_data(root_node)

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
        if self.current_block_index + 1 < len(self.unknown_blocks):
            self.current_block_index += 1
            self.current_block_id = self.unknown_blocks[self.current_block_index]['id']
            self._update_current_block_display()
    
    def _add_new_module_to_containers(self, full_name: str):
        """
        Добавляет новый модуль-плейсхолдер в иерархию module_containers.
        """
        parts = full_name.split('.')
        current = self.module_containers
        parent = None
        for i, part in enumerate(parts):
            is_last = (i == len(parts) - 1)
            if part not in current:
                if is_last:
                    container = ModuleContainer(part)
                    container.set_placeholder(True)
                else:
                    container = PackageContainer(part)
                current[part] = container
            else:
                container = current[part]
            
            if parent is not None:
                if container not in parent.children:
                    parent.add_child(container)
            parent = container
            # Переходим к детям
            if hasattr(container, 'children_dict'):
                current = container.children_dict
            else:
                container.children_dict = {c.name: c for c in container.children}
                current = container.children_dict
        
        # Обновляем глобальные контейнеры в контроллере, если нужно
        # Здесь мы изменили локальную копию, но контроллер должен получить обновление
        # В контроллере после закрытия диалога мы передадим module_containers обратно
    
    def on_ok(self):
        # Возвращаем назначения, а также обновлённые контейнеры
        return {
            'assignments': self.assignments.copy(),
            'module_containers': self.module_containers
        }
    
    def on_cancel(self):
        return None
    
    def on_close(self):
        if self.changed:
            return self.changed
        return False