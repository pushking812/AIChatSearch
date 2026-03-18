# aichat_search/tools/code_structure/tests/test_module_resolver.py

import unittest
import sys
import os

# Добавляем корневую директорию проекта в путь
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


class TestModuleResolver(unittest.TestCase):
    
    def setUp(self):
        """Подготовка тестового окружения."""
        self.identifier = ModuleIdentifier()
        self.resolver = ModuleResolver(self.identifier)
        
        # Заполняем идентификатор известными модулями
        self._setup_known_modules()
    
    def _setup_known_modules(self):
        """Создает известные модули для тестирования."""
        
        # Модуль calculator.py
        calc_module = ModuleNode()
        
        # Класс MathCalc с методами
        math_class = ClassNode("MathCalc", "")
        calc_module.add_child(math_class)
        
        # Метод calculate
        calc_method = MethodNode("calculate", "self, x, y")
        math_class.add_child(calc_method)
        
        # Метод validate
        validate_method = MethodNode("validate", "self, value")
        math_class.add_child(validate_method)
        
        # Метод process
        process_method = MethodNode("process", "self, data")
        math_class.add_child(process_method)
        
        self.identifier.collect_from_tree(calc_module, "calculator")
        
        # Модуль utils.py
        utils_module = ModuleNode()
        
        # Функция calculate (без self)
        calc_func = FunctionNode("calculate", "x, y")
        utils_module.add_child(calc_func)
        
        # Функция validate
        validate_func = FunctionNode("validate", "value")
        utils_module.add_child(validate_func)
        
        self.identifier.collect_from_tree(utils_module, "utils")
        
        # Модуль data_processor.py
        dp_module = ModuleNode()
        
        # Класс DataProcessor
        dp_class = ClassNode("DataProcessor", "")
        dp_module.add_child(dp_class)
        
        # Метод process
        process_method = MethodNode("process", "self, data, options=None")
        dp_class.add_child(process_method)
        
        # Статический метод validate
        validate_static = MethodNode("validate", "input_data")
        dp_class.add_child(validate_static)
        
        self.identifier.collect_from_tree(dp_module, "data_processor")
    
    def _create_block_info(self, content: str, tree: ModuleNode, block_id: str, index: int = 0) -> MessageBlockInfo:
        """Создает MessageBlockInfo для тестирования."""
        # Создаем MessageBlock с правильными параметрами
        block = MessageBlock(
            index=index,
            content=content,
            language="python",
            block_type="response"
        )
        
        block_info = MessageBlockInfo(
            block=block,
            language="python",
            content=content,
            block_id=block_id,
            global_index=index
        )
        block_info.set_tree(tree)
        return block_info
    
    def assertResolved(self, result, expected_module):
        """Проверяет успешное разрешение модуля."""
        success, module = result
        self.assertTrue(success, f"Блок не разрешился, ожидался модуль {expected_module}")
        self.assertEqual(module, expected_module)
    
    def assertNotResolved(self, result):
        """Проверяет, что модуль не разрешен."""
        success, module = result
        self.assertFalse(success, f"Блок разрешился как {module}, ожидалась неопределенность")
    
    # Тест 1: Точное совпадение метода
    def test_1_exact_method_match(self):
        content = """
def calculate(self, x, y):
    return x + y
"""
        tree = ModuleNode()
        method = MethodNode("calculate", "self, x, y")
        tree.add_child(method)
        
        block_info = self._create_block_info(content, tree, "block1", 1)
        result = self.resolver.resolve_block(block_info)
        
        self.assertResolved(result, "calculator")
        print("\n✅ Тест 1 (точное совпадение метода) пройден")
    
    # Тест 2: Метод с cls
    def test_2_method_with_cls(self):
        content = """
def calculate(cls, x, y):
    return x + y
"""
        tree = ModuleNode()
        method = MethodNode("calculate", "cls, x, y")
        tree.add_child(method)
        
        block_info = self._create_block_info(content, tree, "block2", 2)
        result = self.resolver.resolve_block(block_info)
        
        self.assertResolved(result, "calculator")
        print("\n✅ Тест 2 (метод с cls) пройден")
    
    # Тест 3: Функция с self в теле
    def test_3_method_as_function(self):
        content = """
def calculate(x, y):
    self.data = x + y
    return self.data
"""
        tree = ModuleNode()
        func = FunctionNode("calculate", "x, y")
        tree.add_child(func)
        
        block_info = self._create_block_info(content, tree, "block3", 3)
        result = self.resolver.resolve_block(block_info)
        
        # Должен определить как метод из-за self в теле
        self.assertResolved(result, "calculator")
        print("\n✅ Тест 3 (функция с self) пройден")
    
    # Тест 4: Обычная функция
    def test_4_function_match(self):
        content = """
def validate(value):
    return value > 0
"""
        tree = ModuleNode()
        func = FunctionNode("validate", "value")
        tree.add_child(func)
        
        block_info = self._create_block_info(content, tree, "block4", 4)
        result = self.resolver.resolve_block(block_info)
        
        self.assertResolved(result, "utils")
        print("\n✅ Тест 4 (обычная функция) пройден")
    
    # Тест 5: Статический метод
    def test_5_static_method(self):
        content = """
@staticmethod
def validate(input_data):
    return input_data is not None
"""
        tree = ModuleNode()
        method = MethodNode("validate", "input_data")
        tree.add_child(method)
        
        block_info = self._create_block_info(content, tree, "block5", 5)
        result = self.resolver.resolve_block(block_info)
        
        self.assertResolved(result, "data_processor")
        print("\n✅ Тест 5 (статический метод) пройден")
    
    # Тест 6: Фрагмент класса
    def test_6_class_fragment(self):
        content = """
class MathCalc:
    def multiply(self, a, b):
        return a * b
"""
        tree = ModuleNode()
        class_node = ClassNode("MathCalc", "")
        method = MethodNode("multiply", "self, a, b")
        class_node.add_child(method)
        tree.add_child(class_node)
        
        block_info = self._create_block_info(content, tree, "block6", 6)
        result = self.resolver.resolve_block(block_info)
        
        self.assertResolved(result, "calculator")
        print("\n✅ Тест 6 (фрагмент класса) пройден")
    
    # Тест 7: Неоднозначный случай
    def test_7_ambiguous_case(self):
        content = """
def process(data):
    return data * 2
"""
        tree = ModuleNode()
        func = FunctionNode("process", "data")
        tree.add_child(func)
        
        block_info = self._create_block_info(content, tree, "block7", 7)
        result = self.resolver.resolve_block(block_info)
        
        self.assertNotResolved(result)
        print("\n✅ Тест 7 (неоднозначный случай) пройден")
    
    # Тест 8: С подсказкой через импорт
    def test_8_with_import_hint(self):
        content = """
from utils import something

def calculate(x, y):
    return x * y
"""
        tree = ModuleNode()
        func = FunctionNode("calculate", "x, y")
        tree.add_child(func)
        
        block_info = self._create_block_info(content, tree, "block8", 8)
        result = self.resolver.resolve_block(block_info)
        
        # Должен найти utils по импорту
        self.assertResolved(result, "utils")
        print("\n✅ Тест 8 (с импортом) пройден")
    
    # Тест 9: Частичное совпадение класса
    def test_9_partial_class_match(self):
        content = """
class AdvancedMathCalc:
    def calculate(self, x, y):
        return x ** y
"""
        tree = ModuleNode()
        class_node = ClassNode("AdvancedMathCalc", "")
        method = MethodNode("calculate", "self, x, y")
        class_node.add_child(method)
        tree.add_child(class_node)
        
        block_info = self._create_block_info(content, tree, "block9", 9)
        result = self.resolver.resolve_block(block_info)
        
        # Должен найти calculator по частичному совпадению класса
        self.assertResolved(result, "calculator")
        print("\n✅ Тест 9 (частичное совпадение класса) пройден")
    
    # Тест 10: Метод с контекстом (неоднозначный)
    def test_10_method_with_context(self):
        content = """
    def process(self, data):
        result = self.validate(data)
        return self._transform(result)
    """
        tree = ModuleNode()
        method = MethodNode("process", "self, data")
        tree.add_child(method)
        
        # Добавляем вызываемые методы в дерево
        validate = MethodNode("validate", "self, data")
        transform = MethodNode("_transform", "self, result")
        tree.add_child(validate)
        tree.add_child(transform)
        
        block_info = self._create_block_info(content, tree, "block10", 10)
        result = self.resolver.resolve_block(block_info)
        
        # Ситуация неоднозначная, ожидаем False
        self.assertNotResolved(result)
        print("\n✅ Тест 10 (метод с контекстом) пройден (неоднозначность)")


