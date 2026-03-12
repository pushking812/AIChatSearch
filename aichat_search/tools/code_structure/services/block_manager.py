# aichat_search/tools/code_structure/services/block_manager.py

import logging
from typing import List, Dict, Optional
from aichat_search.services.block_parser import BlockParser, MessageBlock
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

    def load_from_messages(self, messages: List[str]) -> None:
        """Загружает все блоки из списка сообщений."""
        parser = BlockParser()
        global_index = 0
        self.blocks_info.clear()
        self.blocks_by_lang.clear()

        for msg_idx, msg_text in enumerate(messages):
            # Получаем блоки из сообщения
            blocks = parser.parse(msg_text)  # возвращает список MessageBlock
            for block_idx, block in enumerate(blocks):
                lang = block.language.lower() if block.language else ""
                if lang not in PARSERS:
                    continue  # пропускаем неподдерживаемые языки

                # Создаём информацию о блоке
                block_id = f"msg{msg_idx}_block{block_idx}"
                content = block.content
                module_hint = extract_module_hint(block)

                block_info = MessageBlockInfo(
                    block=block,
                    language=lang,
                    content=content,
                    block_id=block_id,
                    global_index=global_index,
                    module_hint=module_hint
                )
                global_index += 1

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
            logger.exception(f"Ошибка парсинга блока {block_info.block_id}")
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