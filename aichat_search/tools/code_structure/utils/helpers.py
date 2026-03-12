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