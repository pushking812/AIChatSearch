class MessageTreePanel:
    def __init__(self, parent, controller, on_select):
        # ... инициализация ...
        self.tree = ttk.Treeview(parent, ...)
        # ...

    def display_chats(self, chats):
        # ... заполнение дерева ...
        pass

    def display_search_results(self, results):
        # ... отображение результатов поиска ...
        pass

    def clear(self):
        """Удаляет все элементы из дерева."""
        for item in self.tree.get_children():
            self.tree.delete(item)