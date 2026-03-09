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
                desc = f"БлокКода{self.language.capitalize()}"
            else:
                desc = "БлокТекста"
        desc = self._sanitize_filename(desc)
        return f"{self.index:03d}_{desc}.{self.file_extension}"


class BlockParser:
    """Разбирает текст на блоки, выделяя блоки кода, обозначенные ```, и остальной текст.
    
    Атрибуты:
        unclosed_blocks: количество незакрытых блоков кода, обнаруженных при последнем вызове parse.
    """

    def __init__(self):
        self.unclosed_blocks = 0

    def _find_closing_backticks(self, text: str, pos: int) -> int:
        """Ищет позицию закрывающих ```, начиная с pos, учитывая возможные пробелы в начале строки.
        Возвращает индекс символа '`' (первого из трёх) или -1, если не найдено."""
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
        """Ищет позицию открывающих ```, начиная с pos, учитывая возможные пробелы в начале строки.
        Возвращает индекс символа '`' (первого из трёх) или -1, если не найдено."""
        line_start = pos
        while line_start > 0 and text[line_start - 1] != '\n':
            line_start -= 1
        i = line_start
        while i < len(text) and text[i] in (' ', '\t'):
            i += 1
        if i + 3 <= len(text) and text[i:i+3] == '```':
            # Проверим, что после ``` нет символов (кроме пробелов) до конца строки,
            # чтобы отличать от закрывающих? Для открывающих допустимо, что после ``` может быть язык.
            # В любом случае, если мы нашли ``` в начале строки, это может быть как открывающий, так и закрывающий.
            # Мы используем это в состоянии CODE, чтобы принудительно закрыть блок при встрече новой ```.
            return i
        return -1

    def parse(self, text: str) -> List[MessageBlock]:
        """Разбирает текст на блоки, используя конечный автомат.
        
        Особенность: если в состоянии CODE встречается новая открывающая последовательность ```,
        текущий блок считается закрытым (без ошибки) и начинается новый блок.
        Это позволяет корректно обрабатывать случаи, когда автор забыл закрыть предыдущий блок,
        но начал новый.
        """
        logger.debug(f"Начало парсинга, длина текста: {len(text)}")
        self.unclosed_blocks = 0
        blocks = []
        i = 0
        length = len(text)
        state = 'TEXT'          # 'TEXT', 'CODE_START', 'CODE'
        start = 0                # начало текущего фрагмента
        lang = None

        while i < length:
            if state == 'TEXT':
                # Ищем открывающие ``` в начале строки (с учётом пробелов)
                opening_pos = self._find_opening_backticks(text, i)
                if opening_pos != -1 and opening_pos == i:  # проверяем, что это именно в текущей позиции
                    logger.debug(f"Найдены открывающие ``` на позиции {i}")
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
                # Считываем язык до конца строки
                lang_start = i
                while i < length and text[i] != '\n':
                    i += 1
                lang = text[lang_start:i].strip() or None
                logger.debug(f"Прочитан язык блока: {lang}")
                if i < length and text[i] == '\n':
                    i += 1
                start = i
                state = 'CODE'

            elif state == 'CODE':
                # Сначала ищем закрывающие ``` в текущей позиции
                closing_pos = self._find_closing_backticks(text, i)
                if closing_pos != -1:
                    # Нашли закрывающие
                    logger.debug(f"Найдены закрывающие ``` на позиции {closing_pos}")
                    code = text[start:closing_pos].rstrip('\n')
                    blocks.append(MessageBlock(len(blocks), code, language=lang))
                    i = closing_pos + 3
                    if i < length and text[i] == '\n':
                        i += 1
                    start = i
                    state = 'TEXT'
                    lang = None
                else:
                    # Нет закрывающих в текущей позиции. Проверим, не начинается ли новый блок.
                    opening_pos = self._find_opening_backticks(text, i)
                    if opening_pos != -1 and opening_pos == i:
                        # Начинается новый блок. Закрываем текущий принудительно.
                        logger.debug(f"В состоянии CODE найдены новые открывающие на позиции {i}, принудительно закрываем текущий блок")
                        code = text[start:i].rstrip('\n')
                        blocks.append(MessageBlock(len(blocks), code, language=lang))
                        # Не увеличиваем unclosed_blocks, так как это нормальное принудительное закрытие
                        i = opening_pos + 3
                        start = i
                        state = 'CODE_START'
                        lang = None
                    else:
                        i += 1

        # Обработка остатка текста после цикла
        if start < length:
            remaining = text[start:]
            if state == 'CODE':
                if remaining.strip():
                    self.unclosed_blocks += 1
                    logger.debug(
                        f"Незакрытый блок кода в конце текста. Язык: {lang}, длина остатка: {len(remaining)}"
                    )
                    marker = "\n<<<ОШИБКА ПАРСИНГА БЛОКА - ОТСУТСВУЮТ ЗАКРЫВАЮЩИЕ СИМВОЛЫ \"```\">>>"
                    logger.debug(f"Добавляю маркер в блок. Длина до: {len(remaining)}")
                    remaining += marker
                    logger.debug(f"Длина после: {len(remaining)}")
                    blocks.append(MessageBlock(len(blocks), remaining, language=lang))
                else:
                    logger.debug("Остаток пустой или состоит из пробелов, не считаем незакрытым блоком")
            elif state == 'TEXT' and remaining.strip():
                logger.debug(f"Остаток текста (не блок): {len(remaining)} символов")
                blocks.append(MessageBlock(len(blocks), remaining, language=None))
            else:
                logger.debug("Остаток пустой или пробелы, игнорируем")

        logger.debug(f"Парсинг завершён. Всего блоков: {len(blocks)}, незакрытых: {self.unclosed_blocks}")
        return blocks