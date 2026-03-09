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
        self.blocks = []          # все блоки сообщения
        self.python_blocks = []   # только Python-блоки
        self.block_names = []     # имена для отображения в комбобоксе
        self._parsed_cache = {}  # кэш: индекс блока -> корневой узел

        self._load_blocks()
        if self.python_blocks:
            self._fill_combos()
            self.view.show_button.config(command=self.on_show_structure)
        else:
            self.view.show_error("В сообщении нет блоков Python.")
            self.view.destroy()


    def _load_blocks(self):
        """Разбирает сообщение на блоки и отбирает Python-блоки."""
        parser = BlockParser()

        # Парсим запрос и ответ отдельно, затем объединяем списки
        request_blocks = parser.parse(self.pair.request_text)
        response_blocks = parser.parse(self.pair.response_text)
        self.blocks = request_blocks + response_blocks

        # Фильтруем Python-блоки (язык 'python' или 'py')
        for block in self.blocks:
            lang = block.language.lower() if block.language else ""
            if lang in ("python", "py"):
                self.python_blocks.append(block)

    def _extract_block_name(self, block):
        """Извлекает имя блока из его содержимого."""
        lines = block.content.splitlines()
        # Проверяем первые несколько строк на наличие комментария
        for line in lines[:10]:
            stripped = line.strip()
            if stripped.startswith('#'):
                return stripped[1:].strip()
            if stripped:  # первая непустая не-комментарий строка – прекращаем поиск комментария
                break

        # Поиск class или def
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('class '):
                parts = stripped[6:].split()
                if parts:
                    return parts[0].split('(')[0]
            elif stripped.startswith('def '):
                parts = stripped[4:].split()
                if parts:
                    return parts[0].split('(')[0]

        return "блок_кода"

    def _fill_combos(self):
        """Заполняет комбобоксы данными."""
        self.block_names = []
        for i, block in enumerate(self.python_blocks):
            name = self._extract_block_name(block)
            self.block_names.append(f"{i+1:03d}: {name}")

        self.view.set_type_combo_values(["Python"])
        self.view.set_block_combo_values(self.block_names)
        if self.block_names:
            self.view.set_current_block_index(len(self.block_names) - 1)

    def on_type_selected(self, event):
        pass
        
    def on_show_structure(self):
        """Обработчик кнопки 'Показать структуру'."""
        index = self.view.get_selected_block_index()
        if index < 0 or index >= len(self.python_blocks):
            return

        # Проверяем кэш
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