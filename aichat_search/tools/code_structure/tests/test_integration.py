# aichat_search/tools/code_structure/tests/test_integration_manual.py

import unittest
import sys
import os
from typing import List, Tuple
from unittest.mock import MagicMock
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.core.project_tree_builder import ProjectTreeBuilder
from aichat_search.tools.code_structure.core.module_orchestrator import ModuleOrchestrator
from aichat_search.tools.code_structure.core.import_analyzer import extract_imports_from_block
from aichat_search.tools.code_structure.parser import PythonParser
from aichat_search.services.block_parser import MessageBlock


class TestManualIntegration(unittest.TestCase):
    """Интеграционные тесты, создающие блоки вручную."""

    def _create_block_info(self, content: str, module_hint: str = None) -> MessageBlockInfo:
        """Создаёт MessageBlockInfo с корректным MessageBlock и деревом."""
        # Создаём MessageBlock с необходимыми полями
        block = MessageBlock(index=0, content=content, language="python")
        block_info = MessageBlockInfo(
            block=block,
            language="python",
            content=content,
            block_id="test",
            global_index=0,
            module_hint=module_hint,
            metadata={}
        )
        parser = PythonParser()
        try:
            tree = parser.parse(content)
            block_info.set_tree(tree)
        except SyntaxError as e:
            block_info.set_error(e)
        return block_info

    # ---------- Тесты ProjectTreeBuilder ----------
    def test_project_tree_builder_comments(self):
        block1 = self._create_block_info("# myapp.models\nclass User:\n    pass", "myapp.models")
        block2 = self._create_block_info("# myapp.views\nclass ProfileView:\n    pass", "myapp.views")
        builder = ProjectTreeBuilder()
        project_info = builder.process_blocks([block1, block2])
        self.assertIn("myapp.models", project_info.modules)
        self.assertIn("myapp.views", project_info.modules)
        self.assertIn("User", project_info.definitions)
        self.assertIn("class", project_info.definitions["User"])
        self.assertIn("myapp.models", project_info.definitions["User"]["class"])
        self.assertIn("ProfileView", project_info.definitions)
        self.assertIn("class", project_info.definitions["ProfileView"])
        self.assertIn("myapp.views", project_info.definitions["ProfileView"]["class"])

    def test_project_tree_builder_imports(self):
        block1 = self._create_block_info("from . import utils", "myapp.sub.module")
        block2 = self._create_block_info("from ..models import User", "myapp.sub.module")
        builder = ProjectTreeBuilder()
        project_info = builder.process_blocks([block1, block2])
        self.assertIn("myapp.sub", project_info.modules)
        self.assertIn("myapp.models", project_info.modules)
        self.assertIn("User", project_info.definitions)
        self.assertIn("class", project_info.definitions["User"])
        self.assertIn("myapp.models", project_info.definitions["User"]["class"])
        self.assertIn("utils", project_info.definitions)
        self.assertIn("function", project_info.definitions["utils"])
        self.assertIn("myapp.sub", project_info.definitions["utils"]["function"])

    def test_project_tree_builder_conflict(self):
        block1 = self._create_block_info("# myapp.models\nclass User:\n    pass", "myapp.models")
        block2 = self._create_block_info("# myapp.other\nclass User:\n    pass", "myapp.other")
        builder = ProjectTreeBuilder()
        project_info = builder.process_blocks([block1, block2])
        self.assertIn("User", project_info.definitions)
        self.assertEqual(len(project_info.definitions["User"]["class"]), 2)

    def test_project_tree_builder_assign_blocks(self):
        block1 = self._create_block_info("class User:\n    pass")
        block2 = self._create_block_info("def helper():\n    return 42")
        block3 = self._create_block_info("# myapp.utils\nclass Helper:\n    pass", "myapp.utils")
        builder = ProjectTreeBuilder()
        builder.process_blocks([block1, block2, block3])
        need_dialog = builder.assign_blocks_to_modules([block1, block2, block3])
        self.assertEqual(block3.module_hint, "myapp.utils")
        self.assertIsNone(block1.module_hint)
        self.assertIsNone(block2.module_hint)
        self.assertEqual(len(need_dialog), 2)

    # ---------- Тесты ModuleOrchestrator ----------
    def test_orchestrator_methods_attach_to_class(self):
        block1 = self._create_block_info("# myapp.models\nclass User:\n    pass", "myapp.models")
        block2 = self._create_block_info("# myapp.models\n    def __init__(self):\n        pass", "myapp.models")
        orchestrator = ModuleOrchestrator()
        containers, unknown = orchestrator.process_blocks([block1, block2])
        self.assertIn("myapp.models", containers)
        module = containers["myapp.models"]
        # Находим класс User
        user_class = None
        for child in module.children:
            if child.name == "User" and child.node_type == "class":
                user_class = child
                break
        self.assertIsNotNone(user_class)
        method_names = [m.name for m in user_class.children if m.node_type == "method"]
        self.assertIn("__init__", method_names)

    def test_orchestrator_class_from_import(self):
        block1 = self._create_block_info("# myapp.models\nclass User:\n    pass", "myapp.models")
        block2 = self._create_block_info("# myapp.views\nfrom ..models import User", "myapp.views")
        orchestrator = ModuleOrchestrator()
        containers, unknown = orchestrator.process_blocks([block1, block2])
        # Проверяем, что модули созданы
        self.assertIn("myapp.models", containers)
        self.assertIn("myapp.views", containers)

    def test_orchestrator_conflict_resolution(self):
        block1 = self._create_block_info("# myapp.models\nclass User:\n    pass", "myapp.models")
        block2 = self._create_block_info("# myapp.other\nclass User:\n    pass", "myapp.other")
        block3 = self._create_block_info("from .models import User", "myapp.views")
        orchestrator = ModuleOrchestrator()
        containers, unknown = orchestrator.process_blocks([block1, block2, block3])
        # Блок с импортом не должен быть разрешён автоматически из-за конфликта
        self.assertIn(block3, unknown)

    def test_orchestrator_imports_inside_function(self):
        code = """
        def func():
            import os
            from sys import path
        """
        block = self._create_block_info(code)
        orchestrator = ModuleOrchestrator()
        containers, unknown = orchestrator.process_blocks([block])
        # Не должно быть модулей os, sys
        module_names = list(containers.keys())
        self.assertNotIn("os", module_names)
        self.assertNotIn("sys", module_names)

    def test_orchestrator_nested_classes(self):
        code = """
        class Outer:
            class Inner:
                def method(self):
                    pass
        """
        block = self._create_block_info(code)
        orchestrator = ModuleOrchestrator()
        containers, unknown = orchestrator.process_blocks([block])
        self.assertEqual(len(containers), 1)
        module = list(containers.values())[0]
        outer_class = None
        for child in module.children:
            if child.name == "Outer" and child.node_type == "class":
                outer_class = child
                break
        self.assertIsNotNone(outer_class)
        inner_class = None
        for child in outer_class.children:
            if child.name == "Inner" and child.node_type == "class":
                inner_class = child
                break
        self.assertIsNotNone(inner_class)
        method = None
        for child in inner_class.children:
            if child.name == "method" and child.node_type == "method":
                method = child
                break
        self.assertIsNotNone(method)

    def test_orchestrator_mixed_block(self):
        code = """
        # myapp.utils
        import os
        def helper():
            return os.getcwd()
        """
        block = self._create_block_info(code, "myapp.utils")
        orchestrator = ModuleOrchestrator()
        containers, unknown = orchestrator.process_blocks([block])
        self.assertIn("myapp.utils", containers)
        utils_module = containers["myapp.utils"]
        helper = None
        for child in utils_module.children:
            if child.name == "helper" and child.node_type == "function":
                helper = child
                break
        self.assertIsNotNone(helper)

    def test_orchestrator_circular_imports(self):
        block1 = self._create_block_info("# app.mod1\nfrom .mod2 import func2", "app.mod1")
        block2 = self._create_block_info("# app.mod2\nfrom .mod1 import func1", "app.mod2")
        orchestrator = ModuleOrchestrator()
        containers, unknown = orchestrator.process_blocks([block1, block2])
        self.assertIn("app.mod1", containers)
        self.assertIn("app.mod2", containers)

    # ---------- Тесты парсинга импортов ----------
    def test_extract_imports_absolute(self):
        code = "import os\nfrom sys import path\nfrom collections import defaultdict as dd"
        imports = extract_imports_from_block(code, current_module="myapp.module")
        self.assertEqual(len(imports), 3)
        self.assertEqual(imports[0].target_fullname, "os")
        self.assertEqual(imports[0].target_type, "module")
        self.assertEqual(imports[1].target_fullname, "sys.path")
        self.assertEqual(imports[1].target_type, "function")
        self.assertEqual(imports[2].target_fullname, "collections.defaultdict")
        self.assertEqual(imports[2].target_type, "function")
        self.assertEqual(imports[2].alias, "dd")

    def test_extract_imports_relative(self):
        code = "from . import utils\nfrom ..models import User"
        imports = extract_imports_from_block(code, current_module="myapp.sub.module")
        self.assertEqual(len(imports), 2)
        self.assertEqual(imports[0].target_fullname, "myapp.sub.utils")
        self.assertTrue(imports[0].is_relative)
        self.assertEqual(imports[0].target_type, "function")
        self.assertEqual(imports[1].target_fullname, "myapp.models.User")
        self.assertTrue(imports[1].is_relative)
        self.assertEqual(imports[1].target_type, "class")

    def test_extract_imports_multiline(self):
        code = "from myapp import (\n    utils,\n    models\n)"
        imports = extract_imports_from_block(code, current_module=None)
        self.assertEqual(len(imports), 1)

    def test_import_alias(self):
        code = "import os as operating_system"
        imports = extract_imports_from_block(code, current_module=None)
        self.assertEqual(len(imports), 1)
        imp = imports[0]
        self.assertEqual(imp.target_fullname, "os")
        self.assertEqual(imp.alias, "operating_system")
        self.assertEqual(imp.target_type, "module")

    def test_from_import_alias(self):
        code = "from collections import defaultdict as dd"
        imports = extract_imports_from_block(code, current_module=None)
        self.assertEqual(len(imports), 1)
        imp = imports[0]
        self.assertEqual(imp.target_fullname, "collections.defaultdict")
        self.assertEqual(imp.alias, "dd")
        self.assertEqual(imp.target_type, "function")


if __name__ == '__main__':
    unittest.main(verbosity=2)