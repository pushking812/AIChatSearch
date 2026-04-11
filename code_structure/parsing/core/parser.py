# code_structure/parsing/core/parser.py

import ast
import logging
import re
from abc import ABC, abstractmethod
from typing import List, Optional

from code_structure.models.block import Block
from code_structure.models.code_node import (
    CodeNode,
    ModuleNode,
    ClassNode,
    FunctionNode,
    MethodNode,
    CodeBlockNode,
    ImportNode,
    CommentNode
)

import logging
from code_structure.utils.logger import get_logger
logger = get_logger(__name__, level=logging.DEBUG)


class CodeParser(ABC):
    @abstractmethod
    def parse(self, block: Block) -> ModuleNode:
        pass


class PythonParser(CodeParser):
    def parse(self, block: Block) -> ModuleNode:
        try:
            tree = ast.parse(block.content)
            last_line = block.content.count('\n') + 1
            module_node = ModuleNode("", block, 1, last_line)
            self._process_body(tree.body, module_node, block, is_method_body=False)
            return module_node
        except SyntaxError as e:
            logger.debug(f"Синтаксическая ошибка в блоке {block.id}: {e}")
            raise
        except Exception as e:
            logger.error(f"КРИТИЧЕСКАЯ ОШИБКА В ПАРСЕРЕ ДЛЯ БЛОКА {block.id}: {e}", exc_info=True)
            raise

    def _process_body(self, body, parent_node: CodeNode, block: Block, is_method_body: bool = False):
        i = 0
        n = len(body)
        while i < n:
            node = body[i]

            if isinstance(node, ast.ClassDef):
                bases = ", ".join(self._format_base(b) for b in node.bases)
                class_node = ClassNode(
                    name=node.name,
                    bases=bases,
                    block=block,
                    start_line=node.lineno,
                    end_line=node.end_lineno,
                    parent=parent_node
                )
                self._process_body(node.body, class_node, block, is_method_body=False)
                parent_node.add_child(class_node)
                i += 1

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args_str = self._format_args(node.args, node.returns)
                is_method = isinstance(parent_node, ClassNode)
                if not is_method:
                    if node.args.args and node.args.args[0].arg in ('self', 'cls'):
                        is_method = True
                if is_method:
                    func_node = MethodNode(
                        name=node.name,
                        signature=args_str,
                        block=block,
                        start_line=node.lineno,
                        end_line=node.end_lineno,
                        parent=parent_node
                    )
                else:
                    func_node = FunctionNode(
                        name=node.name,
                        signature=args_str,
                        block=block,
                        start_line=node.lineno,
                        end_line=node.end_lineno,
                        parent=parent_node
                    )
                self._process_body(node.body, func_node, block, is_method_body=True)
                parent_node.add_child(func_node)
                i += 1

            else:
                # Обработка импортов, комментариев и кода верхнего уровня
                start = i
                while i < n and not isinstance(body[i], (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    i += 1

                first_node = body[start]
                last_node = body[i-1]
                end_line = last_node.end_lineno if hasattr(last_node, 'end_lineno') else last_node.lineno
                lines = block.content.splitlines()
                fragment_lines = lines[first_node.lineno-1:end_line]

                # Разделяем фрагмент на импорты/комментарии и остальной код
                import_lines = []
                code_lines = []
                in_import_block = True
                for line in fragment_lines:
                    stripped = line.strip()
                    if not stripped or stripped.startswith('#'):
                        if in_import_block:
                            import_lines.append(line)
                        else:
                            code_lines.append(line)
                    elif stripped.startswith(('import ', 'from ')):
                        import_lines.append(line)
                    else:
                        in_import_block = False
                        code_lines.append(line)

                if import_lines:
                    import_statement = '\n'.join(import_lines).rstrip()
                    import_node = ImportNode(
                        statement=import_statement,
                        block=block,
                        start_line=first_node.lineno,
                        end_line=first_node.lineno + len(import_lines) - 1,
                        parent=parent_node
                    )
                    parent_node.add_child(import_node)
                    logger.debug(f"Created ImportNode in block {block.id}: lines {import_node.start_line}-{import_node.end_line}")

                if code_lines:
                    code_start_line = first_node.lineno + len(import_lines)
                    code_end_line = end_line
                    code_block_node = CodeBlockNode(
                        name="code_block",
                        block=block,
                        start_line=code_start_line,
                        end_line=code_end_line,
                        parent=parent_node
                    )
                    parent_node.add_child(code_block_node)
                    logger.debug(f"Created CodeBlockNode in block {block.id}: lines {code_start_line}-{code_end_line}")

    # ---------- вспомогательные методы (без изменений) ----------
    def _format_base(self, base_node):
        if isinstance(base_node, ast.Name):
            return base_node.id
        elif isinstance(base_node, ast.Attribute):
            return self._get_attr_name(base_node)
        else:
            return "?"

    def _get_attr_name(self, attr_node):
        if isinstance(attr_node, ast.Name):
            return attr_node.id
        elif isinstance(attr_node, ast.Attribute):
            return self._get_attr_name(attr_node.value) + "." + attr_node.attr
        else:
            return "?"

    def _format_args(self, args_node, returns_node=None):
        args = []
        defaults = args_node.defaults
        n_pos_args = len(args_node.args)
        n_defaults = len(defaults)

        for i, arg in enumerate(args_node.args):
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {self._format_annotation(arg.annotation)}"
            default_offset = n_pos_args - n_defaults
            if i >= default_offset:
                default_index = i - default_offset
                if default_index < n_defaults:
                    default_value = self._format_constant(defaults[default_index])
                    if default_value is not None:
                        arg_str += f" = {default_value}"
            args.append(arg_str)

        if args_node.vararg:
            vararg_str = f"*{args_node.vararg.arg}"
            if args_node.vararg.annotation:
                vararg_str += f": {self._format_annotation(args_node.vararg.annotation)}"
            args.append(vararg_str)

        kw_defaults = args_node.kw_defaults or []
        for i, arg in enumerate(args_node.kwonlyargs):
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {self._format_annotation(arg.annotation)}"
            if i < len(kw_defaults) and kw_defaults[i] is not None:
                default_value = self._format_constant(kw_defaults[i])
                if default_value is not None:
                    arg_str += f" = {default_value}"
            args.append(arg_str)

        if args_node.kwarg:
            kwarg_str = f"**{args_node.kwarg.arg}"
            if args_node.kwarg.annotation:
                kwarg_str += f": {self._format_annotation(args_node.kwarg.annotation)}"
            args.append(kwarg_str)

        result = ", ".join(args)
        if returns_node:
            result += f" -> {self._format_annotation(returns_node)}"
        return result

    def _format_annotation(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_attr_name(node)
        elif isinstance(node, ast.Subscript):
            value = self._format_annotation(node.value)
            slice_ = self._format_slice(node.slice)
            return f"{value}[{slice_}]"
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        else:
            return "?"

    def _format_slice(self, node):
        if isinstance(node, ast.Index):
            return self._format_annotation(node.value)
        elif isinstance(node, ast.Tuple):
            return ", ".join(self._format_annotation(elt) for elt in node.elts)
        else:
            return self._format_annotation(node)

    def _format_constant(self, node):
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            sign = '-' if isinstance(node.op, ast.USub) else '+'
            operand = self._format_constant(node.operand)
            return sign + operand
        elif isinstance(node, ast.List):
            return "[" + ", ".join(self._format_constant(elt) for elt in node.elts) + "]"
        elif isinstance(node, ast.Tuple):
            return "(" + ", ".join(self._format_constant(elt) for elt in node.elts) + ")"
        elif isinstance(node, ast.Dict):
            items = []
            for k, v in zip(node.keys, node.values):
                if k is not None:
                    items.append(f"{self._format_constant(k)}: {self._format_constant(v)}")
                else:
                    items.append(f"**{self._format_constant(v)}")
            return "{" + ", ".join(items) + "}"
        elif isinstance(node, ast.Name):
            return node.id
        else:
            return "?"


PARSERS = {
    "python": PythonParser,
    "py": PythonParser,
}