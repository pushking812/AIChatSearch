# code_structure/utils/logger.py

import logging
import sys
import os
from typing import Dict, Optional

# Глобальный файл для логов (если None – используется "_all.log" при one_file=True)
GLOBAL_LOG_FILE: Optional[str] = "_all.log"
# Общая директория для всех логов (применяется к относительным путям)
LOG_DIR: Optional[str] = ".logs"

_file_handlers: Dict[str, logging.FileHandler] = {}


class CustomFileFormatter(logging.Formatter):
    def format(self, record):
        # 1. Считаем mm:ss на основе relativeCreated (оно в миллисекундах)
        millis = int(record.relativeCreated / 1)
        record.runtime = f"{millis:7d}"

        # 2. Логика rsplit для имени логгера (из прошлого шага)
        if '.' in record.name:
            record.short_name = record.name.rsplit('.', 1)[1]
        else:
            record.short_name = record.name

        return super().format(record)



def _resolve_log_path(file_path: str) -> str:
    if LOG_DIR is not None and not os.path.isabs(file_path):
        return os.path.abspath(os.path.join(LOG_DIR, os.path.normpath(file_path)))
    return os.path.abspath(file_path)

def _ensure_log_directory(file_path: str) -> None:
    dir_path = os.path.dirname(file_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)

def get_logger(
    name: str,
    level: int = logging.DEBUG,
    to_file: bool = True,
    file_path: Optional[str] = None,
    one_file: bool = False,
    append_file: bool = False
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)


    # Консольный обработчик
    # if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = CustomFileFormatter('[%(runtime)s] | %(short_name)25s | %(levelname)10s | %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    if not to_file:
        return logger

    # --- Определяем целевой файл ---
    target: Optional[str] = None
    if one_file:
        target = GLOBAL_LOG_FILE if GLOBAL_LOG_FILE is not None else "_all.log"
    elif file_path is not None:
        target = file_path
    else:
        safe_name = name.replace('.', '_')
        target = f"{safe_name}.log"

    if target is None:
        return logger

    abs_target = _resolve_log_path(target)
    _ensure_log_directory(abs_target)

    # Не добавляем повторно обработчик для этого файла к этому же логгеру
    for h in logger.handlers:
        if isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', None) == abs_target:
            return logger

    # Получаем или создаём FileHandler (один на файл, уровень обработчика = DEBUG)
    if abs_target not in _file_handlers:
        file_handler = logging.FileHandler(
            abs_target, mode='a' if append_file else 'w', encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)   # обработчик пропускает всё
        file_formatter = console_formatter
        # file_formatter = logging.Formatter(
            # '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        # )
        file_handler.setFormatter(file_formatter)
        # Принудительный сброс после каждой записи
        original_emit = file_handler.emit
        file_handler.emit = lambda record: (original_emit(record), file_handler.flush())
        _file_handlers[abs_target] = file_handler
    else:
        file_handler = _file_handlers[abs_target]
        # Уровень существующего обработчика не меняем (остаётся DEBUG)

    logger.addHandler(file_handler)
    return logger