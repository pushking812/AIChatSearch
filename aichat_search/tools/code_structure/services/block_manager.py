# aichat_search/tools/code_structure/services/block_manager.py

import logging
import re
from typing import List, Dict, Optional, Tuple
from aichat_search.services.block_parser import BlockParser, MessageBlock
from aichat_search.model import Chat, MessagePair
from ..parser import PARSERS
from ..models.node import Node
from ..models.block_info import MessageBlockInfo
from ..utils.helpers import extract_module_hint

logger = logging.getLogger(__name__)


class BlockManager:
    """Управляет загрузкой, парсингом и хранением блоков из сообщений."""

    def __init__(self):
        self.blocks_info: List[MessageBlockInfo] = []
        self.blocks_by_lang: Dict[str, List[MessageBlockInfo]] = {}

    def load_from_items(self, items: List[Tuple[Chat, MessagePair]]) -> None:
        """
        Загружает все блоки из списка пар, сортируя их по времени чата и индексу пары.
        Каждая пара обрабатывается как отдельное сообщение (response_text).
        """
        # Сортируем по времени обновления чата и индексу пары
        # Если updated_at отсутствует, используем пустую строку для сортировки
        sorted_items = sorted(
            items,
            key=lambda x: (x[0].updated_at or "", x[1].index)
        )

        parser = BlockParser()
        self.blocks_info.clear()
        self.blocks_by_lang.clear()

        for global_index, (chat, pair) in enumerate(sorted_items):
            text = pair.response_text
            blocks = parser.parse(text)
            for block_idx, block in enumerate(blocks):
                lang = block.language.lower() if block.language else ""
                if lang not in PARSERS:
                    continue  # пропускаем неподдерживаемые языки

                # Генерируем читаемое имя чата для block_id
                chat_name = re.sub(r'\W+', '_', chat.title) if chat.title else "unknown"
                block_id = f"chat_{chat_name}_msg_{pair.index}_block{block_idx}"
                content = block.content
                module_hint = extract_module_hint(block)

                # Метаданные о происхождении
                metadata = {
                    'chat_id': chat.id,
                    'chat_title': chat.title,
                    'chat_updated': chat.updated_at,
                    'pair_index': pair.index,
                }

                block_info = MessageBlockInfo(
                    block=block,
                    language=lang,
                    content=content,
                    block_id=block_id,
                    global_index=global_index,
                    module_hint=module_hint,
                    metadata=metadata
                )

                # Парсим блок
                self._parse_block(block_info)

                # Сохраняем
                self.blocks_info.append(block_info)
                self.blocks_by_lang.setdefault(lang, []).append(block_info)

    def _parse_block(self, block_info: MessageBlockInfo) -> None:
        """Парсит блок и сохраняет дерево или ошибку."""
        lang = block_info.language
        parser_class = PARSERS.get(lang)
        if not parser_class:
            block_info.set_error(ValueError(f"Нет парсера для языка {lang}"))
            return

        parser = parser_class()
        try:
            tree = parser.parse(block_info.content)
            block_info.set_tree(tree)
        except Exception as e:
            # Логируем только сообщение об ошибке, без traceback
            logger.error(f"Ошибка парсинга блока {block_info.block_id}: {e}")
            block_info.set_error(e)

    def get_blocks_by_lang(self, lang: str) -> List[MessageBlockInfo]:
        """Возвращает список блоков для указанного языка."""
        return self.blocks_by_lang.get(lang, [])

    def get_all_blocks(self) -> List[MessageBlockInfo]:
        """Возвращает все блоки."""
        return self.blocks_info

    def get_languages(self) -> List[str]:
        """Возвращает отсортированный список доступных языков."""
        return sorted(self.blocks_by_lang.keys())