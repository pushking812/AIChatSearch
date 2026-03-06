# deepseek/services/search_service.py

import re
from typing import List, Tuple, Any

from ..model import Chat, MessagePair


class SearchService:
    """Сервис для поиска по сообщениям и чатам."""

    def search(self, chat: Chat, query: str, field: str) -> List[MessagePair]:
        """
        Возвращает список пар сообщений, соответствующих запросу.
        Если field == "Название чата", проверяется заголовок чата.
        """
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

    def search_with_positions(
        self, chat: Chat, query: str, field: str
    ) -> List[Tuple[Chat, MessagePair, str, int, int]]:
        """
        Возвращает список кортежей (chat, pair, field, start, end)
        для каждого вхождения запроса в тексте.
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
            else:
                for m in pattern.finditer(pair.request_text or ""):
                    results.append((chat, pair, "request", m.start(), m.end()))
                for m in pattern.finditer(pair.response_text or ""):
                    results.append((chat, pair, "response", m.start(), m.end()))

        return results