class TestModuleResolverEdgeCases(unittest.TestCase):
    """Тесты для граничных случаев."""
    
    def setUp(self):
        self.identifier = ModuleIdentifier()
        self.resolver = ModuleResolver(self.identifier)
    
    def _create_block_info(self, content: str, tree: ModuleNode, block_id: str, index: int = 0) -> MessageBlockInfo:
        """Создает MessageBlockInfo для тестирования."""
        block = MessageBlock(
            index=index,
            content=content,
            language="python",
            block_type="response"
        )
        block_info = MessageBlockInfo(
            block=block,
            language="python",
            content=content,
            block_id=block_id,
            global_index=index
        )
        if tree:
            block_info.set_tree(tree)
        return block_info
    
    def test_empty_block(self):
        """Тест: Пустой блок."""
        content = ""
        tree = ModuleNode()
        block_info = self._create_block_info(content, tree, "empty", 0)
        success, module = self.resolver.resolve_block(block_info)
        
        self.assertFalse(success)
        self.assertIsNone(module)
        print("\n✅ Тест пустого блока пройден")
    
    def test_block_with_syntax_error(self):
        """Тест: Блок с синтаксической ошибкой."""
        content = "def invalid syntax here"
        block = MessageBlock(
            index=1,
            content=content,
            language="python",
            block_type="response"
        )
        block_info = MessageBlockInfo(
            block=block,
            language="python",
            content=content,
            block_id="error_block",
            global_index=1
        )
        block_info.set_error(SyntaxError("Invalid syntax"))
        
        success, module = self.resolver.resolve_block(block_info)
        
        self.assertFalse(success)
        self.assertIsNone(module)
        print("\n✅ Тест блока с ошибкой пройден")
    
    def test_block_with_nested_functions(self):
        """Тест: Блок с вложенными функциями."""
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
        
        block_info = self._create_block_info(content, tree, "nested", 2)
        success, module = self.resolver.resolve_block(block_info)
        
        # Вложенные функции не должны определяться
        self.assertFalse(success)
        self.assertIsNone(module)
        print("\n✅ Тест с вложенными функциями пройден")


