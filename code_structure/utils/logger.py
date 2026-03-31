# code_structure/utils/logger.py

import logging
import sys

def get_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    Возвращает логгер с заданным именем, настроенный на вывод в консоль.
    Если у логгера ещё нет обработчиков, добавляется StreamHandler с указанным уровнем.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        # formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger