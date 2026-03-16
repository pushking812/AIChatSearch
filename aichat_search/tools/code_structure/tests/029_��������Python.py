def clear(self):
    """Удаляет все элементы из дерева."""
    for item in self.tree.get_children():
        self.tree.delete(item)