def run_tests():
    """Запускает все тесты."""
    print("=" * 60)
    print("ЗАПУСК ТЕСТОВ МОДУЛЬНОГО РЕЗОЛВЕРА")
    print("=" * 60)
    
    suite = unittest.TestSuite()
    
    # Добавляем основные тесты
    suite.addTest(TestModuleResolver('test_1_exact_method_match'))
    suite.addTest(TestModuleResolver('test_2_method_with_cls'))
    suite.addTest(TestModuleResolver('test_3_method_as_function'))
    suite.addTest(TestModuleResolver('test_4_function_match'))
    suite.addTest(TestModuleResolver('test_5_static_method'))
    suite.addTest(TestModuleResolver('test_6_class_fragment'))
    suite.addTest(TestModuleResolver('test_7_ambiguous_case'))
    suite.addTest(TestModuleResolver('test_8_with_import_hint'))
    suite.addTest(TestModuleResolver('test_9_partial_class_match'))
    suite.addTest(TestModuleResolver('test_10_method_with_context'))
    
    # Добавляем граничные случаи
    suite.addTest(TestModuleResolverEdgeCases('test_empty_block'))
    suite.addTest(TestModuleResolverEdgeCases('test_block_with_syntax_error'))
    suite.addTest(TestModuleResolverEdgeCases('test_block_with_nested_functions'))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("ИТОГИ ТЕСТИРОВАНИЯ:")
    print(f"  Запущено: {result.testsRun}")
    print(f"  Успешно: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  Ошибки: {len(result.errors)}")
    print(f"  Падения: {len(result.failures)}")
    print("=" * 60)
    
    return result


if __name__ == '__main__':
    run_tests()