# aichat_search/services/block_parser.py

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class MessageBlock:
    """Представляет один блок сообщения (текст или код)."""

    def __init__(self, index: int, content: str, language: Optional[str] = None, block_type: str = 'response'):
        self.index = index
        self.content = content
        self.language = language
        self.block_type = block_type  # 'request' или 'response'
        self.has_error = False        # True, если блок содержит ошибку парсинга (незакрытый код)

    def _sanitize_filename(self, text: str) -> str:
        """Удаляет из текста символы, недопустимые в именах файлов.
        Оставляет только буквы, цифры, пробелы, дефисы и подчёркивания."""
        return ''.join(c for c in text if c.isalnum() or c in (' ', '-', '_')).rstrip()

    @property
    def file_extension(self) -> str:
        """Определяет расширение файла на основе языка."""
        if not self.language:
            return 'txt'
        lang_map = {
            'python': 'py',
            'markdown': 'md',
            'json': 'json',
            'html': 'html',
            'css': 'css',
            'javascript': 'js',
            'js': 'js',
            'bash': 'sh',
            'shell': 'sh',
            'sql': 'sql',
            'xml': 'xml',
            'yaml': 'yaml',
            'yml': 'yaml',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
            'csharp': 'cs',
            'go': 'go',
            'rust': 'rs',
            'ruby': 'rb',
            'php': 'php',
            'perl': 'pl',
            'lua': 'lua',
            'r': 'r',
            'matlab': 'm',
            'swift': 'swift',
            'kotlin': 'kt',
            'scala': 'scala',
            'dart': 'dart',
            'typescript': 'ts',
            'ts': 'ts',
            'jsx': 'jsx',
            'tsx': 'tsx',
            'vue': 'vue',
            'svelte': 'svelte',
            'dockerfile': 'dockerfile',
            'makefile': 'mk',
            'cmake': 'cmake',
            'diff': 'diff',
            'patch': 'patch',
            'ini': 'ini',
            'conf': 'conf',
            'properties': 'properties',
            'toml': 'toml',
            'tex': 'tex',
            'latex': 'tex',
            'bib': 'bib',
            'csv': 'csv',
            'tsv': 'tsv',
            'ps1': 'ps1',
            'bat': 'bat',
            'cmd': 'bat',
            'powershell': 'ps1',
            'nginx': 'nginx',
            'apache': 'conf',
        }
        return lang_map.get(self.language.lower(), 'txt')

    def filename(self) -> str:
        """Генерирует имя файла для блока с трёхзначным номером.
        Описание очищается от недопустимых символов."""
        if self.block_type == 'request':
            desc = "Запрос"
        else:
            if self.language:
                # Используем только первое слово языка для описания
                base_lang = self.language.split()[0] if self.language else None
                desc = f"БлокКода{base_lang.capitalize()}" if base_lang else "БлокКода"
            else:
                desc = "БлокТекста"
        desc = self._sanitize_filename(desc)
        return f"{self.index:03d}_{desc}.{self.file_extension}"


class BlockParser:
    def __init__(self):
        self.unclosed_blocks = 0

    def _find_closing_backticks(self, text: str, pos: int) -> int:
        line_start = pos
        while line_start > 0 and text[line_start - 1] != '\n':
            line_start -= 1
        i = line_start
        while i < len(text) and text[i] in (' ', '\t'):
            i += 1
        if i + 3 <= len(text) and text[i:i+3] == '```':
            after = i + 3
            if after == len(text) or text[after] == '\n':
                return i
        return -1

    def _find_opening_backticks(self, text: str, pos: int) -> int:
        line_start = pos
        while line_start > 0 and text[line_start - 1] != '\n':
            line_start -= 1
        i = line_start
        while i < len(text) and text[i] in (' ', '\t'):
            i += 1
        if i + 3 <= len(text) and text[i:i+3] == '```':
            return i
        return -1

    def parse(self, text: str) -> List[MessageBlock]:
        self.unclosed_blocks = 0
        blocks = []
        i = 0
        length = len(text)
        state = 'TEXT'          # 'TEXT', 'CODE_START', 'CODE'
        start = 0
        lang = None

        while i < length:
            if state == 'TEXT':
                opening_pos = self._find_opening_backticks(text, i)
                if opening_pos != -1 and opening_pos == i:
                    if i > start:
                        content = text[start:i].rstrip('\n')
                        if content:
                            blocks.append(MessageBlock(len(blocks), content, language=None))
                    i = opening_pos + 3
                    start = i
                    state = 'CODE_START'
                else:
                    i += 1

            elif state == 'CODE_START':
                lang_start = i
                while i < length and text[i] != '\n':
                    i += 1
                lang_str = text[lang_start:i].strip()
                lang = lang_str.split()[0] if lang_str else None
                if i < length and text[i] == '\n':
                    i += 1
                start = i
                state = 'CODE'

            elif state == 'CODE':
                closing_pos = self._find_closing_backticks(text, i)
                if closing_pos != -1:
                    code = text[start:closing_pos].rstrip('\n')
                    blocks.append(MessageBlock(len(blocks), code, language=lang))
                    i = closing_pos + 3
                    if i < length and text[i] == '\n':
                        i += 1
                    start = i
                    state = 'TEXT'
                    lang = None
                else:
                    opening_pos = self._find_opening_backticks(text, i)
                    if opening_pos != -1 and opening_pos == i:
                        code = text[start:i].rstrip('\n')
                        blocks.append(MessageBlock(len(blocks), code, language=lang))
                        i = opening_pos + 3
                        start = i
                        state = 'CODE_START'
                        lang = None
                    else:
                        i += 1

        if start < length:
            remaining = text[start:]
            if state == 'CODE':
                if remaining.strip():
                    self.unclosed_blocks += 1
                    marker = "\n<<<ОШИБКА ПАРСИНГА БЛОКА - ОТСУТСТВУЮТ ЗАКРЫВАЮЩИЕ СИМВОЛЫ \"```\">>>"
                    remaining += marker
                    blocks.append(MessageBlock(len(blocks), remaining, language=lang))
            elif state == 'TEXT' and remaining.strip():
                blocks.append(MessageBlock(len(blocks), remaining, language=None))

        return blocks