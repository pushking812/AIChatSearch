# code_structure/facades/module_assignment_manager.py

from typing import Dict
from code_structure.module_resolution.services.module_service import ModuleService
from code_structure.block_processing.services.block_service import BlockService
from code_structure.dialogs.dto import ModuleAssignmentInput, UnknownBlockInfo, KnownModuleInfo, TreeDisplayNode
from code_structure.dialogs.dto_builder import DtoBuilder
from code_structure.parsing.core.tree_builder import TreeBuilder


class ModuleAssignmentManager:
    def __init__(self, block_service: BlockService, module_service: ModuleService):
        self.block_service = block_service
        self.module_service = module_service
        self.tree_builder = TreeBuilder()

    def get_module_assignment_input(self, local_only: bool) -> ModuleAssignmentInput:
        unknown_blocks_info = []
        for block in self.module_service.unknown_blocks:
            chat_title = block.metadata.get('chat_title', block.block_id)
            display_name = f"{chat_title} – {self.block_service.get_block_description(block)}"
            unknown_blocks_info.append(UnknownBlockInfo(
                id=block.block_id,
                display_name=display_name,
                content=block.content
            ))

        known_modules_info = []
        for module_name in sorted(self.module_service.get_known_modules()):
            source = self.module_service.get_module_source(module_name, self.block_service.get_all_blocks())
            code = self.module_service.get_module_code(module_name, self.block_service.get_all_blocks()) or ""
            known_modules_info.append(KnownModuleInfo(
                name=module_name,
                source=source,
                code=code
            ))

        root_dict, _ = self.tree_builder.build_display_tree(
            self.module_service.module_containers,
            local_only=local_only
        )
        module_tree = DtoBuilder.tree_dict_to_dto(root_dict) if root_dict else TreeDisplayNode(text="", type="root")

        return ModuleAssignmentInput(
            unknown_blocks=unknown_blocks_info,
            known_modules=known_modules_info,
            module_tree=module_tree
        )

    def apply_assignments(self, assignments: Dict[str, str]):
        all_blocks = self.block_service.get_all_blocks()
        for block in all_blocks:
            if block.block_id in assignments:
                block.module_hint = assignments[block.block_id]
                if block.tree and not block.syntax_error:
                    self.module_service.identifier.collect_from_tree(
                        block.tree, block.module_hint, block_info=block
                    )

        # Перестраиваем контейнеры
        text_blocks_by_pair = self.block_service.get_text_blocks_by_pair()
        full_texts_by_pair = self.block_service.get_full_texts_by_pair()
        containers, unknown_blocks = self.module_service.process_blocks(
            all_blocks,
            text_blocks_by_pair=text_blocks_by_pair,
            full_texts_by_pair=full_texts_by_pair
        )
        self.module_service.module_containers = containers
        self.module_service.unknown_blocks = unknown_blocks

    def reset_assignments(self):
        all_blocks = self.block_service.get_all_blocks()
        self.module_service.reset_assignments(all_blocks)
        text_blocks_by_pair = self.block_service.get_text_blocks_by_pair()
        full_texts_by_pair = self.block_service.get_full_texts_by_pair()
        containers, unknown_blocks = self.module_service.process_blocks(
            all_blocks,
            text_blocks_by_pair=text_blocks_by_pair,
            full_texts_by_pair=full_texts_by_pair
        )
        self.module_service.module_containers = containers
        self.module_service.unknown_blocks = unknown_blocks