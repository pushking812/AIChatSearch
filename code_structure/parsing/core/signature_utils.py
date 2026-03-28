# code_structure/parsing/core/signature_utils.py

from typing import Tuple, List, Dict
import re


def extract_function_signature(node) -> Tuple[bool, List[str]]:
    """
    Извлекает сигнатуру функции/метода из узла.
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
            # Убираем * и ** для сравнения
            param = param.lstrip('*')
            params.append(param)
    
    has_self = len(params) > 0 and params[0] in ('self', 'cls')
    return has_self, params


def compare_signatures(
    sig1: Tuple[bool, List[str]], 
    sig2: Tuple[bool, List[str]],
    ignore_self: bool = False
) -> bool:
    """
    Сравнивает две сигнатуры.
    
    Args:
        sig1, sig2: сигнатуры для сравнения
        ignore_self: если True, игнорирует наличие self/cls при сравнении
    
    Returns:
        True если сигнатуры совпадают с учетом параметров
    """
    has_self1, params1 = sig1
    has_self2, params2 = sig2
    
    if ignore_self:
        # Игнорируем self/cls при сравнении
        p1 = params1[1:] if has_self1 and params1 and params1[0] in ('self', 'cls') else params1
        p2 = params2[1:] if has_self2 and params2 and params2[0] in ('self', 'cls') else params2
        return p1 == p2
    else:
        # Стандартное сравнение с учетом self
        if has_self1 != has_self2:
            return False
        if has_self1:
            return params1[1:] == params2[1:]
        return params1 == params2


def are_signatures_similar(
    sig1: Tuple[bool, List[str]], 
    sig2: Tuple[bool, List[str]],
    tolerance: float = 0.7
) -> bool:
    """
    Проверяет, похожи ли сигнатуры (нечеткое сравнение).
    Полезно для поиска похожих, но не идентичных функций.
    """
    has_self1, params1 = sig1
    has_self2, params2 = sig2
    
    # Игнорируем self для сравнения
    p1 = params1[1:] if has_self1 and params1 and params1[0] in ('self', 'cls') else params1
    p2 = params2[1:] if has_self2 and params2 and params2[0] in ('self', 'cls') else params2
    
    if len(p1) != len(p2):
        return False
    
    if not p1:
        return True
    
    matches = sum(1 for a, b in zip(p1, p2) if a == b)
    return matches / len(p1) >= tolerance


def detect_method_likelihood(code_fragment: str) -> Dict[str, bool]:
    """
    Определяет вероятность того, что функция на самом деле метод.
    Возвращает контекстные флаги для сравнения.
    """
    flags = {
        'is_method_context': False,
        'allow_self_mismatch': False,
        'has_self_usage': False,
        'has_class_usage': False,
        'has_method_decorator': False
    }
    
    if not code_fragment:
        return flags
    
    # 1. Использование self. или cls. внутри (не только в параметрах)
    if re.search(r'\bself\.', code_fragment):
        flags['is_method_context'] = True
        flags['allow_self_mismatch'] = True
        flags['has_self_usage'] = True
    
    if re.search(r'\bcls\.', code_fragment):
        flags['is_method_context'] = True
        flags['allow_self_mismatch'] = True
        flags['has_class_usage'] = True
    
    # 2. Обращение к атрибутам класса (Classname.attr)
    if re.search(r'\b[A-Z][a-zA-Z0-9]*\.', code_fragment):
        flags['is_method_context'] = True
    
    # 3. Декораторы, характерные для методов
    if re.search(r'@(classmethod|staticmethod|property)', code_fragment):
        flags['is_method_context'] = True
        flags['allow_self_mismatch'] = True
        flags['has_method_decorator'] = True
    
    # 4. Использование super()
    if re.search(r'\bsuper\(\)', code_fragment) or re.search(r'\bsuper\([^)]+\)', code_fragment):
        flags['is_method_context'] = True
        flags['allow_self_mismatch'] = True
    
    # 5. Наличие self в параметрах (из сигнатуры мы уже знаем, но здесь проверяем по тексту)
    if re.search(r'def\s+\w+\s*\(\s*self\s*[,)]', code_fragment):
        flags['is_method_context'] = True
    
    if re.search(r'def\s+\w+\s*\(\s*cls\s*[,)]', code_fragment):
        flags['is_method_context'] = True
        flags['allow_self_mismatch'] = True
    
    return flags


def get_param_count(signature: Tuple[bool, List[str]], include_self: bool = False) -> int:
    """Возвращает количество параметров."""
    has_self, params = signature
    if include_self:
        return len(params)
    if has_self and params and params[0] in ('self', 'cls'):
        return len(params) - 1
    return len(params)


def has_self_param(signature: Tuple[bool, List[str]]) -> bool:
    """Проверяет наличие self/cls в сигнатуре."""
    has_self, params = signature
    return has_self and params and params[0] in ('self', 'cls')


def signature_to_string(signature: Tuple[bool, List[str]]) -> str:
    """Преобразует сигнатуру в строковое представление."""
    has_self, params = signature
    return f"({', '.join(params)})"


def normalize_signature(signature: str) -> str:
    """
    Нормализует строковую сигнатуру для сравнения.
    Убирает пробелы, аннотации типов, значения по умолчанию.
    """
    sig = signature.strip('()')
    params = []
    
    for param in sig.split(','):
        param = param.strip()
        if not param:
            continue
        
        if ':' in param:
            param = param.split(':')[0].strip()
        if '=' in param:
            param = param.split('=')[0].strip()
        param = param.lstrip('*')
        
        if param:
            params.append(param)
    
    return ', '.join(params)