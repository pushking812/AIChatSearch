# aichat_search/tools/code_structure/facades/persistence_manager.py

import pickle
import os
import logging
from tkinter import messagebox
from typing import Optional

from aichat_search.tools.code_structure.module_resolution.services.module_service import ModuleService
from aichat_search.tools.code_structure.imports.services.import_service import ImportService
from aichat_search.tools.code_structure.block_processing.services.block_service import BlockService
from aichat_search.tools.code_structure.utils.logger import get_logger

logger = get_logger(__name__)


class PersistenceManager:
    def __init__(self, block_service: BlockService, module_service: ModuleService, import_service: ImportService):
        self.block_service = block_service
        self.module_service = module_service
        self.import_service = import_service

    def save_structure(self) -> None:
        """Сохраняет структуру в файл .config/project_structure.pkl."""
        try:
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '.config')
            config_dir = os.path.abspath(config_dir)
            os.makedirs(config_dir, exist_ok=True)
            file_path = os.path.join(config_dir, 'project_structure.pkl')
            data = {
                'module_containers': self.module_service.module_containers,
                'imported_items': self.import_service.get_imported_items(self.block_service.get_all_blocks())
            }
            with open(file_path, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info(f"Структура сохранена в {file_path}")
            messagebox.showinfo("Сохранение структуры", f"Структура сохранена в {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении структуры: {e}", exc_info=True)
            messagebox.showerror("Ошибка", f"Не удалось сохранить структуру: {e}")

    def load_structure(self) -> None:
        """Загружает структуру из файла .config/project_structure.pkl."""
        try:
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '.config')
            config_dir = os.path.abspath(config_dir)
            file_path = os.path.join(config_dir, 'project_structure.pkl')
            if not os.path.exists(file_path):
                messagebox.showinfo("Загрузка структуры", "Файл сохранённой структуры не найден.")
                return
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            self.module_service.module_containers = data['module_containers']
            logger.info(f"Структура загружена из {file_path}")
            messagebox.showinfo("Загрузка структуры", f"Структура загружена из {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке структуры: {e}", exc_info=True)
            messagebox.showerror("Ошибка", f"Не удалось загрузить структуру: {e}")