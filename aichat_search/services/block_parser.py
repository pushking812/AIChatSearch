# aichat_search/services/block_parser.py

import re
from typing import List, Optional


class MessageBlock:
    """Представляет один блок сообщения (текст или код)."""

    def __init__(self, index: int, content: str, language: Optional[str] = None):
        self.index = index
        self.content = content
        self.language = language  # например 'python', 'markdown', None для простого текста

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
        """Генерирует имя файла для блока с трёхзначным номером."""
        if self.language:
            desc = f"БлокКода{self.language.capitalize()}"
        else:
            desc = "БлокТекста"
        return f"{self.index:03d}_{desc}.{self.file_extension}"


class BlockParser:
    """Разбирает текст на блоки, выделяя блоки кода, обозначенные ```, и остальной текст."""

    @staticmethod
    def parse(text: str) -> List[MessageBlock]:
        blocks = []
        # Поиск блоков ```language\ncontent```
        pattern = re.compile(r'```(\w*)\n(.*?)```', re.DOTALL)
        pos = 0
        block_index = 0

        for match in pattern.finditer(text):
            start, end = match.span()
            # Текст до блока
            if start > pos:
                content = text[pos:start].strip()
                if content:
                    blocks.append(MessageBlock(block_index, content, language=None))
                    block_index += 1
            # Сам блок кода
            lang = match.group(1).strip() or None
            code = match.group(2).strip()
            if code:
                blocks.append(MessageBlock(block_index, code, language=lang))
                block_index += 1
            pos = end

        # Остаток после последнего блока
        if pos < len(text):
            content = text[pos:].strip()
            if content:
                blocks.append(MessageBlock(block_index, content, language=None))

        return blocks