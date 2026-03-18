# aichat_search/tools/code_structure/controller.py

import logging
from typing import List, Dict, Optional, Tuple, Any

from aichat_search.model import Chat, MessagePair
from aichat_search.tools.code_structure.view import CodeStructureWindow
from aichat_search.tools.code_structure.services.block_manager import BlockManager
from aichat_search.tools.code_structure.models.block_info import MessageBlockInfo
from aichat_search.tools.code_structure.core.module_orchestrator import ModuleOrchestrator
from aichat_search.tools.code_structure.core.tree_builder import TreeBuilder
from aichat_search.tools.code_structure.core.module_resolver import ModuleResolver
from aichat_search.tools.code_structure.parser import PythonParser

from aichat_search.tools.code_structure.ui import ErrorBlockDialog, ModuleAssignmentDialog

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class CodeStructureController:
    """Координатор работы окна структуры кода."""

    def __init__(self, parent, items: List[Tuple[Chat, MessagePair]]):
        self.parent = parent
        self.items = items
        self.view = CodeStructureWindow(parent)
        self.view.set_controller(self)

        # Компоненты
        self.block_manager = BlockManager()
        self.orchestrator = ModuleOrchestrator()
        self.tree_builder = TreeBuilder()

        # Состояние
        self.current_lang: Optional[str] = None
        self.display_root: Optional[Dict[str, Any]] = None

        # Запуск обработки
        self._run_analysis()

    def _run_analysis(self):
        """Запускает полный цикл анализа."""
        # Загрузка блоков
        self.block_manager.load_from_items(self.items)

        # Проверка на наличие блоков с ошибками парсинга
        error_blocks = [b for b in self.block_manager.get_all_blocks() if b.syntax_error]
        if error_blocks:
            self._handle_error_blocks(error_blocks)

        # Определение модулей и построение структур
        unknown_blocks = self._resolve_modules()

        # Построение дерева отображения
        self._build_and_display_tree()

        # Настройка интерфейса
        self._setup_interface()

        # Показ диалога для неопределённых блоков
        if unknown_blocks:
            self._show_module_dialog(unknown_blocks)

    def _handle_error_blocks(self, error_blocks: List[MessageBlockInfo]):
        """Обрабатывает блоки с синтаксическими ошибками: предлагает пользователю исправить."""
        from aichat_search.tools.code_structure.ui.dialogs import ErrorBlockDialog
        parser = PythonParser()
        for block in error_blocks:
            dialog = ErrorBlockDialog(self.view, block)
            self.view.wait_window(dialog)
            if dialog.result is not None:
                # Заменяем содержимое и перепарсиваем
                block.content = dialog.result
                try:
                    tree = parser.parse(block.content)
                    block.set_tree(tree)
                    block.syntax_error = None
                except Exception as e:
                    block.set_error(e)
                    # Если снова ошибка, можно показать сообщение, но оставим как есть
                    self.view.show_error(f"Не удалось исправить ошибку в блоке {block.block_id}: {e}")
            else:
                # Пользователь пропустил блок, он останется с ошибкой
                pass

    def _resolve_modules(self) -> List[MessageBlockInfo]:
        """Определяет модули для блоков. Возвращает неопределённые блоки."""
        logger.info("=== НАЧАЛО определения модулей ===")

        # Запускаем оркестратор
        containers, unknown = self.orchestrator.process_blocks(
            self.block_manager.get_all_blocks()
        )

        logger.info(f"Определено модулей: {len(containers)}")
        logger.info(f"Неопределённых блоков: {len(unknown)}")

        return unknown

    def _build_and_display_tree(self):
        """Строит и отображает дерево."""
        self.display_root = self.tree_builder.build_display_tree(
            self.orchestrator.module_containers
        )

        if self.display_root:
            self.view.display_merged_tree(self.display_root)
            logger.info(f"Дерево отображено, модулей: {len(self.display_root['children'])}")

    def _setup_interface(self):
        """Настраивает интерфейс (языки, блоки)."""
        if not self.block_manager.get_languages():
            self.view.show_error("Нет блоков с поддерживаемыми языками")
            self.view.destroy()
            return

        langs = [lang.capitalize() for lang in self.block_manager.get_languages()]
        self.view.set_type_combo_values(langs)

        self.current_lang = self.block_manager.get_languages()[0]
        self._switch_language(self.current_lang)

    def _switch_language(self, lang: str):
        self.current_lang = lang
        blocks = self.block_manager.get_blocks_by_lang(lang)
        block_names = self._generate_block_names(blocks)

        self.view.set_block_combo_values(block_names)
        if block_names:
            self.view.set_current_block_index(0)

        self.view.clear_tree()
        self.view.display_code("")

    def _generate_block_names(self, blocks: List[MessageBlockInfo]) -> List[str]:
        names = []
        for block in blocks:
            desc = self._get_block_description(block)
            names.append(f"{block.block_id} – {desc}")
        return sorted(names)

    def _get_block_description(self, block: MessageBlockInfo) -> str:
        if block.module_hint:
            return block.module_hint
        if block.tree is None or block.syntax_error:
            return "ошибка" if block.syntax_error else "блок_кода"

        def find_first(node):
            for child in node.children:
                if child.node_type == "class":
                    for m in child.children:
                        if m.node_type == "method":
                            return f"class_{child.name}_def_{m.name}"
                    return f"class_{child.name}"
                elif child.node_type == "function":
                    return f"def_{child.name}"
                else:
                    res = find_first(child)
                    if res:
                        return res
            return None

        return find_first(block.tree) or "блок_кода"

    def _show_module_dialog(self, unknown_blocks: List[MessageBlockInfo]):
        dialog_data = []
        for block_info in unknown_blocks:
            dialog_data.append({
                'id': block_info.block_id,
                'display_name': f"{block_info.block_id} – {self._get_block_description(block_info)}",
                'content': block_info.content
            })

        known_modules = self.orchestrator.module_identifier.get_known_modules()

        module_info = []
        for module in sorted(known_modules):
            source = None
            for bi in self.block_manager.get_all_blocks():
                if bi.module_hint == module and bi.tree:
                    source = f"{bi.block_id} – {self._get_block_description(bi)}"
                    break
            module_info.append({'name': module, 'source': source})

        module_code_map = {}
        for module in known_modules:
            for bi in self.block_manager.get_all_blocks():
                if bi.module_hint == module and bi.content:
                    module_code_map[module] = bi.content
                    break

        from aichat_search.tools.code_structure.ui.dialogs import ModuleAssignmentDialog
        dialog = ModuleAssignmentDialog(
            self.view,
            dialog_data,
            module_info,
            module_code_map,
            self.orchestrator.module_containers  # передаём контейнеры для отображения в дереве
        )
        dialog.controller = self
        self.view.wait_window(dialog)

        if dialog.result:
            assigned_ids = set(dialog.result.keys())
            for block_info in self.block_manager.get_all_blocks():
                if block_info.block_id in assigned_ids:
                    old_hint = block_info.module_hint
                    block_info.module_hint = dialog.result[block_info.block_id]
                    logger.info(f"Диалог: {block_info.block_id}: {old_hint} -> {block_info.module_hint}")
                    if block_info.tree and not block_info.syntax_error:
                        self.orchestrator.module_identifier.collect_from_tree(
                            block_info.tree, block_info.module_hint
                        )
                else:
                    block_info.module_hint = None

            self.orchestrator.module_identifier.remove_temp_modules()
            remaining = self._resolve_remaining_after_dialog()
            if remaining:
                self._show_module_dialog(remaining)
            else:
                self._rebuild_after_dialog()
        else:
            self._rebuild_after_dialog()
            
    def _resolve_remaining_after_dialog(self) -> List[MessageBlockInfo]:
        logger.info("=== Повторное автоматическое определение после диалога ===")
        all_blocks = self.block_manager.get_all_blocks()
        unknown = [b for b in all_blocks if not b.module_hint and b.tree and not b.syntax_error]
        if not unknown:
            return []
        return self.orchestrator.resolve_blocks(unknown)

    def _rebuild_after_dialog(self):
        logger.info("=== Перестроение после диалога ===")
        self.orchestrator.module_identifier.remove_temp_modules()
        all_blocks = self.block_manager.get_all_blocks()
        self.orchestrator.module_groups = self.orchestrator._group_blocks_by_module(all_blocks)
        self.orchestrator._select_base_blocks()
        self.orchestrator.module_containers = {}
        self.orchestrator._build_initial_structures()
        self.orchestrator._merge_remaining_blocks()
        self.orchestrator._merge_temp_modules()
        self._build_and_display_tree()

    # ---------- Обработчики событий ----------
    def on_type_selected(self, event):
        idx = self.view.type_combo.current()
        langs = self.block_manager.get_languages()
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
        blocks = self.block_manager.get_blocks_by_lang(self.current_lang)
        if idx >= len(blocks):
            return
        selected = self.view.block_combo.get()
        block = None
        for b in blocks:
            if f"{b.block_id} – {self._get_block_description(b)}" == selected:
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
        blocks = self.block_manager.get_blocks_by_lang(self.current_lang)
        if idx >= len(blocks):
            return
        selected_name = self.view.block_combo.get()
        block = None
        for b in blocks:
            if f"{b.block_id} – {self._get_block_description(b)}" == selected_name:
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
                for block in self.block_manager.get_all_blocks():
                    if block.block_id == block_id:
                        lines = block.content.splitlines()
                        code = '\n'.join(lines[start-1:end]) if start and end else block.content
                        self.view.display_merged_code(code, block.language)
                        return
        else:
            self.view.display_merged_code("")

    def _reset_module_assignments(self):
        for block in self.block_manager.get_all_blocks():
            block.module_hint = None
        unknown = self._resolve_modules()
        self._build_and_display_tree()
        if unknown:
            self._show_module_dialog(unknown)
            self._build_and_display_tree()