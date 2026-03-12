# aichat_search/tools/code_structure/utils/helpers.py

import re
from typing import Optional
from aichat_search.services.block_parser import MessageBlock


def extract_module_hint(block: MessageBlock) -> Optional[str]:
    """
    Извлекает имя модуля из комментария в начале блока.
    Ищет строку вида '# path/to/module.py' или '# path.to.module' в первых 10 непустых строках.
    Возвращает имя модуля в формате с точками (package.module) или None.
    """
    lines = block.content.splitlines()
    non_empty_count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        non_empty_count += 1
        if non_empty_count > 10:
            break

        # Ищем комментарий, содержащий путь с разделителями или точками
        match = re.search(r'#\s*([\w/\\]+(?:\.\w+)?)', stripped)
        if match:
            path = match.group(1)
            # Проверяем, что извлечённая строка содержит разделитель (/, \) или точку
            if '/' not in path and '\\' not in path and '.' not in path:
                continue  # не похоже на путь к модулю
            # Убираем возможное расширение .py
            if path.endswith('.py'):
                path = path[:-3]
            # Заменяем разделители на точки
            module_name = path.replace('/', '.').replace('\\', '.')
            # Убираем лишние точки в начале/конце
            module_name = module_name.strip('.')
            if module_name:
                return module_name
    return None


def clean_code(code: str) -> str:
    """
    Очищает код от docstring, комментариев, пустых строк и лишних пробелов.
    Возвращает "сжатую" версию для сравнения.
    """
    if not code:
        return ""

    lines = code.splitlines()
    result_lines = []
    in_docstring = False
    docstring_char = None

    for line in lines:
        stripped = line.strip()

        # Обработка docstring
        if not in_docstring:
            # Начало docstring (тройные кавычки)
            if stripped.startswith('"""') or stripped.startswith("'''"):
                # Проверяем, не закрывается ли он на той же строке
                if stripped.count('"""') == 1 and stripped.endswith('"""') or \
                   stripped.count("'''") == 1 and stripped.endswith("'''"):
                    # Однострочный docstring
                    continue
                else:
                    in_docstring = True
                    docstring_char = '"""' if stripped.startswith('"""') else "'''"
                    # Если после открывающих сразу есть закрывающие (например, """text""")
                    if stripped.count(docstring_char) == 2:
                        in_docstring = False
                    continue
        else:
            # Ищем закрывающие тройные кавычки
            if docstring_char in stripped:
                in_docstring = False
                # Если после закрывающих есть код, он будет обработан в следующих итерациях,
                # но по упрощению пропускаем всю строку
                continue
            else:
                continue

        # Удаляем комментарии (всё после #, не внутри строк – упрощённо)
        if '#' in line:
            line = line.split('#', 1)[0]

        # Убираем пустые строки
        if stripped == "":
            continue

        # Нормализуем пробелы: заменяем табуляцию на 4 пробела, убираем лишние пробелы
        line = line.replace('\t', '    ')
        line = re.sub(r'[ \t]+', ' ', line).strip()

        result_lines.append(line)

    return '\n'.join(result_lines)