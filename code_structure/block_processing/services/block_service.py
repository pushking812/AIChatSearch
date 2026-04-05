# code_structure/block_processing/services/block_service.py

import textwrap
from typing import List, Dict, Optional, Tuple
import logging

from aichat_search.model import Chat, MessagePair
from aichat_search.services.block_parser import BlockParser

from code_structure.models.block import Block
from code_structure.models.registry import BlockRegistry
from code_structure.parsing.core.parser import PythonParser

from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level=logging.WARNING)


class BlockService:
    def __init__(self):
        self.parser = PythonParser()
        self._block_registry = BlockRegistry()
        self._text_blocks_by_pair: Dict[str, Dict[int, str]] = {}
        self._full_texts_by_pair: Dict[str, str] = {}
        self._error_blocks: List[Block] = []

    def load_from_items(self, items: List[Tuple[Chat, MessagePair]]):
        block_parser = BlockParser()
        self._error_blocks.clear()   # очищаем перед загрузкой
        for global_index, (chat, pair) in enumerate(items):
            text = pair.response_text
            blocks = block_parser.parse(text)
            self._full_texts_by_pair[pair.index] = text
            text_blocks_for_pair = {}
            for block_idx, mb in enumerate(blocks):
                lang = mb.language.lower() if mb.language else ""
                if not lang:
                    text_blocks_for_pair[block_idx] = mb.content
                else:
                    # Применяем dedent к содержимому блока
                    dedented_content = textwrap.dedent(mb.content)
                    
                    new_block = Block(
                        chat=chat,
                        message_pair=pair,
                        language=lang,
                        content=dedented_content,  # <-- очищенный код
                        block_idx=block_idx,
                        global_index=global_index,
                        code_tree=None,
                        module_hint=None
                    )
                    if lang in ('python', 'py'):
                        try:
                            tree = self.parser.parse(new_block)
                            new_block = Block(
                                chat=new_block.chat,
                                message_pair=new_block.message_pair,
                                language=new_block.language,
                                content=new_block.content,
                                block_idx=new_block.block_idx,
                                global_index=new_block.global_index,
                                code_tree=tree,
                                module_hint=new_block.module_hint
                            )
                        except SyntaxError:
                            # Сохраняем блок с ошибкой (код уже очищен)
                            self._error_blocks.append(new_block)
                            logger.warning(f"Синтаксическая ошибка при парсинге блока {new_block.display_name}")
                        except Exception as e:
                            logger.error(f"Ошибка парсинга блока {new_block.display_name}: {e}")
                    self._block_registry.register(new_block)
            if text_blocks_for_pair:
                self._text_blocks_by_pair[pair.index] = text_blocks_for_pair

        logger.info(f"Зарегистрировано блоков: {len(self._block_registry.get_all())}, ошибок: {len(self._error_blocks)}")

    def get_new_blocks(self) -> List[Block]:
        return self._block_registry.get_all()

    def get_new_block(self, block_id: str) -> Optional[Block]:
        return self._block_registry.get(block_id)

    def get_text_blocks_by_pair(self) -> Dict[str, Dict[int, str]]:
        return self._text_blocks_by_pair

    def get_full_texts_by_pair(self) -> Dict[str, str]:
        return self._full_texts_by_pair
        
    def get_error_blocks(self) -> List[Block]:
        return self._error_blocks