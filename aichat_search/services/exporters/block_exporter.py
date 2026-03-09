# aichat_search/services/exporters/block_exporter.py

import os
import logging
from typing import Dict, Any, List

from .base import Exporter
from ..block_parser import BlockParser, MessageBlock

logger = logging.getLogger(__name__)


class BlockExporter(Exporter):
    """Экспорт сообщения в виде отдельных файлов-блоков в папке."""

    @staticmethod
    def prepare_data(chat_title: str, chat_created_at, pair, message_index: int, source_name: str) -> Dict[str, Any]:
        """Добавляет к стандартным данным распарсенные блоки, включая запрос.
        
        Аргументы:
            chat_title: название чата
            chat_created_at: дата создания чата
            pair: объект MessagePair
            message_index: номер сообщения в чате (начиная с 1)
            source_name: имя файла-источника (например, "deepseek_data-2026-03-02.zip")
        
        Возвращает словарь с ключами:
            - стандартные поля от Exporter.prepare_data
            - 'blocks': список MessageBlock
            - 'unclosed_blocks': количество незакрытых блоков кода
        """
        data = Exporter.prepare_data(chat_title, chat_created_at, pair, message_index)

        parser = BlockParser()
        response_blocks = parser.parse(pair.response_text)
        # Предупреждение НЕ выводится здесь, чтобы избежать дублирования.
        # Оно будет выведено в export_manager.py после назначения глобальных индексов.

        # Создаём блок запроса с индексом 0
        request_block = MessageBlock(0, pair.request_text, language=None, block_type='request')

        # Сдвигаем индексы ответных блоков на 1
        for block in response_blocks:
            block.index += 1

        # Объединяем
        all_blocks = [request_block] + response_blocks
        data['blocks'] = all_blocks
        data['unclosed_blocks'] = parser.unclosed_blocks
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