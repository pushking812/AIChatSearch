# aichat_search/exporters/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict


class Exporter(ABC):
    """Абстрактный базовый класс для экспортёров данных сообщения."""

    @abstractmethod
    def export(self, data: Dict[str, Any], file_path: str) -> None:
        """
        Экспортирует данные сообщения в файл.

        :param data: словарь с данными сообщения (см. prepare_data)
        :param file_path: полный путь к файлу для сохранения
        """
        pass

    @staticmethod
    def prepare_data(chat_title: str, chat_created_at, pair, message_index: int) -> Dict[str, Any]:
        """
        Подготавливает унифицированный словарь данных из модели.
        Может быть переопределён в наследниках для добавления полей.
        """
        return {
            'chat_title': chat_title,
            'chat_created_at': chat_created_at.strftime('%d-%m-%Y %H:%M') if chat_created_at else '',
            'message_index': message_index,
            'pair_index': pair.index,
            'request_text': pair.request_text,
            'response_text': pair.response_text,
            'request_time': pair.request_time.strftime('%d-%m-%Y %H:%M') if pair.request_time else '',
            'response_time': pair.response_time.strftime('%d-%m-%Y %H:%M') if pair.response_time else '',
            'request_node_id': pair.request_node_id,
            'response_node_id': pair.response_node_id,
            'modified': pair.modified,
        }