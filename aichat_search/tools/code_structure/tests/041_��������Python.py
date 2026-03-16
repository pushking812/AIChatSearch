class MessageTreePanel:
    # ... существующий код ...

    def _clear(self):
        """Очистить дерево и карту."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree_item_map.clear()

    def clear(self):
        """Публичный метод для очистки дерева."""
        self._clear()