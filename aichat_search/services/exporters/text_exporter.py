# aichat_search/services/exporters/text_exporter.py

import os
from typing import Any, Dict

from .base import Exporter


class TextExporter(Exporter):
    """Экспорт сообщения в простой текстовый файл."""

    @staticmethod
    def format_message(data: Dict[str, Any]) -> str:
        """Форматирует одно сообщение в строку для экспорта."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"Чат: {data['chat_title']}")
        lines.append(f"Дата создания чата: {data['chat_created_at']}")
        lines.append(f"Сообщение №{data['message_index']} (индекс в чате: {data['pair_index']})")
        lines.append("-" * 60)
        lines.append("ЗАПРОС:")
        lines.append(data['request_text'])
        lines.append("-" * 60)
        lines.append("ОТВЕТ:")
        lines.append(data['response_text'])
        if data['request_time'] or data['response_time']:
            lines.append("-" * 60)
            lines.append(f"Время запроса: {data['request_time']}")
            lines.append(f"Время ответа: {data['response_time']}")
        if data['modified']:
            lines.append("(сообщение было изменено)")
        lines.append("=" * 60)
        return "\n".join(lines)

    def export(self, data: Dict[str, Any], file_path: str) -> None:
        """Сохраняет одно сообщение в файл."""
        content = self.format_message(data)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)