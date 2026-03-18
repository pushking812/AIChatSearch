# aichat_search/tools/code_structure/controller.py

import logging
from typing import List, Dict, Optional, Any, Tuple

from aichat_search.model import Chat, MessagePair
from aichat_search.tools.code_structure.view import CodeStructureWindow
from aichat_search.tools.code_structure.services.block_service import BlockService
from aichat_search.tools.code_structure.services.module_service import ModuleService
from aichat_search.tools.code_structure.services.tree_service import TreeService
from aichat_search.tools.code_structure.services.dialog_service import DialogService
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo

logger = logging.getLogger(__name__)


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
        
        # View
        self.view = CodeStructureWindow(parent)
        self.view.set_controller(self)
        
        # Состояние
        self.current_lang: Optional[str] = None
        
        # Запуск обработки
        self._run_analysis()
    
    def _run_analysis(self):
        """Запускает полный цикл анализа."""
        # Загрузка блоков
        self.block_service.load_from_items(self.items)
        
        # Обработка блоков с ошибками
        error_blocks = self.block_service.get_error_blocks()
        if error_blocks:
            self._handle_error_blocks(error_blocks)
        
        # Определение модулей и построение структур
        all_blocks = self.block_service.get_all_blocks()
        containers, unknown = self.module_service.process_blocks(all_blocks)
        
        # Построение дерева отображения
        self._build_and_display_tree()
        
        # Настройка интерфейса
        self._setup_interface()
        
        # Показ диалога для неопределённых блоков
        if unknown:
            self._show_module_dialog(unknown)
    
    def _handle_error_blocks(self, error_blocks: List[MessageBlockInfo]):
        """Обрабатывает блоки с синтаксическими ошибками."""
        for block in error_blocks:
            result = self.dialog_service.show_error_dialog(
                block, 
                self.block_service.get_block_description(block)
            )
            if result is not None:
                self.block_service.fix_error_block(block, result)
    
    def _build_and_display_tree(self):
        """Строит и отображает дерево."""
        display_root = self.tree_service.build_display_tree(
            self.module_service.module_containers
        )
        if display_root:
            self.view.display_merged_tree(display_root)
    
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
        
        # Генерируем имена блоков для комбобокса
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
        
        result = self.dialog_service.show_module_assignment_dialog(
            unknown_blocks,
            block_descriptions,
            known_modules,
            module_sources,
            module_code_map,
            self.module_service.module_containers
        )
        
        if result:
            self._apply_dialog_result(result)
        else:
            self._rebuild_after_dialog()
    
    def _apply_dialog_result(self, assignments: Dict[str, str]):
        """Применяет результаты диалога."""
        all_blocks = self.block_service.get_all_blocks()
        for block in all_blocks:
            if block.block_id in assignments:
                self.module_service.assign_module_to_block(
                    block, assignments[block.block_id]
                )
            else:
                block.module_hint = None
        
        self.module_service.remove_temp_modules()
        
        # Повторное разрешение оставшихся блоков
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
        
        # Создаём временный оркестратор или используем существующий?
        # В оригинале был метод resolve_blocks, но его нет в ModuleOrchestrator.
        # Вероятно, нужно просто повторно запустить process_blocks?
        # Пока оставим заглушку.
        logger.warning("_resolve_remaining_after_dialog не реализован полностью")
        return []
    
    def _rebuild_after_dialog(self):
        """Перестраивает структуру после диалога."""
        logger.info("=== Перестроение после диалога ===")
        all_blocks = self.block_service.get_all_blocks()
        self.module_service.rebuild_after_dialog(all_blocks)
        self._build_and_display_tree()
    
    # ---------- Обработчики событий ----------
    
    def on_type_selected(self, event):
        """Обработчик выбора языка."""
        idx = self.view.type_combo.current()
        langs = self.block_service.get_languages()
        if 0 <= idx < len(langs):
            lang = langs[idx]
            if lang != self.current_lang:
                self._switch_language(lang)
    
    def on_block_selected(self, event=None):
        """Обработчик выбора блока."""
        self.on_show_structure()
    
    def on_show_structure(self):
        """Показывает структуру выбранного блока."""
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
        """Обработчик выбора узла в дереве."""
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
        """Обработчик выбора узла в объединённом дереве."""
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
    
    def _reset_module_assignments(self):
        """Сбрасывает все назначения модулей."""
        all_blocks = self.block_service.get_all_blocks()
        self.module_service.reset_assignments(all_blocks)
        
        containers, unknown = self.module_service.process_blocks(all_blocks)
        self._build_and_display_tree()
        
        if unknown:
            self._show_module_dialog(unknown)
            self._build_and_display_tree()