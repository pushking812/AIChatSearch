import pickle
import os
from typing import List, Optional
from .model import DataSource

def save_session(sources: List[DataSource], path: str) -> None:
    """Сохраняет список источников в файл с помощью pickle."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        pickle.dump(sources, f)

def load_session(path: str) -> Optional[List[DataSource]]:
    """Загружает список источников из файла pickle. Если файл не существует, возвращает None."""
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        return pickle.load(f)