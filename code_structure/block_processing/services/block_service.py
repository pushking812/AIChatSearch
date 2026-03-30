# code_structure/block_processing/services/block_service.py

import textwrap
from typing import List, Dict, Optional, Tuple
import logging

from aichat_search.model import Chat, MessagePair
from aichat_search.services.block_parser import BlockParser

from code_structure.block_processing.services.block_manager import BlockManager
from code_structure.module_resolution.models.block_info import MessageBlockInfo
from code_structure.parsing.core.parser import PythonParser

from code_structure.models.block import Block
from code_structure.models.registry import BlockRegistry

from code_structure.utils.logger import get_logger
logger = get_logger(__name__, level=logging.WARNING)


class BlockService:
    def __init__(self):
        self.block_manager = BlockManager()
        self.parser = PythonParser()
        self._block_registry = BlockRegistry()

    def load_from_items(self, items: List[Tuple[Chat, MessagePair]]):
        # 1. Загружаем старые блоки через BlockManager (для обратной совместимости)
        self.block_manager.load_from_items(items)
        logger.info(f"Загружено старых блоков: {len(self.block_manager.get_all_blocks())}")

        # 2. Создаём новые блоки (Block) параллельно
        block_parser = BlockParser()
        for global_index, (chat, pair) in enumerate(items):
            text = pair.response_text
            blocks = block_parser.parse(text)
            for block_idx, mb in enumerate(blocks):
                lang = mb.language.lower() if mb.language else ""

                # Создаём блок без явного id – он будет вычислен в __post_init__
                new_block = Block(
                    chat=chat,
                    message_pair=pair,
                    language=lang,
                    content=mb.content,
                    block_idx=block_idx,
                    global_index=global_index,
                    code_tree=None,
                    module_hint=None
                )

                # Парсим только кодовые блоки (язык поддерживается)
                if lang and lang in ('python', 'py'):
                    try:
                        tree = self.parser.parse_new(new_block)
                        # Так как Block неизменяемый, создаём новый экземпляр с заполненным code_tree
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
                        logger.warning(f"Синтаксическая ошибка при парсинге блока {new_block.display_name}")
                    except Exception as e:
                        logger.error(f"Ошибка парсинга блока {new_block.display_name}: {e}")

                self._block_registry.register(new_block)

        logger.info(f"Зарегистрировано новых блоков: {len(self._block_registry.get_all())}")

    # Старые методы (работают с MessageBlockInfo) – без изменений
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
            logger.info(f"Блок {block.display_name} успешно исправлен")
            return True
        except Exception as e:
            block.set_error(e)
            logger.error(f"Не удалось исправить блок {block.display_name}: {e}")
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

    # Новые методы для доступа к новым блокам
    def get_new_blocks(self) -> List[Block]:
        return self._block_registry.get_all()

    def get_new_block(self, block_id: str) -> Optional[Block]:
        return self._block_registry.get(block_id)