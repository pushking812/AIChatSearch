# aichat_search/services/session_manager.py

import pickle
import os
from datetime import datetime
from typing import List, Optional, Dict, Any, Union

from ..model import DataSource, Chat, MessagePair
from ..utils import parse_datetime


class SessionManager:
    """
    Управляет сохранением и загрузкой сессии (списка источников).
    Текущая реализация использует pickle для сериализации, но данные
    преобразуются в словарь с версией, что позволяет в будущем
    легко переключиться на JSON.
    Поддерживается обратная совместимость со старым форматом (список источников).
    """

    _CURRENT_VERSION = "1.0"

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

    def _from_dict(self, data: Union[List, Dict, Any]) -> Optional[List[DataSource]]:
        """
        Восстанавливает список источников из загруженных данных.
        Поддерживает старый формат (список) и новый (словарь с версией).
        """
        # Старый формат: просто список источников
        if isinstance(data, list):
            print("Загружен старый формат сессии (список). При следующем сохранении формат будет обновлён.")
            # Проверим, что все элементы действительно DataSource (опционально)
            # В старом формате так и было
            return data

        # Новый формат: словарь
        if isinstance(data, dict):
            version = data.get("version")
            if version != self._CURRENT_VERSION:
                # В будущем здесь можно добавить логику миграции
                print(f"Предупреждение: версия файла сессии ({version}) отличается от текущей ({self._CURRENT_VERSION})")

            sources_data = data.get("sources", [])
            sources = []
            for src_data in sources_data:
                source = self._source_from_dict(src_data)
                if source:
                    sources.append(source)
            return sources

        # Неизвестный формат
        print("Ошибка: неизвестный формат данных сессии.")
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
            print(f"Ошибка загрузки источника: {e}")
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
            print(f"Ошибка загрузки чата: {e}")
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
            print(f"Ошибка загрузки пары: {e}")
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