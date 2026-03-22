# aichat_search/tools/code_structure/services/block_manager.py

import logging
import re
import textwrap
from typing import List, Dict, Optional, Tuple
from aichat_search.services.block_parser import BlockParser, MessageBlock
from aichat_search.model import Chat, MessagePair
from ..parser import PARSERS
from ..models.node import Node
from ..models.block_info import MessageBlockInfo
from ..utils.helpers import extract_module_hint

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class BlockManager:
    def __init__(self):
        self.blocks_info: List[MessageBlockInfo] = []
        self.blocks_by_lang: Dict[str, List[MessageBlockInfo]] = {}

    def load_from_items(self, items: List[Tuple[Chat, MessagePair]]) -> None:
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
                    continue

                chat_name = re.sub(r'\W+', '_', chat.title) if chat.title else "unknown"
                block_id = f"chat_{chat_name}_msg_{pair.index}_block{block_idx}"
                content = block.content
                module_hint = extract_module_hint(block)

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
            # Удаляем общий отступ у содержимого блока, чтобы избежать синтаксических ошибок
            content = textwrap.dedent(block_info.content)
            tree = parser.parse(content)
            block_info.set_tree(tree)
        except SyntaxError as e:
            # Ошибка в коде блока - это ожидаемо
            logger.debug(f"Синтаксическая ошибка в блоке {block_info.block_id}: {e}")
            block_info.set_error(e)
        except Exception as e:
            # Ошибка в самой программе - это серьёзно
            logger.error(f"КРИТИЧЕСКАЯ ОШИБКА ПРИ ПАРСИНГЕ БЛОКА {block_info.block_id}: {e}", exc_info=True)
            block_info.set_error(e)

    def get_blocks_by_lang(self, lang: str) -> List[MessageBlockInfo]:
        return self.blocks_by_lang.get(lang, [])

    def get_all_blocks(self) -> List[MessageBlockInfo]:
        return self.blocks_info

    def get_languages(self) -> List[str]:
        return sorted(self.blocks_by_lang.keys())