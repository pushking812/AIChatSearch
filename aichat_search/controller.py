# aichat_search/controller.py

import os
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime

from .gui_components.constants import CONFIG_DIR, SESSION_FILE
from .model import DataSource, Chat, MessagePair
from .services.loader_factory import LoaderFactory
from .services.search_service import SearchService
from .services.session_manager import SessionManager
from .services.group_manager import GroupManager


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
        self.group_manager = GroupManager(config_dir)

        self.grouping_mode: str = "source"  # source / group / prefix

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

    def add_source(self, file_path: str) -> Tuple[List[Chat], int, int, int, int]:
        loader = LoaderFactory.get_loader(file_path)
        if loader is None:
            raise ValueError(f"Unsupported file format: {file_path}")

        new_chats = loader.load(file_path)

        # Применяем сохранённые группы к новым чатам
        for chat in new_chats:
            self.group_manager.apply_to_chat(chat)

        chats_to_add = self._extract_new_messages_chats(new_chats)

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

    def _find_existing_chats(self, chat_id: str) -> List[Chat]:
        existing = []
        for source in self.sources:
            for chat in source.chats:
                if chat.id == chat_id:
                    existing.append(chat)
        return existing

    def _collect_existing_indices(self, chat_id: str) -> Set[str]:
        indices = set()
        for chat in self._find_existing_chats(chat_id):
            for pair in chat.get_pairs():
                indices.add(pair.index)
        return indices

    def _extract_new_messages_chats(self, new_chats: List[Chat]) -> List[Chat]:
        result = []
        for new_chat in new_chats:
            existing_indices = self._collect_existing_indices(new_chat.id)
            new_pairs = [pair for pair in new_chat.get_pairs() if pair.index not in existing_indices]
            if new_pairs:
                delta_chat = Chat(
                    chat_id=new_chat.id,
                    title=new_chat.title,
                    created_at=new_chat.created_at,
                    updated_at=new_chat.updated_at
                )
                for pair in new_pairs:
                    delta_chat.add_pair(pair)
                # Копируем группу из нового чата (она уже установлена через group_manager)
                delta_chat.group = new_chat.group
                result.append(delta_chat)
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
        for source in reversed(self.sources):
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

    def get_source_info(self, chat: Chat) -> Tuple[str, Optional[str]]:
        source = self._chat_ref_to_source.get(id(chat))
        if source:
            name = os.path.basename(source.file_path) if source.file_path != "Imported" else "Imported"
            time_str = None
            if source.file_path != "Imported" and os.path.exists(source.file_path):
                try:
                    ts = os.path.getctime(source.file_path)
                    time_str = datetime.fromtimestamp(ts).strftime("%d-%m-%Y %H:%M")
                except OSError:
                    pass
            return name, time_str
        return "Unknown", None

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

    def get_nav_state(self) -> Tuple[bool, bool]:
        if self.current_index_in_chat is None:
            return False, False
        return (
            self.current_index_in_chat > 0,
            self.current_index_in_chat < len(self.current_chat_pairs) - 1,
        )

    def get_position_info(self) -> Tuple[Optional[str], Optional[int], Optional[int]]:
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
                    # Восстанавливаем группу из group_manager
                    self.group_manager.apply_to_chat(chat)
            self._rebuild_filtered_chats()

    # ---------- РАБОТА С ГРУППАМИ ----------

    def get_all_groups(self) -> List[str]:
        """Возвращает отсортированный список всех существующих групп."""
        return self.group_manager.get_all_groups()

    def assign_group_to_chats(self, chats: List[Chat], group_name: Optional[str]) -> None:
        """Назначает группу указанным чатам."""
        for chat in chats:
            self.group_manager.set_group(chat.id, group_name)
            chat.group = group_name
        self._rebuild_filtered_chats()  # добавить эту строку

    def rename_group(self, old_name: str, new_name: str) -> bool:
        """Переименовывает группу, обновляя все затронутые чаты в памяти."""
        if self.group_manager.rename_group(old_name, new_name):
            # Обновляем все чаты, у которых была эта группа
            for source in self.sources:
                for chat in source.chats:
                    if chat.group == old_name:
                        chat.group = new_name
            return True
        return False

    def delete_group(self, group_name: str) -> None:
        """Удаляет группу у всех чатов."""
        self.group_manager.delete_group(group_name)
        for source in self.sources:
            for chat in source.chats:
                if chat.group == group_name:
                    chat.group = None
        self._rebuild_filtered_chats()  # добавить эту строку

    def add_group(self, group_name: str) -> bool:
        """Добавляет новую группу в список групп (без привязки к чатам)."""
        return self.group_manager.add_group(group_name)

    def set_grouping_mode(self, mode: str) -> None:
        """Устанавливает режим группировки (source/group/prefix)."""
        self.grouping_mode = mode

    def get_grouping_mode(self) -> str:
        return self.grouping_mode