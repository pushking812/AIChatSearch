# aichat_search/gui.py

"""Точка входа в графический интерфейс AI Chat Archive Search.

Этот файл обеспечивает обратную совместимость и делегирует создание окна
новому классу Application из пакета gui_components.
"""

from .gui_components import Application

def run_gui():
    """Запустить главное окно приложения."""
    app = Application()
    app.mainloop()
