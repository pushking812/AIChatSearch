# aichat_search/gui_components/group_management/group_dialog.py

import tkinter as tk
from tkinter import ttk, messagebox

class GroupDialog(tk.Toplevel):
    def __init__(self, parent, controller, on_update_callback):
        super().__init__(parent)
        self.controller = controller
        self.on_update = on_update_callback
        self.title("Управление группами")
        self.geometry("400x300")
        self.transient(parent)
        self.grab_set()
        self._create_widgets()
        self._refresh_list()

    def _create_widgets(self):
        tk.Label(self, text="Существующие группы:").pack(pady=5)
        list_frame = tk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        # Добавлен параметр exportselection=False для сохранения выделения при потере фокуса
        self.listbox = tk.Listbox(list_frame, exportselection=False)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(list_frame, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.bind('<<ListboxSelect>>', self._on_select)

        tk.Label(self, text="Название группы:").pack(pady=5)
        self.entry = tk.Entry(self)
        self.entry.pack(fill=tk.X, padx=5)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Добавить", command=self._add_group).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Переименовать", command=self._rename_group).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Удалить", command=self._delete_group).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Закрыть", command=self.destroy).pack(side=tk.LEFT, padx=5)

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for g in self.controller.get_all_groups():
            self.listbox.insert(tk.END, g)

    def _on_select(self, event):
        sel = self.listbox.curselection()
        if sel:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, self.listbox.get(sel[0]))

    def _add_group(self):
        name = self.entry.get().strip()
        if not name:
            messagebox.showwarning("Ошибка", "Имя не может быть пустым")
            return
        if self.controller.add_group(name):
            self._refresh_list()
        else:
            messagebox.showerror("Ошибка", "Группа уже существует")

    def _rename_group(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("Ошибка", "Выберите группу")
            return
        old = self.listbox.get(sel[0])
        new = self.entry.get().strip()
        if not new:
            messagebox.showwarning("Ошибка", "Новое имя не может быть пустым")
            return
        if self.controller.rename_group(old, new):
            self._refresh_list()
            self.on_update()
        else:
            messagebox.showerror("Ошибка", "Невозможно переименовать (возможно, группа с таким именем уже существует)")

    def _delete_group(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("Ошибка", "Выберите группу")
            return
        group = self.listbox.get(sel[0])
        if messagebox.askyesno("Подтверждение", f"Удалить группу '{group}'?"):
            self.controller.delete_group(group)
            self._refresh_list()
            self.entry.delete(0, tk.END)
            self.on_update()