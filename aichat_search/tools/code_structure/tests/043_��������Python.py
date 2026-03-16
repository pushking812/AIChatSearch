def clear(self):
    """Очищает текстовые поля и позиционную метку."""
    self.request_text.delete(1.0, tk.END)
    self.response_text.delete(1.0, tk.END)
    self.set_position_label("")