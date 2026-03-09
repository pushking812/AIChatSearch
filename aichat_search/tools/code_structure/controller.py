# aichat_search/tools/code_structure/controller.py

import logging
from ...services.block_parser import BlockParser
from .view import CodeStructureWindow
from .parser import PythonParser, PARSERS

logger = logging.getLogger(__name__)


class CodeStructureController:
    def __init__(self, parent, pair):
        self.parent = parent
        self.pair = pair

        self.view = CodeStructureWindow(parent)
        self.view.set_controller(self)

        # Все блоки сообщения (объекты MessageBlock)
        self.all_blocks = []
        # Словарь: язык -> список блоков (только поддерживаемые языки)
        self.blocks_by_lang = {}
        # Список доступных языков (ключи из blocks_by_lang)
        self.available_languages = []
        # Текущий выбранный язык
        self.current_lang = None
        # Блоки для текущего языка (список)
        self.current_blocks = []
        # Имена для отображения в комбобоксе (для текущего языка)
        self.current_block_names = []

        # Кэш успешно распарсенных узлов для каждого блока (ключ - объект блока)
        self._parsed_cache = {}
        # Флаги синтаксических ошибок (ключ - объект блока)
        self._syntax_error = set()

        self._load_blocks()
        if self.available_languages:
            self._fill_language_combo()
            # Выбираем первый язык и загружаем его блоки
            self.current_lang = self.available_languages[0]
            self._switch_language(self.current_lang)
            self.view.show_button.config(command=self.on_show_structure)
        else:
            self.view.show_error("В сообщении нет блоков с поддерживаемыми языками.")
            self.view.destroy()

    def _load_blocks(self):
        """Разбирает сообщение на блоки и группирует по языкам."""
        parser = BlockParser()
        request_blocks = parser.parse(self.pair.request_text)
        response_blocks = parser.parse(self.pair.response_text)
        self.all_blocks = request_blocks + response_blocks

        # Собираем блоки по языкам
        lang_dict = {}
        for block in self.all_blocks:
            lang = block.language.lower() if block.language else ""
            if lang in PARSERS:   # только поддерживаемые языки
                lang_dict.setdefault(lang, []).append(block)

        self.blocks_by_lang = lang_dict
        self.available_languages = sorted(lang_dict.keys())

    def _fill_language_combo(self):
        """Заполняет первый комбобокс списком языков."""
        # Преобразуем внутренние ключи в отображаемые названия (можно просто с заглавной)
        display_names = [lang.capitalize() for lang in self.available_languages]
        self.view.set_type_combo_values(display_names)

    def _switch_language(self, lang):
        """Переключает текущий язык, обновляет второй комбобокс и сбрасывает кэш."""
        self.current_lang = lang
        self.current_blocks = self.blocks_by_lang[lang]
        self.current_block_names = self._generate_block_names(self.current_blocks)
        self.view.set_block_combo_values(self.current_block_names)
        if self.current_block_names:
            self.view.set_current_block_index(len(self.current_block_names) - 1)
        # Очищаем кэш и ошибки (они привязаны к конкретным блокам, индексы меняются)
        self._parsed_cache.clear()
        self._syntax_error.clear()
        # Очищаем дерево и текстовое поле
        self.view.clear_tree()
        self.view.display_code("")

    def _generate_block_names(self, blocks):
        """Генерирует список имён для отображения во втором комбобоксе."""
        names = []
        for i, block in enumerate(blocks):
            name = self._extract_block_name(block)
            # Если блок помечен как синтаксически ошибочный, добавляем постфикс
            if block in self._syntax_error:
                name += " (синтаксическая ошибка)"
            names.append(f"{i+1:03d}: {name}")
        return names

    def _extract_block_name(self, block):
        """Извлекает имя блока (без изменений)."""
        if block.has_error:
            return "блок_кода (ошибка)"

        lines = block.content.splitlines()
        if not lines:
            return "блок_кода"

        start_idx = 0
        while start_idx < len(lines) and not lines[start_idx].strip():
            start_idx += 1
        if start_idx >= len(lines):
            return "блок_кода"

        # Поиск комментариев
        comment_lines = []
        i = start_idx
        while i < len(lines) and i - start_idx < 10:
            stripped = lines[i].strip()
            if stripped.startswith('#'):
                comment_lines.append(stripped[1:].strip())
                i += 1
            else:
                break
        if comment_lines:
            return " ".join(comment_lines)

        # Поиск class или def
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
            elif stripped.startswith('@'):
                i += 1
                continue
            elif stripped:
                break
            i += 1

        return "блок_кода"

    def on_type_selected(self, event):
        """Обработчик выбора языка в первом комбобоксе."""
        selected_index = self.view.type_combo.current()
        if 0 <= selected_index < len(self.available_languages):
            lang = self.available_languages[selected_index]
            if lang != self.current_lang:
                self._switch_language(lang)

    def on_show_structure(self):
        index = self.view.get_selected_block_index()
        if index < 0 or index >= len(self.current_blocks):
            return

        block = self.current_blocks[index]

        if block.has_error:
            self.view.show_error("Выбранный блок содержит ошибку парсинга (незакрытый код).")
            return

        if block in self._syntax_error:
            self.view.show_error("В блоке обнаружена синтаксическая ошибка.")
            return

        if block in self._parsed_cache:
            root = self._parsed_cache[block]
            self.view.display_structure(root)
            return

        # Определяем парсер по языку блока
        lang = block.language.lower() if block.language else ""
        parser_class = PARSERS.get(lang)
        if not parser_class:
            self.view.show_error(f"Нет парсера для языка {lang}.")
            return

        parser = parser_class()
        try:
            root = parser.parse(block.content)
            self._parsed_cache[block] = root
            self.view.display_structure(root)
        except Exception as e:
            logger.exception("Ошибка парсинга")
            self._syntax_error.add(block)
            # Обновляем имя блока в комбобоксе
            self.current_block_names = self._generate_block_names(self.current_blocks)
            self.view.set_block_combo_values(self.current_block_names)
            self.view.set_current_block_index(index)
            self.view.show_error(f"Синтаксическая ошибка в коде: {e}")

    def on_node_selected(self):
        """Обработчик выбора узла в дереве (без изменений)."""
        selected = self.view.tree.selection()
        if not selected:
            return
        item = selected[0]
        node = self.view.get_node_by_item(item)
        if node and node.lineno_start and node.lineno_end and self.current_blocks:
            # Определяем, какой блок сейчас выбран (текущий)
            index = self.view.get_selected_block_index()
            if index < 0 or index >= len(self.current_blocks):
                return
            block = self.current_blocks[index]
            code_lines = block.content.splitlines()
            start = node.lineno_start - 1
            end = node.lineno_end
            if start < 0:
                start = 0
            if end > len(code_lines):
                end = len(code_lines)
            if start < end:
                selected_code = "\n".join(code_lines[start:end])
                self.view.display_code(selected_code)
            else:
                self.view.display_code("")