# deepseek/controller.py

import os
from typing import List, Dict, Optional, Set
from datetime import datetime

from .gui_components.constants import CONFIG_DIR, SESSION_FILE
from .model import DataSource, Chat, MessagePair
from .services.loader_factory import LoaderFactory   # новый импорт
from .services.search_service import SearchService
from .services.session_manager import SessionManager


class ChatController:
    def __init__(self) -> None:
        self.sources: List[DataSource] = []
        self._chat_ref_to_source: Dict[int, DataSource] = {}
        self._current_filter_query: str = ""

        self.chats: List[Chat] = []
        self.filtered_chats: List[Chat] = []

        self.current_chat: Optional[Chat] = None
        self.current_chat_pairs: List[MessagePair] = []
        self.current_index_in_chat: Optional[int] = None

        self._reset_search_state()

        config_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', CONFIG_DIR))
        self.session_path = os.path.abspath(os.path.join(config_dir, SESSION_FILE))

        self._search_service = SearchService()
        self._session_manager = SessionManager(self.session_path)

    # ---------- DATA ----------

    def _reset_search_state(self) -> None:
        self.visible_pairs = []
        self.search_active = False

    def _reset_navigation(self) -> None:
        self.current_chat = None
        self.current_chat_pairs = []
        self.current_index_in_chat = None

    def get_filtered_chats(self) -> List[Chat]:
        return self.filtered_chats

    # ---------- МЕТОДЫ ДЛЯ ИСТОЧНИКОВ ----------

    def add_source(self, file_path: str) -> tuple[List[Chat], int, int, int, int]:
        """
        Загружает архив, добавляет только новые сообщения.
        Возвращает кортеж:
            (список добавленных чатов,
             количество новых чатов,
             количество новых сообщений в новых чатах,
             количество обновлённых чатов,
             количество новых сообщений в обновлённых чатах)
        """
        loader = LoaderFactory.get_loader(file_path)
        if loader is None:
            raise ValueError(f"Unsupported file format: {file_path}")

        new_chats = loader.load(file_path)
        chats_to_add = self._extract_new_messages_chats(new_chats)

        # Статистика
        new_chats_count = 0
        new_messages_in_new = 0
        updated_chats_count = 0
        new_messages_in_updated = 0

        for chat in chats_to_add:
            existing = self._find_existing_chats(chat.id)
            if not existing:
                new_chats_count += 1
                new_messages_in_new += len(chat.get_pairs())
            else:
                updated_chats_count += 1
                new_messages_in_updated += len(chat.get_pairs())

        if chats_to_add:
            self._add_source_with_chats(chats_to_add, file_path)

        return chats_to_add, new_chats_count, new_messages_in_new, updated_chats_count, new_messages_in_updated

    def _load_new_chats(self, file_path: str) -> List[Chat]:
        return load_from_zip(file_path)

    def _find_existing_chats(self, chat_id: str) -> List[Chat]:
        """Возвращает список всех уже загруженных чатов с указанным ID."""
        existing = []
        for source in self.sources:
            for chat in source.chats:
                if chat.id == chat_id:
                    existing.append(chat)
        return existing

    def _collect_existing_indices(self, chat_id: str) -> Set[str]:
        """Собирает все индексы пар сообщений из всех существующих версий чата."""
        indices = set()
        for chat in self._find_existing_chats(chat_id):
            for pair in chat.get_pairs():
                indices.add(pair.index)
        return indices

    def _extract_new_messages_chats(self, new_chats: List[Chat]) -> List[Chat]:
        """
        Для каждого нового чата создаёт новый объект Chat, содержащий только те пары,
        индексы которых отсутствуют во всех ранее загруженных версиях этого чата.
        Если новых сообщений нет, чат не добавляется.
        """
        result = []
        for new_chat in new_chats:
            existing_indices = self._collect_existing_indices(new_chat.id)
            new_pairs = [pair for pair in new_chat.get_pairs() if pair.index not in existing_indices]

            if new_pairs:
                # Создаём новый чат с теми же метаданными, но только с новыми парами
                delta_chat = Chat(
                    chat_id=new_chat.id,
                    title=new_chat.title,
                    created_at=new_chat.created_at,
                    updated_at=new_chat.updated_at
                )
                for pair in new_pairs:
                    delta_chat.add_pair(pair)
                result.append(delta_chat)
            # else: полностью дублирующийся чат игнорируется
        return result

    def _add_source_with_chats(self, added_chats: List[Chat], file_path: str) -> None:
        source = DataSource(file_path)
        source.chats = added_chats
        self.sources.append(source)

        for chat in added_chats:
            self._chat_ref_to_source[id(chat)] = source

        self._rebuild_filtered_chats()

    def clear_all_sources(self) -> None:
        self.sources.clear()
        self._chat_ref_to_source.clear()
        self._current_filter_query = ""
        self._rebuild_filtered_chats()

    def _rebuild_filtered_chats(self) -> None:
        self._collect_all_chats()
        self._apply_filter()

    def _collect_all_chats(self) -> None:
        all_chats: List[Chat] = []
        for source in self.sources:
            all_chats.extend(source.chats)
        self.chats = all_chats

    def _apply_filter(self) -> None:
        query = self._current_filter_query.lower().strip()
        if query:
            self.filtered_chats = [
                chat for chat in self.chats
                if query in chat.title.lower()
            ]
        else:
            self.filtered_chats = list(self.chats)
        self._reset_navigation()

    def get_source_name(self, chat: Chat) -> str:
        source = self._chat_ref_to_source.get(id(chat))
        if source:
            if source.file_path != "Imported":
                return os.path.basename(source.file_path)
            else:
                return "Imported"
        return "Unknown"

    # ---------- FILTER ----------

    def filter_chats(self, query: str) -> None:
        self._current_filter_query = (query or "").strip()
        self._rebuild_filtered_chats()

    # ---------- SEARCH ----------

    def search(self, chat: Chat, query: str, field: str) -> List[MessagePair]:
        return self._search_service.search(chat, query, field)

    def search_with_positions(self, chat: Chat, query: str, field: str) -> List:
        return self._search_service.search_with_positions(chat, query, field)

    # ---------- SELECT MESSAGE ----------

    def select_pair(self, chat: Chat, pair: MessagePair) -> Optional[MessagePair]:
        pairs = chat.get_pairs()
        for i, p in enumerate(pairs):
            if p is pair:
                self.current_chat = chat
                self.current_chat_pairs = pairs
                self.current_index_in_chat = i
                return p
        return None

    # ---------- NAVIGATION ----------

    def prev_pair(self) -> Optional[MessagePair]:
        if self.current_index_in_chat is None:
            return None
        if self.current_index_in_chat > 0:
            self.current_index_in_chat -= 1
            return self.current_chat_pairs[self.current_index_in_chat]
        return None

    def next_pair(self) -> Optional[MessagePair]:
        if self.current_index_in_chat is None:
            return None
        if self.current_index_in_chat < len(self.current_chat_pairs) - 1:
            self.current_index_in_chat += 1
            return self.current_chat_pairs[self.current_index_in_chat]
        return None

    def get_nav_state(self) -> tuple[bool, bool]:
        if self.current_index_in_chat is None:
            return False, False
        return (
            self.current_index_in_chat > 0,
            self.current_index_in_chat < len(self.current_chat_pairs) - 1,
        )

    def get_position_info(self) -> tuple[Optional[str], Optional[int], Optional[int]]:
        if self.current_chat is None or self.current_index_in_chat is None:
            return None, None, None
        return (
            self.current_chat.title,
            self.current_index_in_chat + 1,
            len(self.current_chat_pairs),
        )

    def get_current_pair(self) -> Optional[MessagePair]:
        if self.current_chat is None or self.current_index_in_chat is None:
            return None
        if self.current_index_in_chat < 0 or self.current_index_in_chat >= len(self.current_chat_pairs):
            return None
        return self.current_chat_pairs[self.current_index_in_chat]

    # ---------- СОХРАНЕНИЕ И ЗАГРУЗКА СЕССИИ ----------

    def save_session(self) -> None:
        self._session_manager.save(self.sources)

    def load_session(self) -> None:
        sources = self._session_manager.load()
        if sources is not None:
            self.sources = sources
            self._chat_ref_to_source.clear()
            for source in self.sources:
                for chat in source.chats:
                    self._chat_ref_to_source[id(chat)] = source
            self._rebuild_filtered_chats()
            
    # deepseek/controller.py (фрагмент)

    def get_source_info(self, chat: Chat) -> tuple[str, Optional[str]]:
        """
        Возвращает кортеж (имя_источника, строка_времени_файла) для чата.
        Время файла вычисляется по file_path источника.
        """
        source = self._chat_ref_to_source.get(id(chat))
        if source:
            name = os.path.basename(source.file_path) if source.file_path != "Imported" else "Imported"
            time_str = None
            if source.file_path != "Imported" and os.path.exists(source.file_path):
                try:
                    ts = os.path.getctime(source.file_path)
                    time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
                except OSError:
                    pass
            return name, time_str
        return "Unknown", None