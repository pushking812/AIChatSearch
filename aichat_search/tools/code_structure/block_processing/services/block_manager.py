# aichat_search/tools/code_structure/services/block_manager.py

import logging
import textwrap
import re
from typing import List, Dict, Optional, Tuple, Any

from aichat_search.model import Chat, MessagePair
from aichat_search.services.block_parser import BlockParser, MessageBlock

from aichat_search.tools.code_structure.parsing.core.parser import PARSERS
from aichat_search.tools.code_structure.parsing.models.node import Node
from aichat_search.tools.code_structure.module_resolution.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.utils.helpers import extract_module_hint

from aichat_search.tools.code_structure.utils.logger import get_logger
logger = get_logger(__name__, level = logging.WARNING)


class BlockManager:
    def __init__(self):
        self.blocks_info: List[MessageBlockInfo] = []
        self.blocks_by_lang: Dict[str, List[MessageBlockInfo]] = {}
        self.text_blocks_by_pair: Dict[str, Dict[int, str]] = {}   # key = pair.index, value = {block_idx: content}
        self.full_texts_by_pair: Dict[str, str] = {}

    def load_from_items(self, items: List[Tuple[Chat, MessagePair]]) -> None:
        def get_timestamp(pair: MessagePair) -> float:
            if pair.response_time:
                return pair.response_time.timestamp()
            elif pair.request_time:
                return pair.request_time.timestamp()
            return 0.0

        sorted_items = sorted(
            items,
            key=lambda x: (get_timestamp(x[1]), x[1].index)
        )

        parser = BlockParser()
        self.blocks_info.clear()
        self.blocks_by_lang.clear()
        self.text_blocks_by_pair.clear()
        self.full_texts_by_pair.clear()

        for global_index, (chat, pair) in enumerate(sorted_items):
            text = pair.response_text
            self.full_texts_by_pair[pair.index] = text
            blocks = parser.parse(text)
            for block_idx, block in enumerate(blocks):
                lang = block.language.lower() if block.language else ""
                # Если язык не поддерживается парсером, считаем текстовым блоком
                if lang not in PARSERS:
                    self.text_blocks_by_pair.setdefault(pair.index, {})[block_idx] = block.content
                    continue
                # Далее только кодовые блоки
                chat_name = re.sub(r'\W+', '_', chat.title) if chat.title else "unknown"
                block_id = f"chat_{chat_name}_msg_{pair.index}_block{block_idx}"
                content = block.content
                module_hint = extract_module_hint(block)

                timestamp = get_timestamp(pair)

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
                    metadata=metadata,
                    timestamp=timestamp,
                    block_idx=block_idx
                )

                self._parse_block(block_info)
                self.blocks_info.append(block_info)
                self.blocks_by_lang.setdefault(lang, []).append(block_info)

    def _parse_block(self, block_info: MessageBlockInfo) -> None:
        lang = block_info.language
        parser_class = PARSERS.get(lang)
        if not parser_class:
            block_info.set_error(ValueError(f"Нет парсера для языка {lang}"))
            return

        parser = parser_class()
        try:
            content = block_info.content
            content = content.replace('\t', '    ')
            content = textwrap.dedent(content)
            tree = parser.parse(content)
            block_info.set_tree(tree)
        except SyntaxError as e:
            logger.debug(f"Синтаксическая ошибка в блоке {block_info.block_id}: {e}")
            block_info.set_error(e)
        except Exception as e:
            logger.error(f"КРИТИЧЕСКАЯ ОШИБКА ПРИ ПАРСИНГЕ БЛОКА {block_info.block_id}: {e}", exc_info=True)
            block_info.set_error(e)

    def get_blocks_by_lang(self, lang: str) -> List[MessageBlockInfo]:
        return self.blocks_by_lang.get(lang, [])

    def get_all_blocks(self) -> List[MessageBlockInfo]:
        return self.blocks_info

    def get_languages(self) -> List[str]:
        return sorted(self.blocks_by_lang.keys())

    def get_text_blocks_by_pair(self) -> Dict[str, Dict[int, str]]:
        return self.text_blocks_by_pair

    def get_full_texts_by_pair(self) -> Dict[str, str]:
        return self.full_texts_by_pair