# code_structure/utils/helpers.py

import ast
import sys
import logging
import re
from typing import Optional
import textwrap

from code_structure.utils.logger import get_logger
logger = get_logger(__name__, level = logging.DEBUG)

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



def _legacy_clean_code(code: str) -> str:
    """
    Очищает код от docstring, комментариев, пустых строк, но сохраняет внутренние отступы.
    Сначала удаляет общий ведущий отступ (как textwrap.dedent).
    Используется как fallback при синтаксических ошибках.
    """
    if not code:
        return ""

    # 1. Убираем общий ведущий отступ (выравниваем код по левому краю)
    code = textwrap.dedent(code)

    lines = code.splitlines()
    result_lines = []
    in_docstring = False
    docstring_char = None

    for line in lines:
        # Сохраняем отступ после выравнивания
        stripped = line.lstrip()
        indent = line[:len(line)-len(stripped)]

        # Обработка docstring
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                # Проверяем, не закрывается ли на той же строке
                if (stripped.count('"""') == 1 and stripped.endswith('"""')) or \
                   (stripped.count("'''") == 1 and stripped.endswith("'''")):
                    # Однострочный docstring – пропускаем строку
                    continue
                else:
                    in_docstring = True
                    docstring_char = '"""' if stripped.startswith('"""') else "'''"
                    # Если открытие и закрытие в одной строке (например, """text""")
                    if stripped.count(docstring_char) == 2:
                        in_docstring = False
                    continue
        else:
            # Внутри docstring, ищем закрытие
            if docstring_char in stripped:
                in_docstring = False
                rest = stripped.split(docstring_char, 1)[1]
                if rest.strip():
                    stripped = rest.lstrip()
                    line = indent + stripped
                else:
                    continue
            else:
                continue

        # Удаление комментариев (всё после #, не внутри строк – упрощённо)
        if '#' in stripped:
            stripped = stripped.split('#', 1)[0]
            line = indent + stripped

        # Удаляем пустые строки
        if stripped.strip() == "":
            continue

        result_lines.append(line)

    return '\n'.join(result_lines)


def clean_code(code: str, keep_empty_lines: bool = False) -> str:
    try:
        tree = ast.parse(code)
        tree = DocstringRemover().visit(tree)
        if sys.version_info >= (3, 9):
            new_code = ast.unparse(tree)
        else:
            logger.warning("Версия Python ниже 3.9, используется fallback")
            return _legacy_clean_code(code)
        if not keep_empty_lines:
            lines = [line for line in new_code.splitlines() if line.strip() != '']
            return '\n'.join(lines)
        return new_code
    except (SyntaxError, TabError, IndentationError):
        logger.debug("Синтаксическая ошибка, используется простая очистка")
        return _legacy_clean_code(code)


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