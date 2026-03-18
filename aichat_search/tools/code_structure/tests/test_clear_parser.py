# aichat_search/tools/code_structure/tests/test_clear_parser.py

import sys
import os
import re

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from aichat_search.tools.code_structure.parser import PythonParser
from aichat_search.tools.code_structure.models.node import FunctionNode, MethodNode

def extract_fragments_from_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    pattern = r'```python\n(.*?)```'
    fragments = re.findall(pattern, content, re.DOTALL)
    return [frag.strip() for frag in fragments]

def analyze_fragment(code, index):
    parser = PythonParser()
    try:
        tree = parser.parse(code)
    except Exception as e:
        print(f"Фрагмент {index}: ОШИБКА ПАРСИНГА: {e}")
        return

    def find_nodes(node):
        results = []
        if isinstance(node, (FunctionNode, MethodNode)):
            results.append(node)
        for child in node.children:
            results.extend(find_nodes(child))
        return results

    nodes = find_nodes(tree)
    print(f"\n--- Фрагмент {index} ---")
    print("Исходный код:")
    print(code[:200] + ("..." if len(code) > 200 else ""))
    for n in nodes:
        node_type = "MethodNode" if isinstance(n, MethodNode) else "FunctionNode"
        has_self = n.signature and n.signature.strip('()').startswith('self') or 'self' in n.signature
        print(f"  {node_type}: {n.name}, сигнатура: {n.signature}, self={has_self}")

if __name__ == "__main__":
    # Путь к файлу с фрагментами (предполагается, что он лежит в той же папке)
    script_dir = os.path.dirname(__file__)
    filepath = os.path.join(script_dir, "test_clear.txt")
    if not os.path.exists(filepath):
        print(f"Файл {filepath} не найден. Создайте его с содержимым из test_clear.txt.")
        sys.exit(1)
    fragments = extract_fragments_from_file(filepath)
    for i, frag in enumerate(fragments):
        analyze_fragment(frag, i)