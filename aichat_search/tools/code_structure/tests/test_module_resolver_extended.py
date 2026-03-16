# aichat_search/tools/code_structure/tests/test_module_resolver_extended.py

import unittest
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from aichat_search.tools.code_structure.core.module_identifier import ModuleIdentifier
from aichat_search.tools.code_structure.core.module_resolver import ModuleResolver
from aichat_search.tools.code_structure.models.node import (
    ModuleNode, ClassNode, FunctionNode, MethodNode
)
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.services.block_parser import MessageBlock


class TestModuleResolverExtended(unittest.TestCase):
    """Расширенные тесты для ModuleResolver, покрывающие множество сценариев."""

    def setUp(self):
        self.identifier = ModuleIdentifier()
        self._setup_known_modules()
        self.resolver = ModuleResolver(self.identifier)

    def _setup_known_modules(self):
        """Создаёт набор модулей для тестирования разнообразных случаев."""
        # Модуль calculator.py – арифметические операции
        calc = ModuleNode()
        calc_class = ClassNode("Calculator", "")
        calc.add_child(calc_class)
        calc_class.add_child(MethodNode("add", "self, a, b"))
        calc_class.add_child(MethodNode("subtract", "self, a, b"))
        calc_class.add_child(MethodNode("multiply", "self, a, b"))
        calc_class.add_child(MethodNode("divide", "self, a, b"))
        calc_class.add_child(MethodNode("calculate", "self, x, y"))  # добавлено для теста функции с self
        # Отдельная функция
        calc.add_child(FunctionNode("pi", ""))
        self.identifier.collect_from_tree(calc, "calculator")

        # Модуль geometry.py – геометрические фигуры
        geom = ModuleNode()
        circle = ClassNode("Circle", "")
        geom.add_child(circle)
        circle.add_child(MethodNode("area", "self"))
        circle.add_child(MethodNode("perimeter", "self"))
        square = ClassNode("Square", "")
        geom.add_child(square)
        square.add_child(MethodNode("area", "self"))
        square.add_child(MethodNode("perimeter", "self"))
        # Статический метод
        geom_static = MethodNode("distance", "x1, y1, x2, y2")
        geom_static.node_type = "method"  # статический, без self
        square.add_child(geom_static)
        # Функция для вычисления расстояния
        geom.add_child(FunctionNode("distance", "x1, y1, x2, y2"))
        self.identifier.collect_from_tree(geom, "geometry")

        # Модуль utils.py – утилиты
        utils = ModuleNode()
        utils.add_child(FunctionNode("sort", "items"))
        utils.add_child(FunctionNode("filter", "items, predicate"))
        utils.add_child(FunctionNode("map", "items, func"))
        self.identifier.collect_from_tree(utils, "utils")

        # Модуль strings.py – работа со строками
        strings = ModuleNode()
        strings.add_child(FunctionNode("capitalize", "s"))
        strings.add_child(FunctionNode("reverse", "s"))
        strings.add_child(FunctionNode("is_palindrome", "s"))
        self.identifier.collect_from_tree(strings, "strings")

        # Модуль db.py – работа с базой данных
        db = ModuleNode()
        db_class = ClassNode("Database", "")
        db.add_child(db_class)
        db_class.add_child(MethodNode("connect", "self, url"))
        db_class.add_child(MethodNode("query", "self, sql"))
        db_class.add_child(MethodNode("close", "self"))
        self.identifier.collect_from_tree(db, "db")

        # Модуль logging.py – логирование
        log = ModuleNode()
        log.add_child(FunctionNode("info", "msg"))
        log.add_child(FunctionNode("error", "msg"))
        log.add_child(FunctionNode("debug", "msg"))
        self.identifier.collect_from_tree(log, "logging")

    def _create_block_info(self, content: str, tree: ModuleNode, block_id: str, index: int) -> MessageBlockInfo:
        block = MessageBlock(index, content, "python", "response")
        block_info = MessageBlockInfo(block, "python", content, block_id, index)
        if tree:
            block_info.set_tree(tree)
        return block_info

    def assertResolved(self, result, expected_module):
        success, module = result
        self.assertTrue(success, f"Не разрешился, ожидался {expected_module}")
        self.assertEqual(module, expected_module)

    def assertNotResolved(self, result):
        success, module = result
        self.assertFalse(success, f"Разрешился как {module}, ожидалась неопределённость")

    # ------------------------------------------------------------
    # ТЕСТЫ МЕТОДОВ
    # ------------------------------------------------------------

    def test_ordinary_method_without_class(self):
        """Обычный метод без указания класса (узел method)."""
        content = "def add(self, a, b): return a + b"
        tree = ModuleNode()
        tree.add_child(MethodNode("add", "self, a, b"))
        block = self._create_block_info(content, tree, "ordinary_method", 1)
        self.assertResolved(self.resolver.resolve_block(block), "calculator")

    def test_method_inside_class(self):
        """Метод, определённый внутри класса."""
        content = """
class Calculator:
    def add(self, a, b): return a + b
"""
        tree = ModuleNode()
        cls = ClassNode("Calculator", "")
        cls.add_child(MethodNode("add", "self, a, b"))
        tree.add_child(cls)
        block = self._create_block_info(content, tree, "method_in_class", 2)
        self.assertResolved(self.resolver.resolve_block(block), "calculator")

    def test_classmethod_with_cls(self):
        """Метод класса с параметром cls."""
        content = "def create(cls, a, b): return cls(a, b)"
        tree = ModuleNode()
        tree.add_child(MethodNode("create", "cls, a, b"))
        block = self._create_block_info(content, tree, "classmethod", 3)
        # В calculator нет метода create – неопределён
        self.assertNotResolved(self.resolver.resolve_block(block))

    def test_classmethod_with_cls_and_self_call(self):
        """Метод класса, использующий cls внутри."""
        content = """
def from_string(cls, s):
    parts = s.split(',')
    return cls(*parts)
"""
        tree = ModuleNode()
        tree.add_child(MethodNode("from_string", "cls, s"))
        block = self._create_block_info(content, tree, "classmethod_call", 4)
        self.assertNotResolved(self.resolver.resolve_block(block))  # нет такого метода

    def test_static_method_without_self(self):
        """Статический метод без self (в дереве method)."""
        content = "@staticmethod\ndef distance(x1, y1, x2, y2): return ((x2-x1)**2 + (y2-y1)**2)**0.5"
        tree = ModuleNode()
        tree.add_child(MethodNode("distance", "x1, y1, x2, y2"))
        block = self._create_block_info(content, tree, "static_method", 5)
        # Статический метод есть в geometry (класс Square) и как функция
        self.assertResolved(self.resolver.resolve_block(block), "geometry")

    def test_abstract_method(self):
        """Абстрактный метод (сигнатура без реализации)."""
        content = "def area(self): pass"
        tree = ModuleNode()
        tree.add_child(MethodNode("area", "self"))
        block = self._create_block_info(content, tree, "abstract_method", 6)
        # area есть в geometry (Circle и Square) – модуль определён
        self.assertResolved(self.resolver.resolve_block(block), "geometry")

    def test_method_ambiguous_different_classes(self):
        """Метод с одинаковым именем и сигнатурой в двух классах одного модуля."""
        content = "def perimeter(self): return 2*3.14*self.r"
        tree = ModuleNode()
        tree.add_child(MethodNode("perimeter", "self"))
        block = self._create_block_info(content, tree, "ambiguous_method_same_module", 7)
        # perimeter есть и в Circle, и в Square (geometry) – но оба в одном модуле, значит модуль определён
        self.assertResolved(self.resolver.resolve_block(block), "geometry")

    def test_method_with_different_signature(self):
        """Метод с тем же именем, но другой сигнатурой (другие параметры)."""
        content = "def area(self, precision): return round(3.14*self.r**2, precision)"
        tree = ModuleNode()
        tree.add_child(MethodNode("area", "self, precision"))
        block = self._create_block_info(content, tree, "method_diff_sig", 8)
        # В geometry area без параметров, сигнатура не совпадает – не должно находиться
        self.assertNotResolved(self.resolver.resolve_block(block))

    # ------------------------------------------------------------
    # ТЕСТЫ ФУНКЦИЙ
    # ------------------------------------------------------------

    def test_simple_function(self):
        """Обычная функция верхнего уровня."""
        content = "def sort(items): return sorted(items)"
        tree = ModuleNode()
        tree.add_child(FunctionNode("sort", "items"))
        block = self._create_block_info(content, tree, "simple_func", 10)
        self.assertResolved(self.resolver.resolve_block(block), "utils")

    def test_function_with_self_call(self):
        """Функция, внутри которой используется self (должна определяться как метод)."""
        content = """
def calculate(self, x, y):
    return self.data[x] + y
"""
        tree = ModuleNode()
        tree.add_child(FunctionNode("calculate", "self, x, y"))
        block = self._create_block_info(content, tree, "func_with_self", 11)
        # Должен найти calculator (метод calculate)
        self.assertResolved(self.resolver.resolve_block(block), "calculator")

    def test_function_ambiguous(self):
        """Функция, присутствующая в нескольких модулях."""
        content = "def info(msg): print(msg)"
        tree = ModuleNode()
        tree.add_child(FunctionNode("info", "msg"))
        block = self._create_block_info(content, tree, "func_ambiguous", 12)
        # info есть в logging и, допустим, больше нигде – пока только logging
        self.assertResolved(self.resolver.resolve_block(block), "logging")

    # ------------------------------------------------------------
    # ТЕСТЫ КЛАССОВ
    # ------------------------------------------------------------

    def test_class_exact_match(self):
        """Класс, точно совпадающий с известным."""
        content = "class Calculator: pass"
        tree = ModuleNode()
        tree.add_child(ClassNode("Calculator", ""))
        block = self._create_block_info(content, tree, "class_exact", 20)
        self.assertResolved(self.resolver.resolve_block(block), "calculator")

    def test_class_partial_match(self):
        """Класс с похожим именем (должен быть неопределён – частичное совпадение не ищем)."""
        content = "class AdvancedCalculator: pass"
        tree = ModuleNode()
        tree.add_child(ClassNode("AdvancedCalculator", ""))
        block = self._create_block_info(content, tree, "class_partial", 21)
        # Частичное совпадение не ищем, поэтому неопределён
        self.assertNotResolved(self.resolver.resolve_block(block))

    def test_class_with_methods(self):
        """Класс с методами, совпадающими с известным модулем."""
        content = """
class Calculator:
    def add(self, a, b): pass
    def subtract(self, a, b): pass
"""
        tree = ModuleNode()
        cls = ClassNode("Calculator", "")
        cls.add_child(MethodNode("add", "self, a, b"))
        cls.add_child(MethodNode("subtract", "self, a, b"))
        tree.add_child(cls)
        block = self._create_block_info(content, tree, "class_with_methods", 22)
        self.assertResolved(self.resolver.resolve_block(block), "calculator")

    # ------------------------------------------------------------
    # ТЕСТЫ КОНТЕКСТА ВЫЗОВОВ
    # ------------------------------------------------------------

    def test_method_calling_other_methods(self):
        """Метод, вызывающий другие методы, которые есть только в одном модуле."""
        content = """
def process(self, data):
    result = self.validate(data)
    return self._transform(result)
"""
        tree = ModuleNode()
        tree.add_child(MethodNode("process", "self, data"))
        tree.add_child(MethodNode("validate", "self, data"))
        tree.add_child(MethodNode("_transform", "self, result"))
        block = self._create_block_info(content, tree, "method_with_calls", 30)
        # Такого метода process нет нигде, но validate есть в geometry (Circle.area нет)
        # process нет нигде → неопределён
        self.assertNotResolved(self.resolver.resolve_block(block))

    def test_method_calls_that_match_one_module(self):
        """Метод, вызывающий методы, которые есть только в одном модуле."""
        content = """
def query(self, sql):
    self.connect()
    result = self._execute(sql)
    self.close()
"""
        tree = ModuleNode()
        tree.add_child(MethodNode("query", "self, sql"))
        tree.add_child(MethodNode("connect", "self"))
        tree.add_child(MethodNode("_execute", "self, sql"))
        tree.add_child(MethodNode("close", "self"))
        block = self._create_block_info(content, tree, "method_calls_match", 31)
        # В db есть connect, query, close, но нет _execute – однако модуль db определён по методу query
        self.assertResolved(self.resolver.resolve_block(block), "db")

    # ------------------------------------------------------------
    # ТЕСТЫ ИМПОРТОВ
    # ------------------------------------------------------------

    def test_function_with_import_hint(self):
        """Функция с импортом из модуля."""
        content = """
from utils import something

def my_sort(items):
    return sorted(items)
"""
        tree = ModuleNode()
        tree.add_child(FunctionNode("my_sort", "items"))
        block = self._create_block_info(content, tree, "import_hint", 40)
        # В utils есть sort, но my_sort нет – неопределён
        self.assertNotResolved(self.resolver.resolve_block(block))

    def test_method_with_import(self):
        """Метод с импортом из модуля."""
        content = """
from geometry import Circle

def area(self):
    return 3.14 * self.r**2
"""
        tree = ModuleNode()
        tree.add_child(MethodNode("area", "self"))
        block = self._create_block_info(content, tree, "method_import", 41)
        # area есть только в geometry, импорт подтверждает – модуль определён
        self.assertResolved(self.resolver.resolve_block(block), "geometry")

    # ------------------------------------------------------------
    # ТЕСТЫ ВЛОЖЕННЫХ СТРУКТУР
    # ------------------------------------------------------------

    def test_nested_function(self):
        """Функция, внутри которой определена другая функция."""
        content = """
def outer():
    def inner():
        return 42
    return inner()
"""
        tree = ModuleNode()
        outer = FunctionNode("outer", "")
        inner = FunctionNode("inner", "")
        outer.add_child(inner)
        tree.add_child(outer)
        block = self._create_block_info(content, tree, "nested_func", 50)
        # Вложенные функции не должны определяться
        self.assertNotResolved(self.resolver.resolve_block(block))

    def test_nested_class(self):
        """Класс, внутри которого определён другой класс."""
        content = """
class Outer:
    class Inner:
        def method(self): pass
"""
        tree = ModuleNode()
        outer = ClassNode("Outer", "")
        inner = ClassNode("Inner", "")
        inner.add_child(MethodNode("method", "self"))
        outer.add_child(inner)
        tree.add_child(outer)
        block = self._create_block_info(content, tree, "nested_class", 51)
        # Нет совпадений с известными классами
        self.assertNotResolved(self.resolver.resolve_block(block))

    # ------------------------------------------------------------
    # ТЕСТЫ ГРАНИЧНЫХ СЛУЧАЕВ
    # ------------------------------------------------------------

    def test_empty_block(self):
        """Пустой блок."""
        content = ""
        tree = ModuleNode()
        block = self._create_block_info(content, tree, "empty", 60)
        self.assertNotResolved(self.resolver.resolve_block(block))

    def test_syntax_error_block(self):
        """Блок с синтаксической ошибкой."""
        content = "def foo(:"
        block = MessageBlock(61, content, "python", "response")
        block_info = MessageBlockInfo(block, "python", content, "syntax_error", 61)
        block_info.set_error(SyntaxError("invalid syntax"))
        self.assertNotResolved(self.resolver.resolve_block(block_info))

    def test_module_without_matches(self):
        """Без совпадений (совсем чужой код)."""
        content = "def unknown(): pass"
        tree = ModuleNode()
        tree.add_child(FunctionNode("unknown", ""))
        block = self._create_block_info(content, tree, "unknown", 62)
        self.assertNotResolved(self.resolver.resolve_block(block))

    def test_method_with_self_but_not_in_module(self):
        """Метод с self, которого нет ни в одном модуле."""
        content = "def foo(self): pass"
        tree = ModuleNode()
        tree.add_child(MethodNode("foo", "self"))
        block = self._create_block_info(content, tree, "foo_method", 63)
        self.assertNotResolved(self.resolver.resolve_block(block))


def run_extended_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestModuleResolverExtended)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == '__main__':
    run_extended_tests()