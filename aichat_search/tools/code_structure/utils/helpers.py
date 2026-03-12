# aichat_search/tools/code_structure/utils/helpers.py

import re
from typing import Optional
from aichat_search.services.block_parser import MessageBlock


def extract_module_hint(block: MessageBlock) -> Optional[str]:
    """
    Извлекает имя модуля из комментария в начале блока.
    Ищет строку вида '# path/to/module.py' и преобразует в 'path.to.module'.
    Возвращает None, если не найдено.
    """
    lines = block.content.splitlines()
    # Просматриваем первые несколько непустых строк
    non_empty = 0
    for line in lines:
        if line.strip():
            non_empty += 1
            if non_empty > 5:
                break
            # Ищем комментарий с .py
            match = re.search(r'#\s*([\w/]+\.py)', line)
            if match:
                path = match.group(1)
                # Преобразуем путь в имя модуля: заменяем / на ., убираем .py
                module_name = path.replace('/', '.').replace('.py', '')
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
                if stripped.count('"""') == 1 and stripped.endswith('"""'):
                    # Однострочный docstring
                    continue
                else:
                    in_docstring = True
                    docstring_char = '"""' if stripped.startswith('"""') else "'''"
                    # Если после открывающих есть ещё текст (например, """text"""), нужно проверить закрытие
                    if stripped.count(docstring_char) == 2:
                        # docstring закрыт на этой же строке
                        in_docstring = False
                    continue
        else:
            # Ищем закрывающие тройные кавычки
            if docstring_char in stripped:
                in_docstring = False
                # Если после закрывающих есть код, надо его обработать, но по упрощению пропускаем строку
                continue
            else:
                continue

        # Удаляем комментарии (все, что после #, не внутри строк)
        # Простой вариант: убираем всё после #, но нужно учитывать # внутри строк.
        # Для простоты пока так, позже можно улучшить.
        if '#' in line:
            # Находим позицию # не внутри строки (очень упрощённо)
            line = line.split('#', 1)[0]

        # Убираем пустые строки
        if stripped == "":
            continue

        # Нормализуем пробелы: заменяем табуляцию на 4 пробела, убираем лишние пробелы
        line = line.replace('\t', '    ')
        line = re.sub(r'[ \t]+', ' ', line).strip()

        result_lines.append(line)

    return '\n'.join(result_lines)