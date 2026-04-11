# code_structure/module_resolution/services/versioned_tree_builder.py

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import replace
from code_structure.models.block import Block
from code_structure.models.registry import BlockRegistry
from code_structure.dialogs.dto import AmbiguityInfo
from code_structure.utils.helpers import extract_module_hint
from code_structure.utils.logger import get_logger

from .candidate_collector import CandidateCollector
from .ambiguity_resolver import AmbiguityResolver
from .identifier_tree_builder import IdentifierTreeBuilder
from .block_resolver import BlockResolver
from .versioned_tree_assembler import VersionedTreeAssembler
from .tree_utils import extract_method_names

logger = get_logger(__name__, level=logging.DEBUG)

class VersionedTreeBuilder:
    def __init__(self):
        self.collector = CandidateCollector()
        self.tree_builder = IdentifierTreeBuilder()

    def _assign_and_replace(self, block: Block, module_hint: str, strategy: str, blocks: List[Block], idx: int) -> Block:
        new_block = replace(block, module_hint=module_hint, assignment_strategy=strategy)
        BlockRegistry().register(new_block)
        blocks[idx] = new_block
        return new_block

    def _apply_immediate_hints(self, blocks: List[Block], text_blocks_by_pair: Dict[str, Dict[int, str]]):
        # 1. Комментарии
        for i, block in enumerate(blocks):
            if block.module_hint:
                continue
            hint = extract_module_hint(block)
            if hint:
                self._assign_and_replace(block, hint, "CommentHint", blocks, i)
                continue

        # 2. Текстовые подсказки (пути .py)
        for i, block in enumerate(blocks):
            if block.module_hint:
                continue
            pair_index = block.pair_index
            if pair_index not in text_blocks_by_pair:
                continue
            prev_text = CandidateCollector._get_previous_text_block(block.block_idx, text_blocks_by_pair[pair_index])
            if not prev_text:
                continue
            module_path = CandidateCollector._extract_module_path_from_text(prev_text)
            if module_path:
                new_block = self._assign_and_replace(block, module_path, "TextHint", blocks, i)
                if new_block.code_tree:
                    methods = extract_method_names(new_block.code_tree)
                    for method_name in methods:
                        identifier = f"{module_path.split('.')[-1]}.{method_name}"
                        full_path = f"{module_path}.{method_name}"
                        self.collector.register_candidate(identifier, full_path, node_type='method')
                        logger.debug(f"  Добавлен кандидат от пути .py: {identifier} -> {full_path}")
                continue

            # 3. Упоминание класса
            class_match = re.search(r'класс[еауы]?\s+[`\'"]?([A-Za-z_]+)[`\'"]?', prev_text, re.IGNORECASE)
            if class_match:
                class_name = class_match.group(1)
                self.collector.class_hints_by_block[block.id] = class_name
                if block.code_tree:
                    methods = extract_method_names(block.code_tree)
                    for method_name in methods:
                        identifier = f"{class_name}.{method_name}"
                        temp_path = f"__pending__.{class_name}.{method_name}"
                        self.collector.register_candidate(identifier, temp_path, node_type='method')
                        self.collector.pending_method_hints.append((class_name, method_name, block.id))
                        logger.debug(f"  Добавлен временный кандидат от упоминания класса: {identifier} -> {temp_path}")

    def build_from_blocks(
        self,
        blocks: List[Block],
        text_blocks_by_pair: Dict[str, Dict[int, str]] = None,
        full_texts_by_pair: Dict[str, str] = None,
        resolved_ambiguities: Optional[Dict[str, str]] = None
    ) -> Tuple[Dict, List[Block], List[AmbiguityInfo]]:
        text_blocks_by_pair = text_blocks_by_pair or {}
        self.collector.collect_explicit_candidates(blocks, text_blocks_by_pair)
        self._apply_immediate_hints(blocks, text_blocks_by_pair)
        self.collector.collect_from_resolved_blocks(blocks)

        if resolved_ambiguities is None:
            amb_resolver = AmbiguityResolver(self.collector.candidate_paths)
            ambiguities = amb_resolver.build_filtered_ambiguity_list()
            if ambiguities:
                return {}, [], ambiguities
            resolved_ambiguities = {}

        self.collector.resolved_paths.update(resolved_ambiguities)
        AmbiguityResolver.apply_resolved_paths_to_blocks(blocks, self.collector.resolved_paths, self._assign_and_replace)

        self.tree_builder.build_from_resolved(self.collector.resolved_paths)
        self.collector.node_type_map.update(self.tree_builder.node_type_map)

        block_resolver = BlockResolver(self.collector.resolved_paths, self.collector.class_hints_by_block)
        block_resolver.resolve_blocks(blocks, self._assign_and_replace)
        block_resolver.resolve_orphan_methods(blocks, self.collector.orphan_methods, self._assign_and_replace)
        block_resolver.resolve_pending_method_hints(
            self.collector.pending_method_hints,
            self.collector.candidate_paths,
            blocks,
            self._assign_and_replace
        )

        # Повторное построение дерева и разрешение
        self.tree_builder.build_from_resolved(self.collector.resolved_paths)
        self.collector.node_type_map.update(self.tree_builder.node_type_map)
        block_resolver.resolve_blocks(blocks, self._assign_and_replace)

        # Сборка сводного дерева
        assembler = VersionedTreeAssembler(
            self.collector.resolved_paths,
            self.collector.node_type_map,
            self.collector.imported_paths
        )
        versioned_roots = assembler.build_versioned_tree_from_blocks(blocks)

        unknown_blocks = [b for b in blocks if b.module_hint is None and b.code_tree is not None]
        return versioned_roots, unknown_blocks, []