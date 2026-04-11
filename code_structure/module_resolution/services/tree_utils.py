# code_structure/module_resolution/services/tree_utils.py

import re
from typing import Optional, Set, List
from code_structure.models.code_node import CodeNode, ClassNode, FunctionNode, MethodNode, ImportNode, CommentNode
from code_structure.models.block import Block
from code_structure.imports.core.import_analyzer import extract_imports_from_block

def has_self_parameter(func_node: FunctionNode) -> bool:
    signature = getattr(func_node, 'signature', '')
    if signature and re.search(r'\b(self|cls)\b', signature):
        return True
    try:
        code = func_node.get_raw_code()
        match = re.search(r'def\s+\w+\s*\(([^)]*)\)', code)
        if match:
            params = match.group(1)
            if re.search(r'\b(self|cls)\b', params):
                return True
    except Exception:
        pass
    return False

def find_parent_class(node: CodeNode) -> Optional[ClassNode]:
    current = node.parent
    while current:
        if isinstance(current, ClassNode):
            return current
        current = current.parent
    return None

def extract_class_names(node: CodeNode) -> Set[str]:
    classes = set()
    if isinstance(node, ClassNode):
        classes.add(node.name)
    for child in node.children:
        if not isinstance(child, (ImportNode, CommentNode)):
            classes.update(extract_class_names(child))
    return classes

def extract_function_names(node: CodeNode) -> Set[str]:
    functions = set()
    if isinstance(node, FunctionNode) and not isinstance(node, MethodNode):
        functions.add(node.name)
    for child in node.children:
        if not isinstance(child, (ClassNode, ImportNode, CommentNode)):
            functions.update(extract_function_names(child))
    return functions

def extract_method_names(node: CodeNode) -> Set[str]:
    methods = set()
    if isinstance(node, MethodNode):
        methods.add(node.name)
    for child in node.children:
        methods.update(extract_method_names(child))
    return methods

def make_identifier_from_path(full_path: str, node_type: str) -> Optional[str]:
    parts = full_path.split('.')
    if node_type == 'module':
        return parts[-1] if parts else None
    elif node_type == 'class':
        return parts[-1] if parts else None
    elif node_type == 'function':
        if len(parts) >= 2:
            return f"{parts[-2]}.{parts[-1]}"
        return full_path
    elif node_type == 'method':
        if len(parts) >= 3:
            return f"{parts[-2]}.{parts[-1]}"
        return full_path
    return None

def infer_node_type(identifier: str, full_path: str) -> str:
    if '.' not in identifier:
        if identifier and identifier[0].isupper():
            return 'class'
        return 'module'
    else:
        parts = identifier.split('.')
        if len(parts) == 2:
            if parts[0][0].isupper():
                return 'method'
            else:
                return 'function'
        return 'method'