# aichat_search/services/block_parser.py

from typing import List, Optional


class MessageBlock:
    """Представляет один блок сообщения (текст или код)."""

    def __init__(self, index: int, content: str, language: Optional[str] = None, block_type: str = 'response'):
        self.index = index
        self.content = content
        self.language = language
        self.block_type = block_type  # 'request' или 'response'

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
        if self.block_type == 'request':
            desc = "Запрос"
        else:
            if self.language:
                desc = f"БлокКода{self.language.capitalize()}"
            else:
                desc = "БлокТекста"
        return f"{self.index:03d}_{desc}.{self.file_extension}"


class BlockParser:
    """Разбирает текст на блоки, выделяя блоки кода, обозначенные ```, и остальной текст.
    
    Атрибуты:
        unclosed_blocks: количество незакрытых блоков кода, обнаруженных при последнем вызове parse.
    """

    def __init__(self):
        self.unclosed_blocks = 0

    def parse(self, text: str) -> List[MessageBlock]:
        """Разбирает текст на блоки, используя конечный автомат.
        
        Возвращает список блоков MessageBlock.
        Если блок кода не закрыт до конца текста, в его содержимое добавляется маркер ошибки,
        и счётчик unclosed_blocks увеличивается.
        """
        self.unclosed_blocks = 0
        blocks = []
        i = 0
        length = len(text)
        state = 'TEXT'
        start = 0
        lang = None

        while i < length:
            if state == 'TEXT':
                # Ищем открывающие ``` в начале строки
                if text[i:i+3] == '```' and (i == 0 or text[i-1] == '\n'):
                    # Сохраняем предшествующий текст
                    if i > start:
                        content = text[start:i].rstrip('\n')
                        if content:
                            blocks.append(MessageBlock(len(blocks), content, language=None))
                    i += 3
                    start = i
                    state = 'CODE_START'
                else:
                    i += 1

            elif state == 'CODE_START':
                # Считываем язык до конца строки
                lang_start = i
                while i < length and text[i] != '\n':
                    i += 1
                lang = text[lang_start:i].strip() or None
                # Пропускаем перевод строки, если он есть
                if i < length and text[i] == '\n':
                    i += 1
                start = i
                state = 'CODE'

            elif state == 'CODE':
                # Ищем закрывающие ``` в начале строки
                if text[i:i+3] == '```' and (i == 0 or text[i-1] == '\n'):
                    # Код до этого момента (без закрывающих)
                    code = text[start:i].rstrip('\n')
                    blocks.append(MessageBlock(len(blocks), code, language=lang))
                    i += 3
                    start = i
                    state = 'TEXT'
                    lang = None
                else:
                    i += 1

        # Обработка остатка текста после цикла
        if start < length:
            remaining = text[start:]
            if state == 'CODE':
                # Незакрытый блок кода
                self.unclosed_blocks += 1
                # Добавляем маркер ошибки в конец содержимого
                remaining += "\n<<<ОШИБКА ПАРСИНГА БЛОКА - ОТСУТСВУЮТ ЗАКРЫВАЮЩИЕ СИМВОЛЫ \"```\">>>"
                blocks.append(MessageBlock(len(blocks), remaining, language=lang))
            elif state == 'TEXT' and remaining.strip():
                blocks.append(MessageBlock(len(blocks), remaining, language=None))
            # Если остаток пустой, ничего не добавляем

        return blocks