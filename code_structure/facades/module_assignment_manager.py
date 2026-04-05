# code_structure/facades/module_assignment_manager.py

from typing import Dict, List, Optional
import logging
from code_structure.dialogs.dto import ModuleAssignmentInput, UnknownBlockInfo, KnownModuleInfo, TreeDisplayNode
from code_structure.parsing.core.tree_builder import TreeBuilderNew
from code_structure.models.block import Block
from code_structure.models.registry import BlockRegistry
from code_structure.models.versioned_node import VersionedNode
from code_structure.facades.structure_data_provider import StructureDataProvider
from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level=logging.INFO)


class ModuleAssignmentManager:
    def __init__(self, block_service, data_provider: StructureDataProvider):
        self.block_service = block_service
        self.data_provider = data_provider
        self.tree_builder = TreeBuilderNew()

    def get_module_assignment_input(self, local_only: bool) -> ModuleAssignmentInput:
        all_blocks = self.block_service.get_new_blocks()
        logger.info(f"get_module_assignment_input: всего блоков={len(all_blocks)}")
        
        unknown_blocks = [b for b in all_blocks if b.module_hint is None and b.language in ('python', 'py')]
        logger.info(f"  unknown_blocks={len(unknown_blocks)}")

        unknown_blocks_info = []
        for block in unknown_blocks:
            display_name = f"{block.display_name} – {self._get_block_description(block)}"
            unknown_blocks_info.append(UnknownBlockInfo(
                id=block.id,
                display_name=display_name,
                content=block.content
            ))

        versioned_roots = self.data_provider.get_versioned_roots()
        known_modules_info = []
        
        def collect_local_nodes(node: VersionedNode, path: str = ""):
            current_path = f"{path}.{node.name}" if path else node.name
            
            if node.name and node.name.startswith('_temp_'):
                return
            if getattr(node, 'is_imported', False):
                return
            
            if node.node_type in ('module', 'class', 'package'):
                if node.versions:
                    code = self._render_node_code(node)
                else:
                    code = f"# {node.node_type.capitalize()} {node.name}\n# (нет кода)"
                
                known_modules_info.append(KnownModuleInfo(
                    name=current_path,
                    source="",
                    code=code
                ))
            
            for child in node.children:
                collect_local_nodes(child, current_path)
        
        for root in versioned_roots.values():
            collect_local_nodes(root)
        
        known_modules_info.sort(key=lambda m: m.name)
        
        logger.info(f"  known_modules={len(known_modules_info)}")

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
        """Обновляет module_hint в блоках согласно назначениям, используя инкрементальное обновление дерева."""
        for block_id, module_name in assignments.items():
            self.data_provider.update_block_assignment(block_id, module_name, strategy="ManualAssignment")

    def reset_assignments(self):
        """Сбрасывает module_hint для всех блоков с полной перестройкой структуры."""
        self.data_provider.rebuild_structure()

    def _get_block_description(self, block: Block) -> str:
        """
        Возвращает описание блока (имя класса/функции/метода или "блок_кода").
        """
        if block.code_tree is None:
            return "синтаксическая_ошибка"
        
        # Ищем первое определение (класс, функцию или метод)
        desc = self._find_first_definition(block.code_tree)
        
        # Если нашли определение, возвращаем его
        if desc:
            return desc
        
        # Если нет определений, но есть блок кода
        for child in block.code_tree.children:
            if child.node_type == "code_block":
                return "блок_кода"
        
        return "блок_кода"

    def _find_first_definition(self, node) -> str:
        """
        Рекурсивно ищет первое определение (класс, функцию, метод).
        Возвращает строку вида:
        - для класса: "class_ClassName"
        - для метода: "class_ClassName_def_methodName"
        - для функции: "def_functionName"
        """
        if node.node_type == "class":
            # Ищем первый метод в классе
            for child in node.children:
                if child.node_type == "method":
                    return f"class_{node.name}_def_{child.name}"
            return f"class_{node.name}"
        
        elif node.node_type == "function":
            return f"def_{node.name}"
        
        elif node.node_type == "method":
            # Если метод найден, ищем его класс-родитель
            parent = node.parent
            while parent:
                if parent.node_type == "class":
                    return f"class_{parent.name}_def_{node.name}"
                parent = parent.parent
            return f"def_{node.name}"
        
        # Рекурсивный обход детей
        for child in node.children:
            res = self._find_first_definition(child)
            if res:
                return res
        
        return ""