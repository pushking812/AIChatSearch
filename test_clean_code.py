import sys
sys.path.insert(0, '.')  # чтобы импортировать модули из текущей папки

from code_structure.utils.helpers import clean_code

# Код из блока с отступами (из лога Version 2)
code1 = """def clear(self):
    for item in self.tree.get_children():
        self.tree.delete(item)"""

# Код из блока без отступов (из лога Version 0)
code2 = """def clear(self):
for item in self.tree.get_children():
self.tree.delete(item)"""

# Код из блока с вызовом _clear (из лога Version 1)
code3 = """def clear(self):
    self._clear()"""

print("=== Code1 (с отступами) ===")
print("Raw:")
print(code1)
print("\nNormalized:")
print(repr(clean_code(code1)))
print("\n")

print("=== Code2 (без отступов) ===")
print("Raw:")
print(code2)
print("\nNormalized:")
print(repr(clean_code(code2)))
print("\n")

print("=== Code3 (вызов _clear) ===")
print("Raw:")
print(code3)
print("\nNormalized:")
print(repr(clean_code(code3)))
print("\n")

# Проверка синтаксической валидности
import ast
print("=== Проверка синтаксиса ===")
for i, code in enumerate([code1, code2, code3], 1):
    try:
        ast.parse(code)
        print(f"Code{i}: синтаксис верен")
    except SyntaxError as e:
        print(f"Code{i}: синтаксическая ошибка: {e}")