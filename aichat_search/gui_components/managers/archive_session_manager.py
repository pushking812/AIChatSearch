# aichat_search/gui_components/managers/archive_session_manager.py

import tkinter as tk
from tkinter import filedialog, messagebox

class ArchiveSessionManager:
    def __init__(self, controller, tree_panel, detail_panel, on_update_callback, on_clear_interface):
        self.controller = controller
        self.tree_panel = tree_panel
        self.detail_panel = detail_panel
        self.on_update_callback = on_update_callback
        self.on_clear_interface = on_clear_interface

    def add_archive(self):
        file_path = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")])
        if not file_path:
            return
        try:
            added, new_cnt, new_msg, upd_cnt, upd_msg = self.controller.add_source(file_path)
            if added:
                self.on_update_callback()
                parts = []
                if new_cnt:
                    parts.append(f"Добавлено чатов: {new_cnt} шт. ({new_msg} сообщ.)")
                if upd_cnt:
                    parts.append(f"Обновлено чатов: {upd_cnt} шт. ({upd_msg} сообщ.)")
                message = "\n".join(parts)
                messagebox.showinfo("Добавление архива", message)
                self.controller.save_session()
            else:
                messagebox.showinfo("Добавление архива",
                                    "Все чаты из этого архива уже загружены и не содержат новых сообщений.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить архив:\n{e}")

    def new_session(self):
        self.controller.clear_all_sources()
        self.controller.reset_current_pair()
        self.on_clear_interface()
        self.on_update_callback()  # Добавлено: обновляем список чатов

    def save_current_pair(self):
        current_pair = self.controller.get_current_pair()
        if current_pair is None:
            messagebox.showwarning("Предупреждение", "Нет выбранной пары для сохранения.")
            return

        new_request, new_response = self.detail_panel.get_current_texts()
        modified = False

        if new_request != current_pair.request_text:
            current_pair.request_text = new_request
            modified = True
        if new_response != current_pair.response_text:
            current_pair.response_text = new_response
            modified = True

        if modified:
            current_pair.modified = True
            self.tree_panel.update_pair_item(current_pair)
            messagebox.showinfo("Сохранение", "Изменения сохранены.")
            self.controller.save_session()
        else:
            messagebox.showinfo("Сохранение", "Нет изменений для сохранения.")