# aichat_search/gui_components/managers/navigation_manager.py

import tkinter as tk

class NavigationManager:
    def __init__(self, controller, detail_panel, prev_button, next_button, position_label):
        self.controller = controller
        self.detail_panel = detail_panel
        self.prev_button = prev_button
        self.next_button = next_button
        self.position_label = position_label

    def update_buttons(self):
        can_prev, can_next = self.controller.get_nav_state()
        self.prev_button.config(state=tk.NORMAL if can_prev else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if can_next else tk.DISABLED)

    def update_position_label(self):
        title, index, total = self.controller.get_position_info()
        if title is None:
            self.position_label.config(text="")
        else:
            self.position_label.config(text=f"Чат: {title} | Сообщение {index} из {total}")

    def prev(self):
        pair = self.controller.prev_pair()
        if pair:
            self.detail_panel.display_pair(pair)
            self.update_position_label()
            self.update_buttons()

    def next(self):
        pair = self.controller.next_pair()
        if pair:
            self.detail_panel.display_pair(pair)
            self.update_position_label()
            self.update_buttons()