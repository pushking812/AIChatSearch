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
                bases = ", ".join(self._get_base_name(b) for b in node.bases)
                class_node = ClassNode(node.name, bases)
                # Обрабатываем тело класса (внутри него is_class_body=True)
                self._process_body(node.body, class_node, is_class_body=True)
                parent_node.add_child(class_node)
                i += 1

            # Определения функций/методов
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = self._format_args(node.args)
                if is_class_body:
                    func_node = MethodNode(node.name, args)
                else:
                    func_node = FunctionNode(node.name, args)
                # Обрабатываем тело функции (внутри него is_class_body=False,
                # потому что вложенные функции не являются методами класса)
                self._process_body(node.body, func_node, is_class_body=False)
                parent_node.add_child(func_node)
                i += 1

            else:
                # Группируем несколько подряд идущих не-определений
                start = i
                while i < n and not isinstance(body[i], (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    i += 1
                if i > start:
                    # Создаём узел "Блок кода" для группы инструкций
                    first_node = body[start]
                    last_node = body[i-1]
                    line_range = f"строки {first_node.lineno}-{last_node.lineno}"
                    block_node = CodeBlockNode("Блок кода", line_range)
                    parent_node.add_child(block_node)

        return

    def _get_base_name(self, base_node):
        """Извлекает имя базового класса из узла ast."""
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

    def _format_args(self, args_node):
        """Форматирует аргументы функции в строку."""
        args = []
        # Позиционные аргументы
        for arg in args_node.args:
            args.append(arg.arg)
        # *args
        if args_node.vararg:
            args.append(f"*{args_node.vararg.arg}")
        # keyword-only args
        for arg in args_node.kwonlyargs:
            args.append(arg.arg)
        # **kwargs
        if args_node.kwarg:
            args.append(f"**{args_node.kwarg.arg}")
        return ", ".join(args)