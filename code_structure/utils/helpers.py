# code_structure/utils/helpers.py

import ast
import sys
import logging
import re
import textwrap
from typing import List, Optional

from code_structure.utils.logger import get_logger
logger = get_logger(__name__, level=logging.DEBUG)


class DocstringRemover(ast.NodeTransformer):
    @staticmethod
    def _is_docstring(node):
        if not isinstance(node, ast.Expr):
            return False
        val = node.value
        return (isinstance(val, ast.Constant) and isinstance(val.value, str)) or \
               (isinstance(val, ast.Str) and isinstance(val.s, str))

    def _remove_docstring(self, node):
        if hasattr(node, 'body') and node.body and self._is_docstring(node.body[0]):
            node.body.pop(0)
        self.generic_visit(node)
        return node

    visit_Module = _remove_docstring
    visit_ClassDef = _remove_docstring
    visit_FunctionDef = _remove_docstring
    visit_AsyncFunctionDef = _remove_docstring


def normalize_quotes(code: str) -> str:
    """Заменяет двойные кавычки на одинарные."""
    return code.replace('"', "'")


def remove_trailing_whitespace(lines: List[str]) -> List[str]:
    """Удаляет пробелы в конце каждой строки."""
    return [line.rstrip() for line in lines]


def remove_comments(lines: List[str]) -> List[str]:
    """Удаляет комментарии (всё после #, не внутри строк – упрощённо)."""
    result = []
    for line in lines:
        if '#' in line:
            line = line.split('#', 1)[0]
        result.append(line)
    return result


def remove_empty_lines(lines: List[str]) -> List[str]:
    """Удаляет строки, состоящие только из пробелов."""
    return [line for line in lines if line.strip() != '']


def remove_docstrings_simple(lines: List[str]) -> List[str]:
    """
    Удаляет docstrings (многострочные и однострочные) из списка строк.
    Используется как fallback при синтаксических ошибках.
    """
    result = []
    in_docstring = False
    docstring_char = None
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = '"""' if stripped.startswith('"""') else "'''"
                # Проверяем, не закрывается ли на той же строке
                if stripped.count(docstring_char) >= 2:
                    i += 1
                    continue
                else:
                    in_docstring = True
                    i += 1
                    continue
        else:
            if docstring_char in stripped:
                in_docstring = False
            i += 1
            continue
        result.append(line)
        i += 1
    return result


def normalize_code_lines(
    lines: List[str],
    remove_comments_flag: bool = True,
    remove_empty_lines_flag: bool = True,
    strip_trailing: bool = True,
    remove_docstrings_flag: bool = False
) -> str:
    """
    Общая нормализация строк кода:
    - удаляет docstrings (опционально)
    - удаляет комментарии (опционально)
    - удаляет пустые строки (опционально)
    - удаляет trailing whitespace (опционально)
    - нормализует кавычки
    Возвращает объединённую строку.
    """
    if remove_docstrings_flag:
        lines = remove_docstrings_simple(lines)
    if strip_trailing:
        lines = remove_trailing_whitespace(lines)
    if remove_comments_flag:
        lines = remove_comments(lines)
    if remove_empty_lines_flag:
        lines = remove_empty_lines(lines)
    result = '\n'.join(lines)
    return normalize_quotes(result)


def clean_code(code: str, keep_empty_lines: bool = False) -> str:
    """
    Очищает код от docstring, комментариев, пустых строк, trailing whitespace,
    нормализует кавычки.
    """
    if not code:
        return ""

    code = textwrap.dedent(code)

    remove_docstrings_flag = False

    try:
        tree = ast.parse(code)
        tree = DocstringRemover().visit(tree)
        if sys.version_info >= (3, 9):
            code = ast.unparse(tree)
    except (SyntaxError, TabError, IndentationError) as e:
        logger.debug("Обнаружена синтаксическая ошибка при очистке кода: %s", e)
        remove_docstrings_flag = True

    lines = code.splitlines()
    return normalize_code_lines(
        lines,
        remove_comments_flag=True,
        remove_empty_lines_flag=not keep_empty_lines,
        strip_trailing=True,
        remove_docstrings_flag=remove_docstrings_flag
    )


def extract_module_hint(block) -> Optional[str]:
    lines = block.content.splitlines()
    non_empty_count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        non_empty_count += 1
        if non_empty_count > 10:
            break
        match = re.search(r'#\s*([\w/\\]+(?:\.\w+)?)', stripped)
        if match:
            path = match.group(1)
            if '/' not in path and '\\' not in path and '.' not in path:
                continue
            if path.endswith('.py'):
                path = path[:-3]
            module_name = path.replace('/', '.').replace('\\', '.')
            module_name = module_name.strip('.')
            if module_name:
                return module_name
    return None