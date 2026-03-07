# deepseek/services/loader_factory.py

import os
from typing import Optional
from .loaders import ChatLoader, DeepSeekZipLoader


class LoaderFactory:
    """Фабрика для получения подходящего загрузчика по файлу."""

    @staticmethod
    def get_loader(file_path: str) -> Optional[ChatLoader]:
        """
        Возвращает экземпляр загрузчика, подходящего для данного файла,
        или None, если формат не поддерживается.
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.zip':
            return DeepSeekZipLoader()
        # Здесь можно добавить другие условия для других форматов
        return None