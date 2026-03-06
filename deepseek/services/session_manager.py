# deepseek/services/session_manager.py

import pickle
import os
from typing import List, Optional

from ..model import DataSource


class SessionManager:
    """Управляет сохранением и загрузкой сессии (списка источников) в pickle-файл."""

    def __init__(self, session_path: str):
        """
        :param session_path: полный путь к файлу сессии (например, .config/session.pkl)
        """
        self.session_path = session_path

    def save(self, sources: List[DataSource]) -> None:
        """Сохраняет список источников в файл сессии."""
        os.makedirs(os.path.dirname(self.session_path), exist_ok=True)
        with open(self.session_path, 'wb') as f:
            pickle.dump(sources, f)

    def load(self) -> Optional[List[DataSource]]:
        """Загружает список источников из файла сессии. Если файла нет, возвращает None."""
        if not os.path.exists(self.session_path):
            return None
        with open(self.session_path, 'rb') as f:
            return pickle.load(f)