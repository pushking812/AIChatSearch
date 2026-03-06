# deepseek/controller.py

import os
from typing import List, Set, Dict, Optional

from .gui_components.constants import CONFIG_DIR, CONFIG_FILE, PKL_FILE
from .model import DataSource, Chat, MessagePair
from .services.archive_loader import load_from_zip
from .services.search_service import SearchService
from .services.session_manager import SessionManager


class ChatController:
    def __init__(self) -> None:
        # Атрибуты для работы с несколькими источниками
        self.sources: List[DataSource] = []                 # список загруженных источников
        self.known_chat_ids: Set[str] = set()               # глобальное множество id чатов
        self._chat_source_map: Dict[str, DataSource] = {}   # id чата -> источник
        self._current_filter_query: str = ""                 # текущий фильтр для перестроения

        # Для обратной совместимости оставляем chats как объединённый список
        self.chats: List[Chat] = []                          # все чаты из всех источников
        self.filtered_chats: List[Chat] = []                 # отфильтрованный список

        self.current_chat: Optional[Chat] = None
        self.current_chat_pairs: List[MessagePair] = []
        self.current_index_in_chat: Optional[int] = None

        self._reset_search_state()

        # Путь к файлу сессии
        config_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', CONFIG_DIR))
        self.session_path = os.path.abspath(os.path.join(config_dir, PKL_FILE))

        # Сервисы
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

    def add_source(self, file_path: str) -> List[Chat]:
        """Загружает архив, добавляет только новые чаты, возвращает список добавленных чатов."""
        new_chats = self._load_new_chats(file_path)
        added_chats = self._filter_unique(new_chats)
        if added_chats:
            self._add_source_with_chats(added_chats, file_path)
        return added_chats

    def _load_new_chats(self, file_path: str) -> List[Chat]:
        """Загружает чаты из ZIP-архива."""
        return load_from_zip(file_path)

    def _filter_unique(self, chats: List[Chat]) -> List[Chat]:
        """Оставляет только те чаты, id которых ещё не встречались, и добавляет их в known_chat_ids."""
        added: List[Chat] = []
        for chat in chats:
            if chat.id not in self.known_chat_ids:
                self.known_chat_ids.add(chat.id)
                added.append(chat)
        return added

    def _add_source_with_chats(self, added_chats: List[Chat], file_path: str) -> None:
        """Создаёт новый источник с добавленными чатами и обновляет структуры."""
        source = DataSource(file_path)
        source.chats = added_chats
        self.sources.append(source)

        for chat in added_chats:
            self._chat_source_map[chat.id] = source

        self._rebuild_filtered_chats()

    def clear_all_sources(self) -> None:
        """Полностью очищает все источники и сбрасывает состояние."""
        self.sources.clear()
        self.known_chat_ids.clear()
        self._chat_source_map.clear()
        self._current_filter_query = ""
        self._rebuild_filtered_chats()   # перестроит пустые списки и сбросит навигацию

    def _rebuild_filtered_chats(self) -> None:
        """Перестраивает объединённый список чатов и применяет фильтр."""
        self._collect_all_chats()
        self._apply_filter()

    def _collect_all_chats(self) -> None:
        """Собирает все чаты из всех источников в self.chats."""
        all_chats: List[Chat] = []
        for source in self.sources:
            all_chats.extend(source.chats)
        self.chats = all_chats

    def _apply_filter(self) -> None:
        """Применяет текущий фильтр к self.chats и сбрасывает навигацию."""
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
        """Возвращает имя файла источника для данного чата или 'Imported', если источник не определён."""
        source = self._chat_source_map.get(chat.id)
        if source:
            # Если file_path не None, берём basename, иначе возвращаем специальное имя
            if source.file_path != "Imported":
                return os.path.basename(source.file_path)
            else:
                return "Imported"
        return "Unknown"

    # ---------- FILTER ----------

    def filter_chats(self, query: str) -> None:
        """Сохраняет запрос фильтра и перестраивает отфильтрованный список."""
        self._current_filter_query = (query or "").strip()
        self._rebuild_filtered_chats()

    # ---------- SEARCH ----------

    def search(self, chat: Chat, query: str, field: str) -> List[MessagePair]:
        """Делегирует выполнение поиска сервису SearchService."""
        return self._search_service.search(chat, query, field)

    def search_with_positions(self, chat: Chat, query: str, field: str) -> List:
        """Делегирует выполнение поиска с позициями сервису SearchService."""
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
        """
        Возвращает текущую выбранную пару сообщений.
        """
        if self.current_chat is None:
            return None

        if self.current_index_in_chat is None:
            return None

        if self.current_index_in_chat < 0:
            return None

        if self.current_index_in_chat >= len(self.current_chat_pairs):
            return None

        return self.current_chat_pairs[self.current_index_in_chat]

    # ---------- СОХРАНЕНИЕ И ЗАГРУЗКА СЕССИИ ----------

    def save_session(self) -> None:
        """Сохраняет текущие источники в файл сессии."""
        self._session_manager.save(self.sources)

    def load_session(self) -> None:
        """Загружает источники из файла сессии и восстанавливает внутренние структуры."""
        sources = self._session_manager.load()
        if sources is not None:
            self.sources = sources
            # Восстанавливаем known_chat_ids и _chat_source_map
            self.known_chat_ids.clear()
            self._chat_source_map.clear()
            for source in self.sources:
                for chat in source.chats:
                    self.known_chat_ids.add(chat.id)
                    self._chat_source_map[chat.id] = source
            self._rebuild_filtered_chats()