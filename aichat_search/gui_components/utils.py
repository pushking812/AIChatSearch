# aichat_search/gui_components/utils.py

from datetime import datetime
from . import constants

def format_datetime(dt) -> str:
    """Форматирует datetime в строку 'ДД-ММ-ГГГГ ЧЧ:ММ' или возвращает пустую строку."""
    if dt:
        return dt.strftime("%d-%m-%Y %H:%M")
    return ""

def escape_newlines(text: str) -> str:
    """Заменяет символы перевода строки на видимые последовательности '\n'."""
    if not text:
        return ""
    return text.replace('\n', '\\n')

def get_context(text: str, start: int, end: int) -> str:
    """
    Возвращает фрагмент текста вокруг позиции совпадения.
    Выделяет до CONTEXT_CHARS символов слева и справа.
    """
    if not text:
        return ""
    context_chars = constants.CONTEXT_CHARS
    left = max(0, start - context_chars)
    right = min(len(text), end + context_chars)
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(text) else ""
    fragment = text[left:right]
    fragment = escape_newlines(fragment)
    return f"{prefix}{fragment}{suffix}"