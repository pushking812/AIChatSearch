# aichat_search/tools/code_structure/parser.py

import ast
from abc import ABC, abstractmethod
from .model import ModuleNode, ClassNode, FunctionNode, MethodNode, CodeBlockNode


class CodeParser(ABC):
    """Абстрактный базовый класс для парсеров кода."""

    @abstractmethod
    def parse(self, code: str) -> ModuleNode:
        """Принимает строку кода, возвращает корневой узел модуля."""
        pass


class PythonParser(CodeParser):
    """Парсер для Python с использованием ast."""

    def parse(self, code: str) -> ModuleNode:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Синтаксическая ошибка: {e}")

        module_node = ModuleNode()
        self._process_body(tree.body, module_node, is_class_body=False)
        return module_node

    def _process_body(self, body, parent_node, is_class_body=False):
        """Обрабатывает список элементов AST и добавляет узлы к parent_node."""
        i = 0
        n = len(body)
        while i < n:
            node = body[i]

            # Определения классов
            if isinstance(node, ast.ClassDef):
                bases = ", ".join(self._format_base(b) for b in node.bases)
                class_node = ClassNode(node.name, bases)
                self._process_body(node.body, class_node, is_class_body=True)
                parent_node.add_child(class_node)
                i += 1

            # Определения функций/методов
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args_str = self._format_args(node.args, node.returns)
                if is_class_body:
                    func_node = MethodNode(node.name, args_str)
                else:
                    func_node = FunctionNode(node.name, args_str)
                self._process_body(node.body, func_node, is_class_body=False)
                parent_node.add_child(func_node)
                i += 1

            else:
                # Группируем несколько подряд идущих не-определений
                start = i
                while i < n and not isinstance(body[i], (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    i += 1
                if i > start:
                    first_node = body[start]
                    last_node = body[i-1]
                    line_range = f"строки {first_node.lineno}-{last_node.lineno}"
                    block_node = CodeBlockNode("Блок кода", line_range)
                    parent_node.add_child(block_node)

        return

    def _format_base(self, base_node):
        """Форматирует базовый класс в строку с учётом возможных атрибутов (module.Class)."""
        if isinstance(base_node, ast.Name):
            return base_node.id
        elif isinstance(base_node, ast.Attribute):
            return self._get_attr_name(base_node)
        else:
            return "?"

    def _get_attr_name(self, attr_node):
        """Рекурсивно собирает имя атрибута (например, module.Class)."""
        if isinstance(attr_node, ast.Name):
            return attr_node.id
        elif isinstance(attr_node, ast.Attribute):
            return self._get_attr_name(attr_node.value) + "." + attr_node.attr
        else:
            return "?"

    def _format_args(self, args_node, returns_node=None):
        """Форматирует аргументы функции в строку, включая аннотации и значения по умолчанию.
        Также добавляет аннотацию возвращаемого значения, если есть.
        """
        args = []

        # Позиционные аргументы
        defaults = args_node.defaults
        n_pos_args = len(args_node.args)
        n_defaults = len(defaults)

        for i, arg in enumerate(args_node.args):
            arg_str = arg.arg
            # Аннотация
            if arg.annotation:
                arg_str += f": {self._format_annotation(arg.annotation)}"
            # Значение по умолчанию (если есть)
            default_offset = n_pos_args - n_defaults
            if i >= default_offset:
                default_index = i - default_offset
                if default_index < n_defaults:
                    default_value = self._format_constant(defaults[default_index])
                    if default_value is not None:
                        arg_str += f" = {default_value}"
            args.append(arg_str)

        # *args
        if args_node.vararg:
            vararg_str = f"*{args_node.vararg.arg}"
            if args_node.vararg.annotation:
                vararg_str += f": {self._format_annotation(args_node.vararg.annotation)}"
            args.append(vararg_str)

        # keyword-only arguments
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

        # **kwargs
        if args_node.kwarg:
            kwarg_str = f"**{args_node.kwarg.arg}"
            if args_node.kwarg.annotation:
                kwarg_str += f": {self._format_annotation(args_node.kwarg.annotation)}"
            args.append(kwarg_str)

        result = ", ".join(args)
        # Добавляем аннотацию возврата
        if returns_node:
            result += f" -> {self._format_annotation(returns_node)}"
        return result

    def _format_annotation(self, node):
        """Преобразует узел аннотации в строку (например, 'int', 'list[str]')."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_attr_name(node)
        elif isinstance(node, ast.Subscript):
            # Для типов вроде list[int]
            value = self._format_annotation(node.value)
            slice_ = self._format_slice(node.slice)
            return f"{value}[{slice_}]"
        elif isinstance(node, ast.Constant):
            # Для Literal или других констант (редко)
            return repr(node.value)
        else:
            return "?"

    def _format_slice(self, node):
        """Форматирует срез для аннотаций (например, 'int' в list[int])."""
        if isinstance(node, ast.Index):
            # Для Python < 3.9
            return self._format_annotation(node.value)
        elif isinstance(node, ast.Tuple):
            return ", ".join(self._format_annotation(elt) for elt in node.elts)
        else:
            # В Python 3.9+ slice может быть просто узлом
            return self._format_annotation(node)

    def _format_constant(self, node):
        """Преобразует константу (число, строку и т.д.) в строковое представление."""
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            # Обработка отрицательных чисел
            sign = '-' if isinstance(node.op, ast.USub) else '+'
            operand = self._format_constant(node.operand)
            return sign + operand
        elif isinstance(node, ast.List):
            # Для списков (редко, но бывает)
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
            # Например, имя переменной (редко)
            return node.id
        else:
            return "?"