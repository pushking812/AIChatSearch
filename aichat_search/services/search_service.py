# aichat_search/services/search_service.py

import re
from typing import List, Tuple, Any

from ..model import Chat, MessagePair


class SearchService:
    """Сервис для поиска по сообщениям и чатам."""

    def search(self, chat: Chat, query: str, field: str) -> List[MessagePair]:
        """
        Возвращает список пар сообщений, соответствующих запросу.
        Если field == "Запрос" – ищет в тексте запроса,
        если "Ответ" – в тексте ответа,
        иначе (или пустое поле) – в обоих полях.
        """
        query = (query or "").lower().strip()

        if not chat:
            return []

        if not query:
            return chat.get_pairs()

        result = []
        for pair in chat.get_pairs():
            if field == "Запрос":
                if query in pair.request_text.lower():
                    result.append(pair)
            elif field == "Ответ":
                if query in pair.response_text.lower():
                    result.append(pair)
            else:  # поиск по обоим полям
                if query in pair.request_text.lower() or query in pair.response_text.lower():
                    result.append(pair)
        return result

    def search_with_positions(
        self, chat: Chat, query: str, field: str
    ) -> List[Tuple[Chat, MessagePair, str, int, int]]:
        """
        Возвращает список кортежей (chat, pair, field, start, end)
        для каждого вхождения запроса в тексте.
        Если field == "Запрос" – только в запросе,
        если "Ответ" – только в ответе,
        иначе – в обоих полях.
        """
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
            else:  # поиск по обоим полям
                for m in pattern.finditer(pair.request_text or ""):
                    results.append((chat, pair, "request", m.start(), m.end()))
                for m in pattern.finditer(pair.response_text or ""):
                    results.append((chat, pair, "response", m.start(), m.end()))

        return results