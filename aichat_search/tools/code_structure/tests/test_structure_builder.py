# aichat_search/tools/code_structure/tests/test_structure_builder.py
"""Тесты для StructureBuilder - фиксация текущего поведения"""

import unittest
import logging
import sys
import os
from unittest.mock import Mock, patch

# Добавляем путь к проекту для импортов
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from aichat_search.tools.code_structure.core.structure_builder import StructureBuilder
from aichat_search.tools.code_structure.models.node import (
    ClassNode, FunctionNode, MethodNode, CodeBlockNode
)
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.models.containers import (
    ModuleContainer, ClassContainer, FunctionContainer, 
    MethodContainer, CodeBlockContainer
)

# Настройка логирования для тестов
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestStructureBuilder(unittest.TestCase):
    """Тесты для фиксации текущего поведения StructureBuilder"""
    
    @classmethod
    def setUpClass(cls):
        """Выполняется один раз перед всеми тестами"""
        logger.info("=" * 60)
        logger.info("НАЧАЛО ТЕСТИРОВАНИЯ StructureBuilder")
        logger.info("=" * 60)
    
    def setUp(self):
        """Подготовка перед каждым тестом"""
        self.builder = StructureBuilder()
        self.test_counter = 0
        
        # Создаем мок для блока, так как не знаем точной сигнатуры MessageBlockInfo
        self.block1 = self._create_test_block(
            block_id="block1",
            global_index=1,
            content="class Test:\n    def method1(self):\n        pass"
        )
        
        self.block2 = self._create_test_block(
            block_id="block2",
            global_index=2,
            content="def func1():\n    pass"
        )
        
        self.block3 = self._create_test_block(
            block_id="block3",
            global_index=3,
            content="class Test:\n    def method2(self):\n        return 42"
        )
        
        self.block4 = self._create_test_block(
            block_id="block4",
            global_index=4,
            content="def method_with_self(self, x):\n    return x * 2"
        )
    
    def _create_test_block(self, block_id: str, global_index: int, content: str) -> MessageBlockInfo:
        """Создает тестовый блок с минимально необходимыми полями"""
        # Создаем мок объект с нужными атрибутами
        block = Mock(spec=MessageBlockInfo)
        block.block_id = block_id
        block.global_index = global_index
        block.content = content
        block.language = "python"
        block.syntax_error = None
        block.tree = None
        block.module_hint = None
        block.metadata = {}
        return block
    
    def _create_class_node(self, name: str, methods: list = None) -> ClassNode:
        """Создает тестовый узел класса"""
        node = ClassNode(name)
        node.lineno_start = 1
        node.lineno_end = 5
        node.node_type = "class"
        
        if methods:
            for i, method_name in enumerate(methods):
                method = self._create_method_node(method_name)
                node.add_child(method)
        return node
    
    def _create_function_node(self, name: str, has_self: bool = False) -> FunctionNode:
        """Создает тестовый узел функции"""
        node = FunctionNode(name)
        node.lineno_start = 1
        node.lineno_end = 3
        node.node_type = "function"
        
        # Для тестирования сигнатуры добавим параметры
        if has_self:
            node.parameters = ['self', 'x']
        else:
            node.parameters = ['x']
        
        # Добавляем строку сигнатуры для extract_function_signature
        if has_self:
            node.signature = f"def {name}(self, x)"
        else:
            node.signature = f"def {name}(x)"
        
        return node
    
    def _create_method_node(self, name: str, class_name: str = "Test") -> MethodNode:
        """Создает тестовый узел метода"""
        node = MethodNode(name)
        node.lineno_start = 2
        node.lineno_end = 4
        node.node_type = "method"
        node.parameters = ['self', 'x']
        node.signature = f"def {name}(self, x)"
        # Указываем родительский класс
        node.parent_class = class_name
        return node
    
    def _create_code_block_node(self, name: str = "code_block") -> CodeBlockNode:
        """Создает тестовый узел блока кода"""
        node = CodeBlockNode(name)
        node.lineno_start = 1
        node.lineno_end = 5
        node.node_type = "code_block"
        node.content = "x = 42\ny = x * 2\nprint(y)"
        return node
    
    @patch('aichat_search.tools.code_structure.core.node_processor.extract_function_signature')
    def test_1_initial_build_with_class(self, mock_extract):
        """Тест 1: Создание модуля с классом и методами"""
        self.test_counter += 1
        logger.info(f"\n--- Тест 1.{self.test_counter}: build_initial_structure с классом ---")
        
        # Настройка мока
        mock_extract.return_value = (True, "def method1(self)")
        
        # Подготовка
        block = self.block1
        class_node = self._create_class_node("Test", ["method1"])
        block.tree = class_node
        
        # Действие
        module_container = self.builder.build_initial_structure("test_module", block)
        
        # Проверки
        self.assertIsNotNone(module_container)
        self.assertEqual(module_container.name, "test_module")
        self.assertEqual(len(module_container.children), 1)
        
        class_container = module_container.children[0]
        self.assertIsInstance(class_container, ClassContainer)
        self.assertEqual(class_container.name, "Test")
        self.assertEqual(len(class_container.children), 1)
        
        method_container = class_container.children[0]
        self.assertIsInstance(method_container, MethodContainer)
        self.assertEqual(method_container.name, "method1")
        self.assertEqual(len(method_container.versions), 1)
        
        # Логируем результат
        logger.info("✓ Создан модуль с классом Test и методом method1")
        logger.info(f"  - Container types: {[type(c).__name__ for c in module_container.children]}")
        
        # Сохраняем для отчета
        self._test1_result = {
            'module_name': module_container.name,
            'class_name': class_container.name,
            'method_name': method_container.name,
            'versions_count': len(method_container.versions)
        }
    
    @patch('aichat_search.tools.code_structure.core.node_processor.extract_function_signature')
    def test_2_merge_function_into_module(self, mock_extract):
        """Тест 2: Слияние функции в модуль"""
        self.test_counter += 1
        logger.info(f"\n--- Тест 2.{self.test_counter}: merge_node_into_container с функцией ---")
        
        # Настройка мока
        mock_extract.return_value = (False, "def func1(x)")
        
        # Подготовка
        module_container = ModuleContainer("test_module")
        function_node = self._create_function_node("func1")
        block = self.block2
        block.tree = function_node
        
        # Действие
        self.builder.merge_node_into_container(function_node, module_container, block)
        
        # Проверки
        self.assertEqual(len(module_container.children), 1)
        func_container = module_container.children[0]
        self.assertIsInstance(func_container, FunctionContainer)
        self.assertEqual(func_container.name, "func1")
        self.assertEqual(len(func_container.versions), 1)
        
        logger.info("✓ Функция func1 добавлена в модуль")
        logger.info(f"  - Container type: {type(func_container).__name__}")
        
        self._test2_result = {
            'function_name': func_container.name,
            'versions_count': len(func_container.versions)
        }
    
    @patch('aichat_search.tools.code_structure.core.node_processor.extract_function_signature')
    def test_3_merge_method_into_existing_class(self, mock_extract):
        """Тест 3: Слияние метода в существующий класс"""
        self.test_counter += 1
        logger.info(f"\n--- Тест 3.{self.test_counter}: слияние метода в существующий класс ---")
        
        # Настройка мока
        mock_extract.return_value = (True, "def method2(self)")
        
        # Подготовка - сначала создаем класс с методом
        block1 = self.block1
        class_node1 = self._create_class_node("Test", ["method1"])
        block1.tree = class_node1
        
        module_container = self.builder.build_initial_structure("test_module", block1)
        logger.info("  Создан начальный модуль с классом Test и method1")
        
        # Теперь сливаем второй блок с новым методом
        block3 = self.block3
        class_node2 = self._create_class_node("Test", ["method2"])
        block3.tree = class_node2
        
        # Действие
        self.builder.merge_node_into_container(class_node2, module_container, block3)
        
        # Проверки
        self.assertEqual(len(module_container.children), 1)
        class_container = module_container.children[0]
        self.assertEqual(class_container.name, "Test")
        self.assertEqual(len(class_container.children), 2)  # Должно быть два метода
        
        # Проверяем, что оба метода существуют
        method_names = [c.name for c in class_container.children]
        self.assertIn("method1", method_names)
        self.assertIn("method2", method_names)
        
        logger.info("✓ В класс Test добавлен метод method2")
        logger.info(f"  - Все методы: {method_names}")
        logger.info(f"  - Количество методов: {len(class_container.children)}")
        
        self._test3_result = {
            'class_name': class_container.name,
            'methods_count': len(class_container.children),
            'methods': method_names
        }
    
    @patch('aichat_search.tools.code_structure.core.node_processor.extract_function_signature')
    def test_4_function_with_self_attached_to_class(self, mock_extract):
        """Тест 4: Функция с self не прикрепляется к классу, если в классе нет метода с таким именем"""
        self.test_counter += 1
        logger.info(f"\n--- Тест 4.{self.test_counter}: функция с self не прикрепляется к пустому классу ---")
        
        # Настройка мока: для method1 возвращаем has_self=True
        def extract_side_effect(node):
            if hasattr(node, 'name') and node.name == "method1":
                logger.info("  ✓ extract_function_signature для method1 возвращает has_self=True")
                return (True, "def method1(self, x)")
            return (False, "")
        
        mock_extract.side_effect = extract_side_effect
        
        # Подготовка
        module_container = ModuleContainer("test_module")
        
        # Создаём пустой класс
        class_node = self._create_class_node("Test", [])
        block1 = self.block1
        block1.tree = class_node
        self.builder.merge_node_into_container(class_node, module_container, block1)
        logger.info("  Создан класс Test без методов")
        
        # Добавляем функцию с self
        func_node = self._create_function_node("method1", has_self=True)
        block4 = self.block4
        block4.tree = func_node
        self.builder.merge_node_into_container(func_node, module_container, block4)
        
        # Проверки
        logger.info(f"  После слияния: {len(module_container.children)} контейнера")
        for child in module_container.children:
            logger.info(f"    {type(child).__name__}: {child.name}")
        
        # Должно быть 2 контейнера: класс и функция
        self.assertEqual(len(module_container.children), 2,
                         f"Должно быть 2 контейнера (класс и функция), получено {len(module_container.children)}")
        
        # Находим класс и функцию
        class_container = next((c for c in module_container.children if isinstance(c, ClassContainer)), None)
        func_container = next((c for c in module_container.children if isinstance(c, FunctionContainer)), None)
        
        self.assertIsNotNone(class_container, "Класс должен существовать")
        self.assertIsNotNone(func_container, "Функция должна существовать")
        
        self.assertEqual(class_container.name, "Test")
        self.assertEqual(len(class_container.children), 0, "В классе не должно быть методов")
        
        self.assertEqual(func_container.name, "method1")
        self.assertEqual(len(func_container.versions), 1, "У функции должна быть одна версия")
        
        logger.info("✓ Функция с self осталась отдельной функцией (как и задумано)")
        
        self._test4_result = {
            'class_name': class_container.name,
            'function_name': func_container.name,
            'class_methods_count': len(class_container.children)
        }
        
    @patch('aichat_search.tools.code_structure.core.node_processor.extract_function_signature')
    def test_5_function_with_self_without_class(self, mock_extract):
        """Тест 5: Функция с self без существующего класса создается как функция"""
        self.test_counter += 1
        logger.info(f"\n--- Тест 5.{self.test_counter}: функция с self без класса ---")
        
        # Настройка мока - для функции method1 возвращаем has_self=True
        def extract_side_effect(node):
            if hasattr(node, 'name') and node.name == "method1":
                logger.info("  ✓ extract_function_signature для method1 возвращает has_self=True")
                return (True, "def method1(self, x)")
            return (False, "")
        
        mock_extract.side_effect = extract_side_effect
        
        # Подготовка
        module_container = ModuleContainer("test_module")
        
        # Функция с self, но класса нет
        func_node = self._create_function_node("method1", has_self=True)
        block4 = self.block4
        block4.tree = func_node
        
        # Действие
        self.builder.merge_node_into_container(func_node, module_container, block4)
        
        # Проверки
        logger.info(f"  После слияния: {len(module_container.children)} контейнеров")
        for i, child in enumerate(module_container.children):
            logger.info(f"    Контейнер {i}: {type(child).__name__} - {child.name}")
        
        self.assertEqual(len(module_container.children), 1)
        func_container = module_container.children[0]
        self.assertIsInstance(func_container, FunctionContainer)  # Должна быть функция, а не метод
        self.assertEqual(func_container.name, "method1")
        
        logger.info("✓ Функция с self без класса создана как функция")
        logger.info(f"  - Container type: {type(func_container).__name__}")
        logger.info(f"  - Function name: {func_container.name}")
        
        self._test5_result = {
            'container_type': type(func_container).__name__,
            'function_name': func_container.name
        }
    
    def test_6_code_block_handling(self):
        """Тест 6: Обработка простых блоков кода"""
        self.test_counter += 1
        logger.info(f"\n--- Тест 6.{self.test_counter}: обработка блока кода ---")
        
        # Подготовка
        module_container = ModuleContainer("test_module")
        code_node = self._create_code_block_node()
        block = self.block1
        block.tree = code_node
        
        # Действие
        self.builder.merge_node_into_container(code_node, module_container, block)
        
        # Проверки
        self.assertEqual(len(module_container.children), 1)
        code_container = module_container.children[0]
        self.assertIsInstance(code_container, CodeBlockContainer)
        self.assertEqual(len(code_container.versions), 1)
        
        logger.info("✓ Блок кода добавлен в модуль")
        logger.info(f"  - Container type: {type(code_container).__name__}")
        logger.info(f"  - Versions count: {len(code_container.versions)}")
        
        self._test6_result = {
            'container_type': type(code_container).__name__,
            'versions_count': len(code_container.versions)
        }
    
    @patch('aichat_search.tools.code_structure.core.node_processor.extract_function_signature')
    def test_7_merge_same_method_different_blocks(self, mock_extract):
        """Тест 7: Слияние одного и того же метода из разных блоков"""
        self.test_counter += 1
        logger.info(f"\n--- Тест 7.{self.test_counter}: слияние одного метода из разных блоков ---")
        
        # Настройка мока
        def extract_side_effect(node):
            if hasattr(node, 'node_type') and node.node_type == 'method':
                return (True, getattr(node, 'signature', 'def method()'))
            return (False, "")
        
        mock_extract.side_effect = extract_side_effect
        
        # Подготовка
        module_container = ModuleContainer("test_module")
        
        # Первый блок с методом
        class_node1 = self._create_class_node("Test", ["method1"])
        block1 = self.block1
        block1.tree = class_node1
        self.builder.merge_node_into_container(class_node1, module_container, block1)
        
        # Второй блок с тем же методом
        class_node2 = self._create_class_node("Test", ["method1"])  # То же имя метода
        # Делаем содержимое немного отличающимся для проверки версионирования
        if class_node2.children:
            class_node2.children[0].signature = "def method1(self, x, y)"  # Другая сигнатура
        
        block3 = self.block3
        block3.tree = class_node2
        self.builder.merge_node_into_container(class_node2, module_container, block3)
        
        # Проверки
        class_container = module_container.children[0]
        method_container = class_container.children[0]
        
        logger.info(f"  - Method versions: {len(method_container.versions)}")
        if method_container.versions:
            logger.info(f"  - Sources count: {len(method_container.versions[0].sources)}")
            for i, version in enumerate(method_container.versions):
                logger.info(f"    Version {i}: signature={getattr(version.node, 'signature', 'unknown')}")
        
        self._test7_result = {
            'method_name': method_container.name,
            'versions_count': len(method_container.versions),
            'sources_count': len(method_container.versions[0].sources) if method_container.versions else 0
        }
        
        # Текущее поведение - создается новая версия
        self.assertEqual(len(method_container.versions), 2, 
                         "Должно быть 2 версии метода (разные сигнатуры)")
    
    def tearDown(self):
        """Выполняется после каждого теста"""
        logger.info(f"--- Тест {self.test_counter} завершен ---")
        if hasattr(self, f'_test{self.test_counter}_result'):
            result = getattr(self, f'_test{self.test_counter}_result')
            logger.info(f"  Результат: {result}")
    
    @classmethod
    def tearDownClass(cls):
        """Выполняется один раз после всех тестов"""
        logger.info("=" * 60)
        logger.info("ИТОГИ ТЕСТИРОВАНИЯ")
        logger.info("=" * 60)


if __name__ == '__main__':
    unittest.main(verbosity=2)