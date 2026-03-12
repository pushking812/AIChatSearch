from aichat_search.tools.code_structure.utils.helpers import clean_code
from aichat_search.tools.code_structure.models.node import FunctionNode
from aichat_search.tools.code_structure.models.containers import Version

# Тест clean_code
code = '''
def test(a, b):
    """Docstring"""
    # comment
    return a + b
'''
cleaned = clean_code(code)
print("Cleaned:")
print(cleaned)
print("---")

# Тест Version
node = FunctionNode("test", "a, b", lineno_start=2, lineno_end=5)
version = Version(node, "test_block", 1, code)
print("Version cleaned content:", version.cleaned_content)
print("Sources:", version.sources)