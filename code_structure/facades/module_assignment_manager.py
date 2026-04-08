# code_structure/facades/module_assignment_manager.py

from typing import Dict, List, Optional
import logging
from code_structure.dialogs.dto import ModuleAssignmentInput, UnknownBlockInfo, KnownModuleInfo, TreeDisplayNode
from code_structure.parsing.core.tree_builder import TreeBuilderNew
from code_structure.models.block import Block
from code_structure.models.registry import BlockRegistry
from code_structure.models.versioned_node import VersionedNode
from code_structure.models.code_node import ClassNode
from code_structure.facades.structure_data_provider import StructureDataProvider
from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level=logging.INFO)


class ModuleAssignmentManager:
    def __init__(self, block_service, data_provider: StructureDataProvider):
        self.block_service = block_service
        self.data_provider = data_provider
        self.tree_builder = TreeBuilderNew()

    def get_module_assignment_input(self, local_only: bool) -> ModuleAssignmentInput:
        unknown_blocks = self.data_provider.get_unknown_blocks()
        logger.info(f"get_module_assignment_input: unknown_blocks={len(unknown_blocks)}")
        
        unknown_blocks_info = []
        for block in unknown_blocks:
            display_name = f"{block.display_name} – {self._get_block_description(block)}"
            unknown_blocks_info.append(UnknownBlockInfo(
                id=block.id,
                display_name=display_name,
                content=block.content
            ))

        versioned_roots = self.data_provider.get_versioned_roots()
        root_dict, _, path_map, source_map = self.tree_builder.build_display_tree(versioned_roots, local_only)
        module_tree = root_dict
        
        known_modules_info = []
        def collect_nodes_from_tree(node: TreeDisplayNode):
            if node.type in ('module', 'class', 'package'):
                vnode = path_map.get(node.full_name)
                if vnode:
                    code = self._render_node_code(vnode)
                else:
                    code = f"# {node.type.capitalize()} {node.text}\n# (нет кода)"
                known_modules_info.append(KnownModuleInfo(
                    name=node.full_name,
                    source="",
                    code=code
                ))
            for child in node.children:
                collect_nodes_from_tree(child)
        for child in module_tree.children:
            collect_nodes_from_tree(child)
        known_modules_info.sort(key=lambda m: m.name)

        return ModuleAssignmentInput(
            unknown_blocks=unknown_blocks_info,
            known_modules=known_modules_info,
            module_tree=module_tree
        )

    def apply_assignments(self, assignments: Dict[str, str], deleted_block_ids: List[str] = None):
        if deleted_block_ids is None:
            deleted_block_ids = []
        for block_id, module_name in assignments.items():
            self.data_provider.update_block_assignment(block_id, module_name, strategy="ManualAssignment")
        for block_id in deleted_block_ids:
            self.data_provider.mark_block_as_deleted(block_id)

    def _render_node_code(self, node: VersionedNode) -> str:
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

    def _get_block_description(self, block: Block) -> str:
        """
        Возвращает описание блока для отображения в диалоге.
        Если блок содержит класс, возвращает имя класса.
        Иначе – имя первой функции/метода или "блок_кода".
        """
        if block.code_tree is None:
            return "синтаксическая_ошибка"

        # Проверяем, есть ли в блоке класс
        has_class = any(isinstance(child, ClassNode) for child in block.code_tree.children)
        if has_class:
            # Находим первый класс
            for child in block.code_tree.children:
                if isinstance(child, ClassNode):
                    return f"class_{child.name}"
            return "class_?"

        # Если нет класса, ищем первую функцию/метод
        desc = self._find_first_definition(block.code_tree)
        if desc:
            return desc

        # Если нет определений, проверяем блоки кода
        for child in block.code_tree.children:
            if child.node_type == "code_block":
                return "блок_кода"

        return "блок_кода"

    def _find_first_definition(self, node) -> str:
        if node.node_type == "class":
            for child in node.children:
                if child.node_type == "method":
                    return f"class_{node.name}_def_{child.name}"
            return f"class_{node.name}"
        
        elif node.node_type == "function":
            return f"def_{node.name}"
        
        elif node.node_type == "method":
            parent = node.parent
            while parent:
                if parent.node_type == "class":
                    return f"class_{parent.name}_def_{node.name}"
                parent = parent.parent
            return f"def_{node.name}"
        
        for child in node.children:
            res = self._find_first_definition(child)
            if res:
                return res
        
        return ""