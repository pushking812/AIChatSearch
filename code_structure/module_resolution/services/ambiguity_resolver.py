# code_structure/module_resolution/services/ambiguity_resolver.py

import logging
from typing import List, Dict, Set
from code_structure.dialogs.dto import AmbiguityInfo
from code_structure.models.block import Block
from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level=logging.DEBUG)

class AmbiguityResolver:
    def __init__(self, candidate_paths: Dict[str, Set[str]]):
        self.candidate_paths = candidate_paths

    def build_filtered_ambiguity_list(self) -> List[AmbiguityInfo]:
        class_identifiers = set()
        for identifier in self.candidate_paths.keys():
            if '.' not in identifier and identifier and identifier[0].isupper():
                class_identifiers.add(identifier)

        filtered_result = []
        for identifier, paths in self.candidate_paths.items():
            is_method = '.' in identifier and identifier.split('.')[0][0].isupper()
            if is_method:
                class_name = identifier.split('.')[0]
                if class_name not in class_identifiers or any(p.startswith('__pending__') for p in paths):
                    filtered_result.append(AmbiguityInfo(name=identifier, candidates=sorted(paths)))
            else:
                filtered_result.append(AmbiguityInfo(name=identifier, candidates=sorted(paths)))
        return filtered_result

    @staticmethod
    def apply_resolved_paths_to_blocks(blocks: List[Block], resolved_paths: Dict[str, str], assign_and_replace):
        logger.info("  === Применение выбранных путей к блокам ===")
        for i, block in enumerate(blocks):
            if block.module_hint and '.' not in block.module_hint:
                if block.module_hint in resolved_paths:
                    new_hint = resolved_paths[block.module_hint]
                    logger.info(f"  Обновляем блок {block.id}: {block.module_hint} -> {new_hint}")
                    assign_and_replace(block, new_hint, "ResolvedPath", blocks, i)