# code_structure/facades/module_assignment_manager.py

from typing import Dict, List, Optional
from code_structure.dialogs.dto import ModuleAssignmentInput, UnknownBlockInfo, KnownModuleInfo, TreeDisplayNode
from code_structure.parsing.core.tree_builder import TreeBuilderNew
from code_structure.models.block import Block
from code_structure.models.registry import BlockRegistry
from code_structure.models.versioned_node import VersionedNode
from code_structure.facades.structure_data_provider import StructureDataProvider


class ModuleAssignmentManager:
    def __init__(self, block_service, data_provider: StructureDataProvider):
        """
        Args:
            block_service: BlockService (для доступа к блокам)
            data_provider: StructureDataProvider (для доступа к версионному дереву)
        """
        self.block_service = block_service
        self.data_provider = data_provider
        self.tree_builder = TreeBuilderNew()

    def get_module_assignment_input(self, local_only: bool) -> ModuleAssignmentInput:
        # Получаем неизвестные блоки (те, у которых нет module_hint)
        all_blocks = self.block_service.get_new_blocks()
        unknown_blocks = [b for b in all_blocks if b.module_hint is None and b.language in ('python', 'py')]

        unknown_blocks_info = []
        for block in unknown_blocks:
            display_name = f"{block.display_name} – {self._get_block_description(block)}"
            unknown_blocks_info.append(UnknownBlockInfo(
                id=block.id,
                display_name=display_name,
                content=block.content
            ))

        # Получаем известные модули из versioned_roots (ключи словаря)
        versioned_roots = self.data_provider.get_versioned_roots()
        known_modules_info = []
        for module_name in sorted(versioned_roots.keys()):
            if module_name.startswith('__'):
                continue
            # Получаем код модуля из дерева
            code = self._get_module_code_from_tree(module_name, versioned_roots)
            known_modules_info.append(KnownModuleInfo(
                name=module_name,
                source="",
                code=code
            ))

        # Построение дерева модулей для отображения
        root_dict, _, _, _ = self.tree_builder.build_display_tree(versioned_roots, local_only)
        module_tree = root_dict

        return ModuleAssignmentInput(
            unknown_blocks=unknown_blocks_info,
            known_modules=known_modules_info,
            module_tree=module_tree
        )

    def _get_module_code_from_tree(self, module_name: str, roots: Dict[str, VersionedNode]) -> str:
        """Извлекает код модуля из VersionedNode дерева."""
        node = roots.get(module_name)
        if node:
            return self._render_node_code(node)
        return ""

    def _render_node_code(self, node: VersionedNode) -> str:
        """Рекурсивно собирает код узла (модуля, класса, функции)."""
        if node.node_type in ('function', 'method', 'code_block', 'import'):
            return node.get_latest_code()
        elif node.node_type == 'class':
            class_lines = [f"class {node.name}:"]
            for child in node.children:
                child_code = self._render_node_code(child)
                if child_code:
                    class_lines.extend("    " + line for line in child_code.splitlines())
            return '\n'.join(class_lines)
        elif node.node_type == 'module':
            lines = []
            for child in node.children:
                child_code = self._render_node_code(child)
                if child_code:
                    lines.append(child_code)
            return '\n\n'.join(lines)
        elif node.node_type == 'package':
            return "# Пакет (не содержит кода)"
        return ""

    def apply_assignments(self, assignments: Dict[str, str]):
        """Обновляет module_hint в блоках согласно назначениям."""
        for block_id, module_name in assignments.items():
            block = self.block_service.get_new_block(block_id)
            if block:
                new_block = Block(
                    id=block.id,
                    chat=block.chat,
                    message_pair=block.message_pair,
                    language=block.language,
                    content=block.content,
                    block_idx=block.block_idx,
                    global_index=block.global_index,
                    code_tree=block.code_tree,
                    module_hint=module_name,
                    assignment_strategy="ManualAssignment"
                )
                BlockRegistry().register(new_block)
        # После назначений нужно перестроить дерево. Это будет сделано при следующем обновлении UI.

    def reset_assignments(self):
        """Сбрасывает module_hint для всех блоков."""
        all_blocks = self.block_service.get_new_blocks()
        for block in all_blocks:
            if block.module_hint:
                new_block = Block(
                    id=block.id,
                    chat=block.chat,
                    message_pair=block.message_pair,
                    language=block.language,
                    content=block.content,
                    block_idx=block.block_idx,
                    global_index=block.global_index,
                    code_tree=block.code_tree,
                    module_hint=None,
                    assignment_strategy=None
                )
                BlockRegistry().register(new_block)

    def _get_block_description(self, block: Block) -> str:
        """Возвращает описание блока (имя класса/функции или просто "блок кода")."""
        if block.code_tree is None:
            return "ошибка"
        desc = self._find_first_definition(block.code_tree)
        return desc or "блок_кода"

    def _find_first_definition(self, node) -> str:
        if node.node_type == "class":
            for child in node.children:
                if child.node_type == "method":
                    return f"class_{node.name}_def_{child.name}"
            return f"class_{node.name}"
        elif node.node_type == "function":
            return f"def_{node.name}"
        for child in node.children:
            res = self._find_first_definition(child)
            if res:
                return res
        return ""