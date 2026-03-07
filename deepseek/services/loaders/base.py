# deepseek/services/loaders/base.py

from abc import ABC, abstractmethod
from typing import List
from ...model import Chat


class ChatLoader(ABC):
    """Абстрактный базовый класс для загрузчиков чатов из различных форматов."""

    @classmethod
    @abstractmethod
    def can_load(cls, file_path: str) -> bool:
        """
        Проверяет, может ли данный загрузчик обработать указанный файл.
        Анализирует расширение, имя файла или содержимое (без полной загрузки).
        """
        pass

    @abstractmethod
    def load(self, file_path: str) -> List[Chat]:
        """
        Загружает и парсит файл, возвращая список чатов.
        Должен выбрасывать исключения при ошибках загрузки или неверном формате.
        """
        pass