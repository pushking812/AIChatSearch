# aichat_search/tools/code_structure/ui/module_assignment_presenter.py

import re
import logging
from typing import List, Dict, Any, Optional

from aichat_search.tools.code_structure.ui.dialog_interfaces import ModuleAssignmentView
from aichat_search.tools.code_structure.core.tree_builder import TreeBuilder

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class ModuleAssignmentPresenter:
    """Презентер для диалога назначения модулей."""
    
    def __init__(self, view: ModuleAssignmentView, controller):
        self.view = view
        self.controller = controller
        
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
        """Инициализация данными."""
        self.unknown_blocks = unknown_blocks
        self.module_info = module_info
        self.module_code_map = module_code_map
        self.module_containers = module_containers
        self.known_modules = [info['name'] for info in module_info]
        
        if unknown_blocks:
            self.current_block_id = unknown_blocks[0]['id']
        
        # Обновляем представление
        self._refresh_view()
    
    def _refresh_view(self):
        """Обновляет все элементы представления."""
        # Устанавливаем списки блоков и модулей
        block_display_names = [block['display_name'] for block in self.unknown_blocks]
        self.view.set_blocks([{'id': b['id'], 'display_name': b['display_name']} 
                              for b in self.unknown_blocks])
        
        module_display_names = []
        for info in self.module_info:
            if info['source']:
                module_display_names.append(f"{info['name']} (из {info['source']})")
            else:
                module_display_names.append(info['name'])
        self.view.set_modules(self.module_info, self.module_code_map)
        
        # Строим и устанавливаем дерево
        if self.module_containers:
            tree_data = self.tree_builder.build_display_tree(self.module_containers)
            self.view.set_tree_data(tree_data)
        
        # Обновляем отображение текущего блока
        self._update_current_block_display()
    
    def _update_current_block_display(self):
        """Обновляет отображение текущего блока."""
        if not self.unknown_blocks or self.current_block_index >= len(self.unknown_blocks):
            return
        
        block = self.unknown_blocks[self.current_block_index]
        self.view.show_block_code(block['content'])
        
        # Восстанавливаем предыдущее назначение, если есть
        if self.current_block_id in self.assignments:
            assigned_module = self.assignments[self.current_block_id]
            self.view.update_assignment_label(assigned_module)
            self.current_applied = assigned_module
        else:
            self.view.update_assignment_label("")
            self.current_applied = ""
        
        self.view.enable_apply_button(False)
    
    def on_block_selected(self, block_id: str):
        """Обработчик выбора блока."""
        for idx, block in enumerate(self.unknown_blocks):
            if block['id'] == block_id:
                self.current_block_index = idx
                self.current_block_id = block_id
                self._update_current_block_display()
                break
    
    def on_module_selected(self, module_name: str):
        """Обработчик выбора модуля в дереве."""
        # Показываем код модуля, если есть
        if module_name in self.module_code_map:
            self.view.show_module_code(self.module_code_map[module_name])
        else:
            self.view.show_module_code("")
    
    def on_action_changed(self, mode: str):
        """Обработчик изменения режима действия."""
        self.view.set_action_mode(mode)
        self._check_changes()
    
    def on_new_module_name_changed(self, name: str):
        """Обработчик изменения имени нового модуля."""
        self._check_changes()
    
    def _check_changes(self):
        """Проверяет, изменилось ли значение по сравнению с применённым."""
        current_value = self._get_current_value()
        self.view.enable_apply_button(current_value != self.current_applied)
    
    def _get_current_value(self) -> str:
        """Возвращает текущее выбранное значение."""
        if self.view.get_action_mode() == "create_new":
            return self.view.get_new_module_name().strip()
        else:
            selected = self.view.get_selected_module()
            # Очищаем от суффикса (из ...)
            if ' (из ' in selected:
                return selected.split(' (из ')[0]
            return selected
    
    def on_apply(self):
        """Обработчик нажатия кнопки Apply."""
        if not self.current_block_id:
            return
        
        action = self.view.get_action_mode()
        
        if action == "create_new":
            new_name = self.view.get_new_module_name().strip()
            if not new_name:
                return  # Должно быть обработано во view
            if not re.match(r'^[a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)*$', new_name):
                return  # Некорректное имя
            if new_name in self.known_modules:
                return  # Уже существует
            
            # Создаём новый модуль
            self.known_modules.append(new_name)
            self.known_modules.sort()
            
            current_block = self.unknown_blocks[self.current_block_index]
            source_text = f"{current_block['id']} – {current_block['display_name'].split(' – ')[-1] if ' – ' in current_block['display_name'] else current_block['display_name']}"
            self.module_info.append({'name': new_name, 'source': source_text})
            self.module_code_map[new_name] = current_block['content']
            
            self.assignments[self.current_block_id] = new_name
            self.changed = True
            
            # Обновляем представление
            self.view.set_modules(self.module_info, self.module_code_map)
            
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
    
    def on_ok(self):
        """Обработчик нажатия кнопки OK."""
        return self.assignments.copy()
    
    def on_cancel(self):
        """Обработчик нажатия кнопки Cancel."""
        return None
    
    def on_close(self):
        """Обработчик закрытия окна."""
        if self.changed:
            # Запрос подтверждения должен быть во view
            return self.changed
        return False