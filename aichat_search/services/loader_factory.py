# aichat_search/services/loader_factory.py

from typing import Optional, Type
from .loaders import ChatLoader, DeepSeekZipLoader

# Реестр доступных загрузчиков (классы)
_LOADERS: list[Type[ChatLoader]] = [
    DeepSeekZipLoader,
    # Здесь можно добавить другие загрузчики
]


class LoaderFactory:
    """Фабрика для получения подходящего загрузчика по файлу."""

    @staticmethod
    def get_loader(file_path: str) -> Optional[ChatLoader]:
        """
        Перебирает все зарегистрированные загрузчики, вызывая их can_load.
        Возвращает экземпляр первого подходящего загрузчика или None.
        """
        for loader_cls in _LOADERS:
            if loader_cls.can_load(file_path):
                return loader_cls()
        return None