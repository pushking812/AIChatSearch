# code_structure/facades/module_assignment_manager.py

from typing import Dict, List
from code_structure.dialogs.dto import ModuleAssignmentInput, UnknownBlockInfo, KnownModuleInfo, TreeDisplayNode
from code_structure.parsing.core.tree_builder import TreeBuilderNew
from code_structure.models.block import Block
from code_structure.models.registry import BlockRegistry
from code_structure.module_resolution.services.versioned_tree_builder import VersionedTreeBuilder


class ModuleAssignmentManager:
    def __init__(self, block_service):
        """
        Args:
            block_service: BlockService (для доступа к блокам)
            module_service: не используется (оставлен для совместимости)
        """
        self.block_service = block_service
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

        # Получаем известные модули из ModuleIdentifier (через VersionedTreeBuilder)
        # Для этого нужно создать временный builder, чтобы получить модули из уже разрешённых блоков
        builder = VersionedTreeBuilder()
        # Строим дерево, чтобы ModuleIdentifier заполнился
        builder.build_from_blocks(all_blocks)  # это может быть тяжело, но для получения модулей подойдёт
        known_modules_info = []
        for module_name in sorted(builder.module_identifier.get_known_modules()):
            # Игнорируем служебные модули
            if module_name.startswith('__'):
                continue
            # Получаем код модуля из первого блока, который его содержит
            code = self._get_module_code(module_name, all_blocks)
            known_modules_info.append(KnownModuleInfo(
                name=module_name,
                source="",
                code=code
            ))

        # Построение дерева модулей для отображения
        # Передаём пустые корни (так как в диалоге мы отображаем структуру модулей)
        root_dict, _, _, _ = self.tree_builder.build_display_tree({}, local_only)
        module_tree = root_dict

        return ModuleAssignmentInput(
            unknown_blocks=unknown_blocks_info,
            known_modules=known_modules_info,
            module_tree=module_tree
        )

    def apply_assignments(self, assignments: Dict[str, str]):
        # Обновляем module_hint в блоках
        for block_id, module_name in assignments.items():
            block = self.block_service.get_new_block(block_id)
            if block:
                # Создаём новый блок с обновлённым module_hint (так как Block неизменяемый)
                new_block = Block(
                    id=block.id,
                    chat=block.chat,
                    message_pair=block.message_pair,
                    language=block.language,
                    content=block.content,
                    block_idx=block.block_idx,
                    global_index=block.global_index,
                    code_tree=block.code_tree,
                    module_hint=module_name
                )
                BlockRegistry().register(new_block)
        # После назначений нужно перестроить дерево. Это будет сделано при следующем обновлении UI.

    def reset_assignments(self):
        # Сброс module_hint для всех блоков
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
                    module_hint=None
                )
                BlockRegistry().register(new_block)

    def _get_block_description(self, block: Block) -> str:
        # Возвращает описание блока (имя класса/функции или просто "блок кода")
        if block.code_tree is None:
            return "ошибка"
        # Ищем первое определение
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

    def _get_module_code(self, module_name: str, blocks: List[Block]) -> str:
        # Возвращает код модуля (из первого блока с этим module_hint)
        for block in blocks:
            if block.module_hint == module_name and block.code_tree:
                return block.content
        return ""