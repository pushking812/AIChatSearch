# aichat_search/services/session_manager.py

import pickle
import os
import logging
from typing import List, Optional, Dict, Any, Union

from ..model import DataSource, Chat, MessagePair
from ..utils import parse_datetime

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Управляет сохранением и загрузкой сессии (списка источников).
    Текущая реализация использует pickle для сериализации, но данные
    преобразуются в словарь с версией, что позволяет в будущем
    легко переключиться на JSON.
    Поддерживается обратная совместимость со старым форматом (список источников).

    Формат сессии (словарь):
        {
            "version": "1.0",
            "sources": [...]
        }

    При изменении структуры данных следует увеличивать версию и добавлять
    соответствующие функции миграции в словарь _MIGRATIONS.
    """

    _CURRENT_VERSION = "1.0"

    # Словарь миграций: ключ (from_version, to_version) -> функция миграции
    # Пока пуст, в будущем будут добавляться пары для обновления формата.
    _MIGRATIONS = {}

    def __init__(self, session_path: str):
        """
        :param session_path: полный путь к файлу сессии (например, .config/session.pkl)
        """
        self.session_path = session_path

    # ------------------------------------------------------------------
    # Приватные методы преобразования в/из словаря
    # ------------------------------------------------------------------

    def _to_dict(self, sources: List[DataSource]) -> Dict[str, Any]:
        """Преобразует список источников в словарь с версией."""
        return {
            "version": self._CURRENT_VERSION,
            "sources": [self._source_to_dict(src) for src in sources]
        }

    def _source_to_dict(self, source: DataSource) -> Dict[str, Any]:
        """Преобразует один источник в словарь."""
        return {
            "file_path": source.file_path,
            "id": source.id,  # сохраняем для информации, но при загрузке не используется
            "chats": [self._chat_to_dict(chat) for chat in source.chats]
        }

    def _chat_to_dict(self, chat: Chat) -> Dict[str, Any]:
        """Преобразует чат в словарь."""
        return {
            "id": chat.id,
            "title": chat.title,
            "created_at": chat.created_at.isoformat() if chat.created_at else None,
            "updated_at": chat.updated_at.isoformat() if chat.updated_at else None,
            "pairs": [self._pair_to_dict(pair) for pair in chat.get_pairs()]
        }

    def _pair_to_dict(self, pair: MessagePair) -> Dict[str, Any]:
        """Преобразует пару сообщений в словарь."""
        return {
            "index": pair.index,
            "request_text": pair.request_text,
            "response_text": pair.response_text,
            "request_time": pair.request_time.isoformat() if pair.request_time else None,
            "response_time": pair.response_time.isoformat() if pair.response_time else None,
            "request_node_id": pair.request_node_id,
            "response_node_id": pair.response_node_id,
            "modified": pair.modified
        }

    def _migrate_if_needed(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Проверяет версию загруженных данных и при необходимости применяет миграции.
        В текущей реализации только логирует несовпадение версий.
        """
        version = data.get("version")
        if version == self._CURRENT_VERSION:
            return data

        # Если версия отсутствует или отличается, логируем предупреждение
        if version is None:
            logger.warning("Загруженные данные не содержат версии. Будет выполнена попытка загрузки в текущем формате.")
        else:
            logger.warning(f"Версия сессии {version} отличается от текущей {self._CURRENT_VERSION}. "
                           f"Попытка загрузки без миграции.")
        # В будущем здесь будет вызов цепочки миграций
        return data

    def _from_dict(self, data: Union[List, Dict, Any]) -> Optional[List[DataSource]]:
        """
        Восстанавливает список источников из загруженных данных.
        Поддерживает старый формат (список) и новый (словарь с версией).
        """
        # Старый формат: просто список источников
        if isinstance(data, list):
            logger.info("Загружен старый формат сессии (список). При следующем сохранении формат будет обновлён.")
            # Проверим, что все элементы действительно DataSource (опционально)
            # В старом формате так и было
            return data

        # Новый формат: словарь
        if isinstance(data, dict):
            # Применяем миграцию, если необходимо
            data = self._migrate_if_needed(data)

            sources_data = data.get("sources", [])
            sources = []
            for src_data in sources_data:
                source = self._source_from_dict(src_data)
                if source:
                    sources.append(source)
            return sources

        # Неизвестный формат
        logger.error("Неизвестный формат данных сессии.")
        return None

    def _source_from_dict(self, data: Dict[str, Any]) -> Optional[DataSource]:
        """Восстанавливает источник из словаря."""
        try:
            file_path = data["file_path"]
            source = DataSource(file_path)
            chats_data = data.get("chats", [])
            for chat_data in chats_data:
                chat = self._chat_from_dict(chat_data)
                if chat:
                    source.chats.append(chat)
            return source
        except (KeyError, TypeError) as e:
            logger.error(f"Ошибка загрузки источника: {e}")
            return None

    def _chat_from_dict(self, data: Dict[str, Any]) -> Optional[Chat]:
        """Восстанавливает чат из словаря."""
        try:
            chat = Chat(
                chat_id=data["id"],
                title=data["title"],
                created_at=parse_datetime(data["created_at"]),
                updated_at=parse_datetime(data["updated_at"])
            )
            pairs_data = data.get("pairs", [])
            for pair_data in pairs_data:
                pair = self._pair_from_dict(pair_data)
                if pair:
                    chat.add_pair(pair)
            return chat
        except (KeyError, TypeError) as e:
            logger.error(f"Ошибка загрузки чата: {e}")
            return None

    def _pair_from_dict(self, data: Dict[str, Any]) -> Optional[MessagePair]:
        """Восстанавливает пару сообщений из словаря."""
        try:
            pair = MessagePair(
                index=data["index"],
                request_text=data["request_text"],
                response_text=data["response_text"],
                request_time=parse_datetime(data["request_time"]),
                response_time=parse_datetime(data["response_time"]),
                request_node_id=data["request_node_id"],
                response_node_id=data["response_node_id"]
            )
            pair.modified = data.get("modified", False)
            return pair
        except (KeyError, TypeError) as e:
            logger.error(f"Ошибка загрузки пары: {e}")
            return None

    # ------------------------------------------------------------------
    # Публичные методы сохранения/загрузки
    # ------------------------------------------------------------------

    def save(self, sources: List[DataSource]) -> None:
        """Сохраняет список источников в файл сессии (в формате pickle, но с версионированным словарём)."""
        os.makedirs(os.path.dirname(self.session_path), exist_ok=True)
        data = self._to_dict(sources)
        with open(self.session_path, 'wb') as f:
            pickle.dump(data, f)

    def load(self) -> Optional[List[DataSource]]:
        """Загружает список источников из файла сессии. Если файла нет, возвращает None."""
        if not os.path.exists(self.session_path):
            return None
        with open(self.session_path, 'rb') as f:
            data = pickle.load(f)
        return self._from_dict(data)