# aichat_search/services/exporters/block_exporter.py

import os
from typing import Dict, Any, List

from .base import Exporter
from ..block_parser import BlockParser, MessageBlock


class BlockExporter(Exporter):
    """Экспорт сообщения в виде отдельных файлов-блоков в папке."""

    @staticmethod
    def prepare_data(chat_title: str, chat_created_at, pair, message_index: int) -> Dict[str, Any]:
        """Добавляет к стандартным данным распарсенные блоки, включая запрос."""
        data = Exporter.prepare_data(chat_title, chat_created_at, pair, message_index)

        parser = BlockParser()
        response_blocks = parser.parse(pair.response_text)

        # Создаём блок запроса с индексом 0
        request_block = MessageBlock(0, pair.request_text, language=None, block_type='request')

        # Сдвигаем индексы ответных блоков на 1
        for block in response_blocks:
            block.index += 1

        # Объединяем
        all_blocks = [request_block] + response_blocks
        data['blocks'] = all_blocks
        return data

    def export(self, data: Dict[str, Any], folder_path: str) -> None:
        """Сохраняет блоки в указанную папку. Если папка не существует, создаёт её."""
        os.makedirs(folder_path, exist_ok=True)

        blocks: List[MessageBlock] = data.get('blocks', [])
        if not blocks:
            # Если блоков нет (пустой запрос и ответ), создаём пустой блок запроса
            blocks = [MessageBlock(0, data['request_text'], language=None, block_type='request')]

        for block in blocks:
            file_path = os.path.join(folder_path, block.filename())
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(block.content)

        # Метаданные сообщения
        meta_path = os.path.join(folder_path, 'metadata.txt')
        with open(meta_path, 'w', encoding='utf-8') as f:
            f.write(f"Чат: {data['chat_title']}\n")
            f.write(f"Дата создания чата: {data['chat_created_at']}\n")
            f.write(f"Сообщение №{data['message_index']} (индекс в чате: {data['pair_index']})\n")
            f.write(f"Время запроса: {data['request_time']}\n")
            f.write(f"Время ответа: {data['response_time']}\n")
            if data['modified']:
                f.write("(сообщение было изменено)\n")