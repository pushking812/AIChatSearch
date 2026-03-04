# deepseek/controller.py

import os
from typing import List, Set, Dict, Optional

from .gui_components.constants import CONFIG_DIR, CONFIG_FILE, PKL_FILE

from .model import DataSource, Chat, MessagePair  # добавлен импорт DataSource


class ChatController:
    def __init__(self):
        # Новые атрибуты для работы с несколькими источниками
        self.sources: List[DataSource] = []                 # список загруженных источников
        self.known_chat_ids: Set[str] = set()               # глобальное множество id чатов
        self._chat_to_source: Dict[str, DataSource] = {}    # id чата -> источник
        self._current_filter_query: str = ""                 # текущий фильтр для перестроения

        # Для обратной совместимости оставляем chats как объединённый список
        self.chats: List[Chat] = []                          # все чаты из всех источников
        self.filtered_chats: List[Chat] = []                 # отфильтрованный список

        self.current_chat: Optional[Chat] = None
        self.current_chat_pairs: List[MessagePair] = []
        self.current_index_in_chat: Optional[int] = None

        self._reset_search_state()

        # ---- НОВОЕ: путь к файлу сессии ----
        config_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', CONFIG_DIR))
        self.session_path = os.path.abspath(os.path.join(config_dir, PKL_FILE))

    # ---------- DATA ----------

    def _reset_search_state(self):
        self.visible_pairs = []
        self.search_active = False

    def set_chats(self, chats):
        """Заменяет все источники одним новым, содержащим переданные чаты (для обратной совместимости)."""
        # Очищаем текущие данные
        self.sources.clear()
        self.known_chat_ids.clear()
        self._chat_to_source.clear()

        if chats:
            # Создаём один источник без реального файла
            source = DataSource("Imported")  # специальное имя
            source.chats = list(chats)       # копируем список
            self.sources.append(source)

            # Обновляем множества и отображения
            for chat in source.chats:
                self.known_chat_ids.add(chat.id)
                self._chat_to_source[chat.id] = source

        # Перестраиваем отфильтрованный список
        self._current_filter_query = ""  # сбрасываем фильтр
        self._rebuild_filtered_chats()

    def _reset_navigation(self):
        self.current_chat = None
        self.current_chat_pairs = []
        self.current_index_in_chat = None

    def get_filtered_chats(self):
        return self.filtered_chats

    # ---------- НОВЫЕ МЕТОДЫ ДЛЯ ИСТОЧНИКОВ ----------

    def add_source(self, file_path: str) -> List[Chat]:
        """Загружает архив, добавляет только новые чаты, возвращает список добавленных чатов."""
        from .model import load_from_zip  # локальный импорт для избежания циклических зависимостей

        new_chats = load_from_zip(file_path)
        added_chats = []

        # Фильтруем только уникальные чаты
        for chat in new_chats:
            if chat.id not in self.known_chat_ids:
                self.known_chat_ids.add(chat.id)
                added_chats.append(chat)

        if added_chats:
            # Создаём новый источник
            source = DataSource(file_path)
            source.chats = added_chats
            self.sources.append(source)

            # Обновляем отображение id -> источник
            for chat in added_chats:
                self._chat_to_source[chat.id] = source

            # Перестраиваем объединённые списки
            self._rebuild_filtered_chats()

        return added_chats

    def clear_all_sources(self):
        """Полностью очищает все источники и сбрасывает состояние."""
        self.sources.clear()
        self.known_chat_ids.clear()
        self._chat_to_source.clear()
        self._current_filter_query = ""
        self._rebuild_filtered_chats()   # перестроит пустые списки и сбросит навигацию

    def _rebuild_filtered_chats(self):
        """Перестраивает объединённый список чатов и применяет фильтр."""
        # Собираем все чаты из источников
        all_chats = []
        for source in self.sources:
            all_chats.extend(source.chats)
        self.chats = all_chats

        # Применяем фильтр, если есть
        query = self._current_filter_query.lower().strip()
        if query:
            self.filtered_chats = [
                chat for chat in self.chats
                if query in chat.title.lower()
            ]
        else:
            self.filtered_chats = list(self.chats)

        # Сбрасываем навигацию (как и раньше при изменении списка)
        self._reset_navigation()

    def get_source_name(self, chat: Chat) -> str:
        """Возвращает имя файла источника для данного чата или 'Imported', если источник не определён."""
        source = self._chat_to_source.get(chat.id)
        if source:
            # Если file_path не None, берём basename, иначе возвращаем специальное имя
            if source.file_path != "Imported":
                return os.path.basename(source.file_path)
            else:
                return "Imported"
        return "Unknown"

    # ---------- FILTER ----------

    def filter_chats(self, query):
        """Сохраняет запрос фильтра и перестраивает отфильтрованный список."""
        self._current_filter_query = (query or "").strip()
        self._rebuild_filtered_chats()

    # ---------- SEARCH ----------

    def search(self, chat, query, field):
        query = (query or "").lower().strip()

        if not chat:
            return []

        if not query:
            return chat.get_pairs()

        result = []
        for pair in chat.get_pairs():
            if field == "Название чата":
                if query in chat.title.lower():
                    result.append(pair)
            elif field == "Запрос":
                if query in pair.request_text.lower():
                    result.append(pair)
            elif field == "Ответ":
                if query in pair.response_text.lower():
                    result.append(pair)

        return result

    def search_with_positions(self, chat, query, field):
        import re

        query = (query or "").strip()
        if not chat or not query:
            return []

        pattern = re.compile(re.escape(query), re.IGNORECASE)
        results = []

        for pair in chat.get_pairs():
            if field == "Запрос":
                for m in pattern.finditer(pair.request_text or ""):
                    results.append((chat, pair, "request", m.start(), m.end()))
            elif field == "Ответ":
                for m in pattern.finditer(pair.response_text or ""):
                    results.append((chat, pair, "response", m.start(), m.end()))
            else:
                for m in pattern.finditer(pair.request_text or ""):
                    results.append((chat, pair, "request", m.start(), m.end()))
                for m in pattern.finditer(pair.response_text or ""):
                    results.append((chat, pair, "response", m.start(), m.end()))

        return results

    # ---------- SELECT MESSAGE ----------

    def select_pair(self, chat, pair):
        pairs = chat.get_pairs()
        for i, p in enumerate(pairs):
            if p is pair:
                self.current_chat = chat
                self.current_chat_pairs = pairs
                self.current_index_in_chat = i
                return p
        return None

    # ---------- NAVIGATION ----------

    def prev_pair(self):
        if self.current_index_in_chat is None:
            return None

        if self.current_index_in_chat > 0:
            self.current_index_in_chat -= 1
            return self.current_chat_pairs[self.current_index_in_chat]

        return None

    def next_pair(self):
        if self.current_index_in_chat is None:
            return None

        if self.current_index_in_chat < len(self.current_chat_pairs) - 1:
            self.current_index_in_chat += 1
            return self.current_chat_pairs[self.current_index_in_chat]

        return None

    def get_nav_state(self):
        if self.current_index_in_chat is None:
            return False, False

        return (
            self.current_index_in_chat > 0,
            self.current_index_in_chat < len(self.current_chat_pairs) - 1,
        )

    def get_position_info(self):
        if self.current_chat is None or self.current_index_in_chat is None:
            return None, None, None

        return (
            self.current_chat.title,
            self.current_index_in_chat + 1,
            len(self.current_chat_pairs),
        )

    def get_current_pair(self):
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

    def save_session(self):
        """Сохраняет текущие источники в файл сессии."""
        from .persistence import save_session as _save
        _save(self.sources, self.session_path)

    def load_session(self):
        """Загружает источники из файла сессии и восстанавливает внутренние структуры."""
        from .persistence import load_session as _load
        sources = _load(self.session_path)
        if sources is not None:
            self.sources = sources
            # Восстанавливаем known_chat_ids и _chat_to_source
            self.known_chat_ids.clear()
            self._chat_to_source.clear()
            for source in self.sources:
                for chat in source.chats:
                    self.known_chat_ids.add(chat.id)
                    self._chat_to_source[chat.id] = source
            self._rebuild_filtered_chats()