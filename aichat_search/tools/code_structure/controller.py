# aichat_search/tools/code_structure/controller.py

import logging
from ...services.block_parser import BlockParser
from .view import CodeStructureWindow
from .parser import PythonParser

logger = logging.getLogger(__name__)


class CodeStructureController:
    def __init__(self, parent, pair):
        self.parent = parent
        self.pair = pair

        self.view = CodeStructureWindow(parent)
        self.blocks = []
        self.python_blocks = []
        self.block_names = []
        self._parsed_cache = {}

        self._load_blocks()
        if self.python_blocks:
            self._fill_combos()
            self.view.show_button.config(command=self.on_show_structure)
        else:
            self.view.show_error("В сообщении нет блоков Python.")
            self.view.destroy()

    def _load_blocks(self):
        parser = BlockParser()
        request_blocks = parser.parse(self.pair.request_text)
        response_blocks = parser.parse(self.pair.response_text)
        self.blocks = request_blocks + response_blocks

        for block in self.blocks:
            lang = block.language.lower() if block.language else ""
            if lang in ("python", "py"):
                self.python_blocks.append(block)

    def _extract_block_name(self, block):
        """Улучшенное извлечение имени блока."""
        lines = block.content.splitlines()
        if not lines:
            return "блок_кода"

        # Пропускаем пустые строки в начале
        start_idx = 0
        while start_idx < len(lines) and not lines[start_idx].strip():
            start_idx += 1
        if start_idx >= len(lines):
            return "блок_кода"

        # 1. Поиск однострочных комментариев (идущих подряд)
        comment_lines = []
        i = start_idx
        while i < len(lines) and i - start_idx < 10:  # ограничим 10 строками
            stripped = lines[i].strip()
            if stripped.startswith('#'):
                comment_lines.append(stripped[1:].strip())
                i += 1
            else:
                break
        if comment_lines:
            # Объединяем несколько комментариев через пробел
            return " ".join(comment_lines)

        # 2. Поиск class или def (пропуская декораторы)
        i = start_idx
        while i < len(lines):
            stripped = lines[i].strip()
            if stripped.startswith('class '):
                parts = stripped[6:].split()
                if parts:
                    return parts[0].split('(')[0]
            elif stripped.startswith('def '):
                parts = stripped[4:].split()
                if parts:
                    return parts[0].split('(')[0]
            elif stripped.startswith('@'):  # декоратор – пропускаем
                i += 1
                continue
            elif stripped:  # встретили что-то другое – прекращаем
                break
            i += 1

        return "блок_кода"

    def _fill_combos(self):
        self.block_names = []
        for i, block in enumerate(self.python_blocks):
            name = self._extract_block_name(block)
            self.block_names.append(f"{i+1:03d}: {name}")

        self.view.set_type_combo_values(["Python"])
        self.view.set_block_combo_values(self.block_names)
        if self.block_names:
            self.view.set_current_block_index(len(self.block_names) - 1)

    def on_type_selected(self, event):
        # Задел для будущего: при смене типа очищаем кэш и блоки
        pass

    def on_show_structure(self):
        index = self.view.get_selected_block_index()
        if index < 0 or index >= len(self.python_blocks):
            return

        if index in self._parsed_cache:
            root = self._parsed_cache[index]
            self.view.display_structure(root)
            return

        block = self.python_blocks[index]
        parser = PythonParser()
        try:
            root = parser.parse(block.content)
            self._parsed_cache[index] = root
            self.view.display_structure(root)
        except Exception as e:
            logger.exception("Ошибка парсинга Python")
            self.view.show_error(f"Не удалось распарсить код:\n{e}")