# aichat_search/tools/code_structure/parsing/core/parser.py

import ast
import logging
from abc import ABC, abstractmethod

from aichat_search.tools.code_structure.parsing.models.node import (
    ModuleNode, ClassNode, FunctionNode, MethodNode, CodeBlockNode
)

logger = logging.getLogger(__name__)


class CodeParser(ABC):
    @abstractmethod
    def parse(self, code: str) -> ModuleNode:
        pass


class PythonParser(CodeParser):
    def parse(self, code: str) -> ModuleNode:
        try:
            tree = ast.parse(code)
            last_line = code.count('\n') + 1
            module_node = ModuleNode(lineno_start=1, lineno_end=last_line)
            self._process_body(tree.body, module_node, is_method_body=False)
            return module_node
        except SyntaxError as e:
            logger.debug(f"Синтаксическая ошибка в блоке: {e}")
            raise
        except Exception as e:
            logger.error(f"КРИТИЧЕСКАЯ ОШИБКА В ПАРСЕРЕ: {e}", exc_info=True)
            raise

    def _process_body(self, body, parent_node, is_method_body=False):
        i = 0
        n = len(body)
        while i < n:
            node = body[i]

            if isinstance(node, ast.ClassDef):
                bases = ", ".join(self._format_base(b) for b in node.bases)
                class_node = ClassNode(node.name, bases, node.lineno, node.end_lineno)
                self._process_body(node.body, class_node, is_method_body=False)
                parent_node.add_child(class_node)
                i += 1

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args_str = self._format_args(node.args, node.returns)
                if isinstance(parent_node, ClassNode):
                    func_node = MethodNode(node.name, args_str, node.lineno, node.end_lineno)
                else:
                    func_node = FunctionNode(node.name, args_str, node.lineno, node.end_lineno)
                self._process_body(node.body, func_node, is_method_body=True)
                parent_node.add_child(func_node)
                i += 1

            else:
                if not is_method_body:
                    start = i
                    while i < n and not isinstance(body[i], (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                        i += 1
                    if i > start:
                        first_node = body[start]
                        last_node = body[i-1]
                        end_line = last_node.end_lineno if hasattr(last_node, 'end_lineno') else last_node.lineno
                        line_range = f"строки {first_node.lineno}-{end_line}"
                        block_node = CodeBlockNode("Блок кода", line_range, first_node.lineno, end_line)
                        parent_node.add_child(block_node)
                else:
                    i += 1
        return

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


# Реестр доступных парсеров
PARSERS = {
    "python": PythonParser,
    "py": PythonParser,
}