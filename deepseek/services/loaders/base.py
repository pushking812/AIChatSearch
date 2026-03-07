# deepseek/services/loaders/base.py

from abc import ABC, abstractmethod
from typing import List
from ...model import Chat


class ChatLoader(ABC):
    """Абстрактный базовый класс для загрузчиков чатов из различных форматов."""

    @abstractmethod
    def load(self, file_path: str) -> List[Chat]:
        """
        Загружает и парсит файл, возвращая список чатов.
        Должен выбрасывать исключения при ошибках загрузки или неверном формате.
        """
        pass