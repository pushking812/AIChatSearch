# code_structure/facades/persistence_manager.py

# code_structure/facades/persistence_manager.py

import pickle
import os
from tkinter import messagebox

import logging
from code_structure.utils.logger import get_logger
logger = get_logger(__name__, level=logging.WARNING)


class PersistenceManager:
    def __init__(self, block_service, import_service):
        self.block_service = block_service
        self.import_service = import_service

    def save_structure(self, versioned_roots: dict, parent=None):
        """Сохраняет структуру модулей (версионированное дерево) и импортированные объекты."""
        try:
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '.config')
            config_dir = os.path.abspath(config_dir)
            os.makedirs(config_dir, exist_ok=True)
            file_path = os.path.join(config_dir, 'project_structure.pkl')
            # Сохраняем дерево и импортированные объекты
            imported_items = self.import_service.get_imported_items(self.block_service.get_new_blocks())
            data = {
                'versioned_roots': versioned_roots,
                'imported_items': imported_items
            }
            with open(file_path, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info(f"Структура сохранена в {file_path}")
            if parent:
                messagebox.showinfo("Сохранение структуры", f"Структура сохранена в {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении структуры: {e}", exc_info=True)
            if parent:
                messagebox.showerror("Ошибка", f"Не удалось сохранить структуру: {e}")

    def load_structure(self, parent=None):
        """Загружает структуру модулей и импортированные объекты из файла."""
        try:
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '.config')
            config_dir = os.path.abspath(config_dir)
            file_path = os.path.join(config_dir, 'project_structure.pkl')
            if not os.path.exists(file_path):
                if parent:
                    messagebox.showinfo("Загрузка структуры", "Файл сохранённой структуры не найден.")
                return None, None
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            versioned_roots = data.get('versioned_roots', {})
            imported_items = data.get('imported_items', {})
            logger.info(f"Структура загружена из {file_path}")
            if parent:
                messagebox.showinfo("Загрузка структуры", f"Структура загружена из {file_path}")
            return versioned_roots, imported_items
        except Exception as e:
            logger.error(f"Ошибка при загрузке структуры: {e}", exc_info=True)
            if parent:
                messagebox.showerror("Ошибка", f"Не удалось загрузить структуру: {e}")
            return None, None