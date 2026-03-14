# aichat_search/tools/code_structure/core/signature_utils.py

from typing import Tuple, List, Optional
from aichat_search.tools.code_structure.models.node import Node

def extract_function_signature(node: Node) -> Tuple[bool, List[str]]:
    """
    Извлекает сигнатуру функции/метода.
    Возвращает (has_self, list_of_param_names)
    """
    if node.node_type not in ('function', 'method'):
        return False, []
    
    signature = node.signature.strip('()')
    if not signature:
        return False, []
    
    params = []
    for param in signature.split(','):
        param = param.strip()
        if param:
            if ':' in param:
                param = param.split(':')[0].strip()
            if '=' in param:
                param = param.split('=')[0].strip()
            params.append(param)
    
    has_self = len(params) > 0 and params[0] in ('self', 'cls')
    return has_self, params

def compare_signatures(sig1: Tuple[bool, List[str]], sig2: Tuple[bool, List[str]]) -> bool:
    """
    Сравнивает две сигнатуры с учётом self.
    """
    has_self1, params1 = sig1
    has_self2, params2 = sig2
    
    if has_self1 != has_self2:
        return False
    
    if has_self1:
        return params1[1:] == params2[1:]
    else:
        return params1 == params2