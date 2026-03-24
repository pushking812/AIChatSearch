# aichat_search/tools/code_structure/services/block_service.py

import textwrap
from typing import List, Dict, Optional, Tuple
import logging

from aichat_search.model import Chat, MessagePair
from aichat_search.tools.code_structure.services.block_manager import BlockManager
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.parser import PythonParser

logger = logging.getLogger(__name__)


class BlockService:
    def __init__(self):
        self.block_manager = BlockManager()
        self.parser = PythonParser()
    
    def load_from_items(self, items: List[Tuple[Chat, MessagePair]]):
        self.block_manager.load_from_items(items)
        logger.info(f"Загружено блоков: {len(self.block_manager.get_all_blocks())}")
    
    def get_all_blocks(self) -> List[MessageBlockInfo]:
        return self.block_manager.get_all_blocks()
    
    def get_blocks_by_language(self, lang: str) -> List[MessageBlockInfo]:
        return self.block_manager.get_blocks_by_lang(lang)
    
    def get_languages(self) -> List[str]:
        return self.block_manager.get_languages()
    
    def get_error_blocks(self) -> List[MessageBlockInfo]:
        return [b for b in self.block_manager.get_all_blocks() if b.syntax_error]
    
    def fix_error_block(self, block: MessageBlockInfo, new_content: str) -> bool:
        block.content = new_content
        try:
            content = new_content.replace('\t', '    ')
            content = textwrap.dedent(content)
            tree = self.parser.parse(content)
            block.set_tree(tree)
            block.syntax_error = None
            logger.info(f"Блок {block.block_id} успешно исправлен")
            return True
        except Exception as e:
            block.set_error(e)
            logger.error(f"Не удалось исправить блок {block.block_id}: {e}")
            return False
    
    def get_block_description(self, block: MessageBlockInfo) -> str:
        if block.module_hint:
            return block.module_hint
        if block.tree is None or block.syntax_error:
            return "ошибка" if block.syntax_error else "блок_кода"
        
        desc = self._find_first_definition(block.tree)
        return desc or "блок_кода"
    
    def _find_first_definition(self, node) -> Optional[str]:
        for child in node.children:
            if child.node_type == "class":
                for m in child.children:
                    if m.node_type == "method":
                        return f"class_{child.name}_def_{m.name}"
                return f"class_{child.name}"
            elif child.node_type == "function":
                return f"def_{child.name}"
            else:
                res = self._find_first_definition(child)
                if res:
                    return res
        return None
    
    def get_text_blocks_by_pair(self) -> Dict[str, Dict[int, str]]:
        return self.block_manager.get_text_blocks_by_pair()
    
    def get_full_texts_by_pair(self) -> Dict[str, str]:
        return self.block_manager.get_full_texts_by_pair()