from aichat_search.services.block_parser import MessageBlock
from aichat_search.tools.code_structure.utils.helpers import extract_module_hint

# Тест 1: комментарий с путём
block1 = MessageBlock(0, "# utils/helpers.py\nimport os\n\ndef foo(): pass", language="python")
print(extract_module_hint(block1))  # должно быть "utils.helpers"

# Тест 2: комментарий с путём без .py
block2 = MessageBlock(0, "# models/user\nclass User: pass", language="python")
print(extract_module_hint(block2))  # должно быть "models.user"

# Тест 3: комментарий с обратным слешем (Windows)
block3 = MessageBlock(0, "# utils\\helpers.py\nimport sys", language="python")
print(extract_module_hint(block3))  # должно быть "utils.helpers"

# Тест 4: нет комментария
block4 = MessageBlock(0, "import os\nprint('hello')", language="python")
print(extract_module_hint(block4))  # должно быть None

# Тест 5: комментарий не в первых строках (после пустых)
block5 = MessageBlock(0, "\n\n# main.py\nif __name__ == '__main__': pass", language="python")
print(extract_module_hint(block5))  # должно быть "main"