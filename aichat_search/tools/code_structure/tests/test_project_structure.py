# aichat_search/tools/code_structure/tests/test_project_structure.py

import unittest
import os
import sys
from typing import Dict, List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from aichat_search.services.block_parser import MessageBlock
from aichat_search.tools.code_structure.services.block_manager import BlockManager
from aichat_search.tools.code_structure.core.module_orchestrator import ModuleOrchestrator
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.parser import PythonParser


class TestProjectStructure(unittest.TestCase):
    """Проверяет, что фрагменты реального проекта группируются в правильные модули."""

    @classmethod
    def setUpClass(cls):
        # Ожидаемое соответствие: имя файла -> модуль
        cls.expected = {
            "018_БлокКодаPython.py": "deepseek.gui_components.chat_list",
            "020_БлокКодаPython.py": "deepseek.gui_components.application",
            "029_БлокКодаPython.py": "deepseek.gui_components.message_tree",
            "031_БлокКодаPython.py": "deepseek.gui_components.message_tree",
            "033_БлокКодаPython.py": "deepseek.gui_components.message_detail",
            "037_БлокКодаPython.py": "deepseek.gui_components.message_tree",
            "039_БлокКодаPython.py": "deepseek.gui_components.message_tree",
            "041_БлокКодаPython.py": "deepseek.gui_components.message_tree",
            "043_БлокКодаPython.py": "deepseek.gui_components.message_detail",
            "002_БлокКодаPython.py": "deepseek.controller",
            "004_БлокКодаPython.py": "deepseek.gui_components.chat_list",
            "006_БлокКодаPython.py": "deepseek.gui_components.application",
            "008_БлокКодаPython.py": "deepseek.gui_components.application",
            "010_БлокКодаPython.py": "deepseek.gui_components.application",
            "012_БлокКодаPython.py": "deepseek.gui_components.application",
            "016_БлокКодаPython.py": "deepseek.controller",
        }

    def setUp(self):
        self.orchestrator = ModuleOrchestrator()
        self.blocks_info = []
        # Собираем все файлы, начинающиеся с цифры
        test_dir = os.path.dirname(__file__)
        self.fragment_files = [
            f for f in os.listdir(test_dir)
            if f.endswith(".py") and f[0].isdigit()
        ]
        # Убедимся, что все ожидаемые файлы присутствуют
        for fname in self.expected:
            self.assertIn(fname, self.fragment_files, f"Файл {fname} не найден в тестовой директории")

    def _create_block_info(self, filename: str, content: str, index: int) -> MessageBlockInfo:
        """Создаёт блок с деревом из содержимого."""
        block = MessageBlock(index, content, "python", "response")
        block_info = MessageBlockInfo(block, "python", content, filename, index)
        parser = PythonParser()
        try:
            tree = parser.parse(content)
            block_info.set_tree(tree)
        except Exception as e:
            block_info.set_error(e)
        return block_info

    def test_grouping(self):
        # Загружаем все фрагменты
        for idx, fname in enumerate(self.fragment_files):
            path = os.path.join(os.path.dirname(__file__), fname)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.blocks_info.append(self._create_block_info(fname, content, idx))

        # Запускаем оркестратор
        containers, unknown = self.orchestrator.process_blocks(self.blocks_info)

        # Проверяем, что все блоки определены
        self.assertEqual(
            len(unknown), 0,
            f"Неопределённые блоки: {[b.block_id for b in unknown]}"
        )

        # Проверяем соответствие ожиданиям
        mismatches = []
        for block in self.blocks_info:
            expected = self.expected.get(block.block_id)
            if expected is None:
                continue  # на всякий случай, но все должны быть в expected
            if block.module_hint != expected:
                mismatches.append(f"{block.block_id}: получен {block.module_hint}, ожидался {expected}")

        self.assertEqual(mismatches, [], "\n".join(mismatches))

        # Дополнительно: проверим, что модули содержат ожидаемые классы/методы
        # (можно добавить при необходимости)

        # Вывод статистики
        print("\n=== Результаты группировки ===")
        for module_name, container in containers.items():
            print(f"Модуль {module_name}:")
            blocks_in = [b for b in self.blocks_info if b.module_hint == module_name]
            print(f"  Блоков: {len(blocks_in)}")
            for b in blocks_in:
                print(f"    - {b.block_id}")


if __name__ == '__main__':
    unittest.main()