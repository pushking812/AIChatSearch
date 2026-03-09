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
        self._parsed_cache = {}               # успешно распарсенные блоки
        self.block_has_syntax_error = {}      # индекс блока -> True, если синтаксическая ошибка

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
        """Извлекает имя блока из его содержимого.
        Если блок содержит ошибку парсинга (незакрытый код), возвращает 'блок_кода (ошибка)'."""
        # Если блок ошибочный (незакрытый код), сразу возвращаем специальное имя
        if block.has_error:
            return "блок_кода (ошибка)"

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
            elif stripped:
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

    def _update_block_name_in_combo(self, index):
        """Обновляет имя блока в комбобоксе по индексу."""
        block = self.python_blocks[index]
        name = self._extract_block_name(block)
        # Если есть синтаксическая ошибка, добавляем постфикс
        if self.block_has_syntax_error.get(index, False):
            name += " (синтаксическая ошибка)"
        self.block_names[index] = f"{index+1:03d}: {name}"
        self.view.set_block_combo_values(self.block_names)
        self.view.set_current_block_index(index)

    def on_type_selected(self, event):
        pass

    def on_show_structure(self):
        index = self.view.get_selected_block_index()
        if index < 0 or index >= len(self.python_blocks):
            return

        block = self.python_blocks[index]

        # Проверка на ошибку от парсера блоков (незакрытый код)
        if block.has_error:
            self.view.show_error("Выбранный блок содержит ошибку парсинга (незакрытый код).")
            return

        # Если уже знаем, что блок с синтаксической ошибкой
        if self.block_has_syntax_error.get(index, False):
            self.view.show_error("В блоке обнаружена синтаксическая ошибка.")
            return

        # Проверка кэша (успешно распарсенные)
        if index in self._parsed_cache:
            root = self._parsed_cache[index]
            self.view.display_structure(root)
            return

        parser = PythonParser()
        try:
            root = parser.parse(block.content)
            self._parsed_cache[index] = root
            self.view.display_structure(root)
        except Exception as e:
            logger.error(f"Ошибка парсинга Python: {e}")
            # Помечаем блок как содержащий синтаксическую ошибку
            self.block_has_syntax_error[index] = True
            self._update_block_name_in_combo(index)
            self.view.show_error(f"Синтаксическая ошибка в коде: {e}")