import logging
from typing import List, Optional

from ...services.block_parser import BlockParser
from .view import CodeStructureWindow
from .parser import PARSERS
from .services.block_manager import BlockManager
from .models.block_info import MessageBlockInfo

logger = logging.getLogger(__name__)


class CodeStructureController:
    def __init__(self, parent, messages: List[str]):
        """
        :param parent: родительское окно
        :param messages: список текстов сообщений (может быть один)
        """
        self.parent = parent
        self.messages = messages

        self.view = CodeStructureWindow(parent)
        self.view.set_controller(self)

        # Менеджер блоков
        self.block_manager = BlockManager()

        # Текущие данные для отображения в левой панели
        self.current_lang: Optional[str] = None
        self.current_block_index: int = -1

        # Загружаем все блоки из сообщений
        self._load_all_blocks()
        
        self._resolve_unknown_modules()

        if self.block_manager.get_languages():
            self._fill_language_combo()
            # Выбираем первый язык и загружаем его блоки
            self.current_lang = self.block_manager.get_languages()[0]
            self._switch_language(self.current_lang)
            self.view.show_button.config(command=self.on_show_structure)
        else:
            self.view.show_error("В сообщениях нет блоков с поддерживаемыми языками.")
            self.view.destroy()

    def _load_all_blocks(self):
        """Загружает все блоки из сообщений через BlockManager."""
        self.block_manager.load_from_messages(self.messages)
        
    def _resolve_unknown_modules(self):
        """Вызывает диалог для назначения модулей блокам без подсказки."""
        # Собираем блоки без module_hint
        unknown = []
        known_modules = set()
        for block_info in self.block_manager.get_all_blocks():
            if block_info.module_hint:
                known_modules.add(block_info.module_hint)
            else:
                unknown.append((
                    block_info.block_id,
                    block_info.language,
                    block_info.content
                ))

        if not unknown:
            return

        # Вызываем диалог
        from .ui.dialogs import ModuleAssignmentDialog
        dialog = ModuleAssignmentDialog(self.view, unknown, sorted(known_modules))
        self.view.wait_window(dialog)  # ждём закрытия

        if dialog.result:
            # Обновляем module_hint у соответствующих блоков
            for block_info in self.block_manager.get_all_blocks():
                if block_info.block_id in dialog.result:
                    block_info.module_hint = dialog.result[block_info.block_id]

    def _fill_language_combo(self):
        """Заполняет комбобокс языков."""
        display_names = [lang.capitalize() for lang in self.block_manager.get_languages()]
        self.view.set_type_combo_values(display_names)

    def _switch_language(self, lang: str):
        """Переключает текущий язык, обновляет второй комбобокс."""
        self.current_lang = lang
        blocks = self.block_manager.get_blocks_by_lang(lang)
        block_names = self._generate_block_names(blocks)
        self.view.set_block_combo_values(block_names)
        if block_names:
            self.view.set_current_block_index(len(block_names) - 1)
        # Очищаем дерево и текстовое поле
        self.view.clear_tree()
        self.view.display_code("")

    def _generate_block_names(self, blocks: List[MessageBlockInfo]) -> List[str]:
        """Генерирует список имён для отображения во втором комбобоксе."""
        names = []
        for i, block_info in enumerate(blocks):
            name = self._extract_block_name(block_info)
            if block_info.syntax_error:
                name += " (синтаксическая ошибка)"
            names.append(f"{i+1:03d}: {name}")
        return names

    def _extract_block_name(self, block_info: MessageBlockInfo) -> str:
        """Извлекает имя блока (без изменений, как было)."""
        if block_info.syntax_error:
            return "блок_кода (ошибка)"

        lines = block_info.content.splitlines()
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
        languages = self.block_manager.get_languages()
        if 0 <= selected_index < len(languages):
            lang = languages[selected_index]
            if lang != self.current_lang:
                self._switch_language(lang)

    def on_show_structure(self):
        """Показывает структуру выбранного блока."""
        index = self.view.get_selected_block_index()
        if index < 0:
            return

        blocks = self.block_manager.get_blocks_by_lang(self.current_lang)
        if index >= len(blocks):
            return

        block_info = blocks[index]

        if block_info.syntax_error:
            self.view.show_error(f"Выбранный блок содержит ошибку парсинга: {block_info.syntax_error}")
            return

        if block_info.tree is None:
            self.view.show_error("Дерево блока не построено.")
            return

        # Отображаем структуру
        self.view.display_structure(block_info.tree)

    def on_node_selected(self):
        """Обработчик выбора узла в дереве (без изменений)."""
        selected = self.view.tree.selection()
        if not selected:
            return
        item = selected[0]
        node = self.view.get_node_by_item(item)
        if node and node.lineno_start and node.lineno_end:
            # Определяем текущий блок
            index = self.view.get_selected_block_index()
            if index < 0:
                return
            blocks = self.block_manager.get_blocks_by_lang(self.current_lang)
            if index >= len(blocks):
                return
            block_info = blocks[index]
            code_lines = block_info.content.splitlines()
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