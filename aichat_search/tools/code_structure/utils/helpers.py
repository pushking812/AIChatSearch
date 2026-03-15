# aichat_search/tools/code_structure/utils/helpers.py
import ast
import sys
import logging
import re
from typing import Optional
from aichat_search.services.block_parser import MessageBlock


logger = logging.getLogger(__name__)


class DocstringRemover(ast.NodeTransformer):
    """Удаляет docstring из модулей, классов и функций с рекурсивным обходом."""
    
    @staticmethod
    def _is_docstring(node):
        """Проверяет, является ли узел docstring."""
        if not isinstance(node, ast.Expr):
            return False
        val = node.value
        return (isinstance(val, ast.Constant) and isinstance(val.value, str)) or \
               (isinstance(val, ast.Str) and isinstance(val.s, str))
    
    def _remove_docstring(self, node):
        """Удаляет docstring если он есть и рекурсивно обходит потомков."""
        if hasattr(node, 'body') and node.body and self._is_docstring(node.body[0]):
            node.body.pop(0)
        
        # Рекурсивный обход всех потомков
        self.generic_visit(node)
        return node
    
    # Явное назначение методов для всех типов узлов, где может быть docstring
    visit_Module = _remove_docstring
    visit_ClassDef = _remove_docstring
    visit_FunctionDef = _remove_docstring
    visit_AsyncFunctionDef = _remove_docstring


def _legacy_clean_code(code: str) -> str:
    """
    Заглушка для синтаксически некорректного кода или старых версий Python.
    Будет реализована через re или другие инструменты.
    """
    logger.debug("Синтаксическая ошибка в коде, используется fallback (без изменений)")
    return code


def clean_code(code: str, keep_empty_lines: bool = False) -> str:
    """
    Приводит код к каноническому виду для сравнения версий.
    
    Для синтаксически корректного кода:
      - удаляет docstring из модуля, классов и функций (рекурсивно);
      - использует ast.unparse для нормализации отступов, пробелов и строк;
      - опционально удаляет все пустые строки (по умолчанию удаляет).
    
    Args:
        code: исходный Python код
        keep_empty_lines: если True, сохраняет пустые строки
    
    Returns:
        Нормализованный код
    """
    try:
        tree = ast.parse(code)
    except (SyntaxError, TabError, IndentationError):
        return _legacy_clean_code(code)

    # Рекурсивно удаляем все docstring
    tree = DocstringRemover().visit(tree)

    if sys.version_info >= (3, 9):
        new_code = ast.unparse(tree)
    else:
        logger.warning("Версия Python ниже 3.9, используется fallback")
        return _legacy_clean_code(code)

    # Опциональное удаление пустых строк
    if keep_empty_lines:
        return new_code
    
    # Удаляем пустые строки (состоящие только из пробелов)
    lines = [line for line in new_code.splitlines() if line.strip() != '']
    return '\n'.join(lines)
    
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
