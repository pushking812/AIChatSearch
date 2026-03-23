# aichat_search/tools/code_structure/controller.py

import logging
import pickle
import os
from tkinter import messagebox
from typing import List, Dict, Optional, Any, Tuple

from aichat_search.model import Chat, MessagePair
from aichat_search.tools.code_structure.view import CodeStructureWindow
from aichat_search.tools.code_structure.services.block_service import BlockService
from aichat_search.tools.code_structure.services.module_service import ModuleService
from aichat_search.tools.code_structure.services.tree_service import TreeService
from aichat_search.tools.code_structure.services.dialog_service import DialogService
from aichat_search.tools.code_structure.services.import_service import ImportService
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.core.project_tree_builder import ProjectTreeBuilder

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class CodeStructureController:
    """Координатор работы окна структуры кода."""

    def __init__(self, parent, items: List[Tuple[Chat, MessagePair]]):
        self.parent = parent
        self.items = items

        # Сервисы
        self.block_service = BlockService()
        self.module_service = ModuleService()
        self.tree_service = TreeService()
        self.dialog_service = DialogService(parent)
        self.import_service = ImportService()

        # View
        self.view = CodeStructureWindow(parent)
        self.view.set_controller(self)

        # Состояние
        self.current_lang: Optional[str] = None

        # Запуск обработки
        self._run_analysis()

    def _run_analysis(self):
        """Запускает полный цикл анализа."""
        self.block_service.load_from_items(self.items)

        error_blocks = self.block_service.get_error_blocks()
        if error_blocks:
            self._handle_error_blocks(error_blocks)

        all_blocks = self.block_service.get_all_blocks()

        # 1. Построение дерева проекта из комментариев и импортов
        project_builder = ProjectTreeBuilder()
        project_info = project_builder.process_blocks(all_blocks)

        # 2. Назначение module_hint блокам с классами/функциями
        need_dialog_from_project = project_builder.assign_blocks_to_modules(all_blocks)

        # 3. Добавляем определения блоков, получивших hint, в идентификатор
        for block in all_blocks:
            if block.module_hint and block.tree and not block.syntax_error:
                self.module_service.identifier.collect_from_tree(block.tree, block.module_hint)

        # 4. Обрабатываем блоки без hint оркестратором
        blocks_without_hint = [b for b in all_blocks if not b.module_hint]
        if blocks_without_hint:
            containers, unknown_from_orchestrator = self.module_service.process_blocks(blocks_without_hint)
            need_dialog = need_dialog_from_project + unknown_from_orchestrator
        else:
            need_dialog = need_dialog_from_project

        # 5. Перестраиваем структуру с учётом всех блоков
        self._rebuild_after_dialog()

        # 6. Построение дерева отображения
        imported_items = self.import_service.get_imported_items(all_blocks)
        self._build_and_display_tree(imported_items)

        # 7. Настройка интерфейса
        self._setup_interface()

        # 8. Показ диалога для неопределённых блоков
        if need_dialog:
            self._show_module_dialog(need_dialog)

    def _handle_error_blocks(self, error_blocks: List[MessageBlockInfo]):
        """Обрабатывает блоки с синтаксическими ошибками."""
        from aichat_search.tools.code_structure.ui import ErrorBlockDialog

        for block in error_blocks:
            dialog = ErrorBlockDialog(self.view, block)
            self.view.wait_window(dialog)
            if dialog.result is not None:
                self.block_service.fix_error_block(block, dialog.result)

    def _build_and_display_tree(self, imported_items: Dict[str, str]):
        """Строит и отображает дерево с иерархией пакетов."""
        display_root = self.tree_service.build_package_tree(
            self.module_service.module_containers,
            imported_items,
            local_only=True
        )
        if display_root:
            self.view.display_merged_tree(display_root)
            logger.info(f"Дерево с пакетами отображено")

    def _setup_interface(self):
        """Настраивает интерфейс."""
        languages = self.block_service.get_languages()
        if not languages:
            self.view.show_error("Нет блоков с поддерживаемыми языками")
            self.view.destroy()
            return

        self.view.set_type_combo_values([lang.capitalize() for lang in languages])
        self.current_lang = languages[0]
        self._switch_language(self.current_lang)

    def _switch_language(self, lang: str):
        """Переключает отображение на указанный язык."""
        self.current_lang = lang
        blocks = self.block_service.get_blocks_by_language(lang)

        block_names = []
        for block in blocks:
            desc = self.block_service.get_block_description(block)
            block_names.append(f"{block.block_id} – {desc}")

        self.view.set_block_combo_values(sorted(block_names))
        if block_names:
            self.view.set_current_block_index(0)

        self.view.clear_tree()
        self.view.display_code("")

    def _show_module_dialog(self, unknown_blocks: List[MessageBlockInfo]):
        """Показывает диалог назначения модулей."""
        from aichat_search.tools.code_structure.ui import ModuleAssignmentDialog

        all_blocks = self.block_service.get_all_blocks()
        known_modules = self.module_service.get_known_modules()

        # Подготавливаем описания блоков
        block_descriptions = {
            b.block_id: self.block_service.get_block_description(b)
            for b in all_blocks
        }

        # Подготавливаем источники модулей
        module_sources = {}
        module_code_map = {}
        for module in known_modules:
            module_sources[module] = self.module_service.get_module_source(module, all_blocks)
            code = self.module_service.get_module_code(module, all_blocks)
            if code:
                module_code_map[module] = code

        dialog_data = []
        for block in unknown_blocks:
            display_name = f"{block.block_id} – {block_descriptions.get(block.block_id, 'блок_кода')}"
            dialog_data.append({
                'id': block.block_id,
                'display_name': display_name,
                'content': block.content
            })

        module_info = []
        for module in sorted(known_modules):
            module_info.append({'name': module, 'source': module_sources.get(module)})

        dialog = ModuleAssignmentDialog(
            self.view,
            dialog_data,
            module_info,
            module_code_map,
            self.module_service.module_containers
        )
        dialog.controller = self
        self.view.wait_window(dialog)

        if dialog.result:
            self._apply_dialog_result(dialog.result)
        else:
            self._rebuild_after_dialog()

    def _apply_dialog_result(self, assignments: Dict[str, str]):
        """Применяет результаты диалога."""
        all_blocks = self.block_service.get_all_blocks()
        for block in all_blocks:
            if block.block_id in assignments:
                self.module_service.assign_module_to_block(block, assignments[block.block_id])
            else:
                block.module_hint = None
        self.module_service.remove_temp_modules()
        unknown = self._resolve_remaining_after_dialog()
        if unknown:
            self._show_module_dialog(unknown)
        else:
            self._rebuild_after_dialog()

    def _resolve_remaining_after_dialog(self) -> List[MessageBlockInfo]:
        """Повторно разрешает неопределённые блоки после диалога."""
        logger.info("=== Повторное автоматическое определение после диалога ===")
        all_blocks = self.block_service.get_all_blocks()
        unknown = [b for b in all_blocks if not b.module_hint and b.tree and not b.syntax_error]
        if not unknown:
            return []
        containers, new_unknown = self.module_service.process_blocks(unknown)
        return new_unknown

    def _rebuild_after_dialog(self):
        """Перестраивает структуру после диалога."""
        logger.info("=== Перестроение после диалога ===")
        all_blocks = self.block_service.get_all_blocks()
        self.module_service.rebuild_after_dialog(all_blocks)
        imported_items = self.import_service.get_imported_items(all_blocks)
        self._build_and_display_tree(imported_items)

    def _reset_module_assignments(self):
        """Сбрасывает все назначения модулей и запускает полный анализ заново."""
        all_blocks = self.block_service.get_all_blocks()
        self.module_service.reset_assignments(all_blocks)

        # Построение дерева проекта
        project_builder = ProjectTreeBuilder()
        project_info = project_builder.process_blocks(all_blocks)
        need_dialog_from_project = project_builder.assign_blocks_to_modules(all_blocks)

        # Добавляем определения в идентификатор
        for block in all_blocks:
            if block.module_hint and block.tree and not block.syntax_error:
                self.module_service.identifier.collect_from_tree(block.tree, block.module_hint)

        # Обрабатываем блоки без hint
        blocks_without_hint = [b for b in all_blocks if not b.module_hint]
        if blocks_without_hint:
            containers, unknown_from_orchestrator = self.module_service.process_blocks(blocks_without_hint)
            need_dialog = need_dialog_from_project + unknown_from_orchestrator
        else:
            need_dialog = need_dialog_from_project

        # Перестраиваем структуру
        self._rebuild_after_dialog()

        imported_items = self.import_service.get_imported_items(all_blocks)
        self._build_and_display_tree(imported_items)

        if need_dialog:
            self._show_module_dialog(need_dialog)
            self._build_and_display_tree(imported_items)

    # ---------- Методы для сохранения/загрузки структуры и создания проекта ----------
    def _save_structure(self):
        """Сохраняет текущую структуру проекта в файл .config/project_structure.pkl."""
        try:
            # Нормализованный путь к .config
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '.config')
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
            self.view.show_error(f"Не удалось сохранить структуру: {e}")

    def _load_structure(self):
        """Загружает структуру из файла .config/project_structure.pkl и восстанавливает дерево."""
        try:
            config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '.config')
            config_dir = os.path.abspath(config_dir)
            file_path = os.path.join(config_dir, 'project_structure.pkl')
            if not os.path.exists(file_path):
                messagebox.showinfo("Загрузка структуры", "Файл сохранённой структуры не найден.")
                return

            with open(file_path, 'rb') as f:
                data = pickle.load(f)

            # Восстанавливаем атрибуты
            self.module_service.module_containers = data['module_containers']
            imported_items = data['imported_items']

            # Обновляем дерево
            self._build_and_display_tree(imported_items)
            logger.info(f"Структура загружена из {file_path}")
            messagebox.showinfo("Загрузка структуры", f"Структура загружена из {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке структуры: {e}", exc_info=True)
            self.view.show_error(f"Не удалось загрузить структуру: {e}")

    def _create_project(self):
        """Создаёт проект на основе текущей структуры."""
        messagebox.showinfo("Создание проекта", "Функция создания проекта будет реализована в следующей версии.")

    # ---------- Обработчики событий ----------
    def on_type_selected(self, event):
        idx = self.view.type_combo.current()
        langs = self.block_service.get_languages()
        if 0 <= idx < len(langs):
            lang = langs[idx]
            if lang != self.current_lang:
                self._switch_language(lang)

    def on_block_selected(self, event=None):
        self.on_show_structure()

    def on_show_structure(self):
        idx = self.view.get_selected_block_index()
        if idx < 0:
            return
        blocks = self.block_service.get_blocks_by_language(self.current_lang)
        if idx >= len(blocks):
            return
        selected = self.view.block_combo.get()
        block = None
        for b in blocks:
            desc = self.block_service.get_block_description(b)
            if f"{b.block_id} – {desc}" == selected:
                block = b
                break
        if block and block.tree and not block.syntax_error:
            self.view.display_structure(block.tree)

    def on_node_selected(self):
        selected = self.view.tree.selection()
        if not selected:
            return
        item = selected[0]
        node = self.view.get_node_by_item(item)
        if not (node and node.lineno_start and node.lineno_end):
            return
        idx = self.view.get_selected_block_index()
        if idx < 0:
            return
        blocks = self.block_service.get_blocks_by_language(self.current_lang)
        if idx >= len(blocks):
            return
        selected_name = self.view.block_combo.get()
        block = None
        for b in blocks:
            desc = self.block_service.get_block_description(b)
            if f"{b.block_id} – {desc}" == selected_name:
                block = b
                break
        if block:
            lines = block.content.splitlines()
            start = max(0, node.lineno_start - 1)
            end = min(len(lines), node.lineno_end)
            if start < end:
                self.view.display_code("\n".join(lines[start:end]))

    def on_merged_node_selected(self, node_data: Dict[str, Any]):
        if node_data.get('type') == 'version':
            version = node_data.get('_version_data')
            if version and version.sources:
                block_id, start, end, _ = version.sources[0]
                for block in self.block_service.get_all_blocks():
                    if block.block_id == block_id:
                        lines = block.content.splitlines()
                        code = '\n'.join(lines[start-1:end]) if start and end else block.content
                        self.view.display_merged_code(code, block.language)
                        return
        else:
            self.view.display_merged_code("")