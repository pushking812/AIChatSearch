# code_structure/module_resolution/services/candidate_collector.

import re
import logging
from typing import List, Dict, Set, Tuple, Optional
from code_structure.models.block import Block
from code_structure.models.code_node import CodeNode, ClassNode, FunctionNode, MethodNode, ImportNode
from code_structure.imports.core.import_analyzer import extract_imports_from_block
from code_structure.utils.helpers import extract_module_hint
from .tree_utils import has_self_parameter, find_parent_class, make_identifier_from_path
from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level=logging.DEBUG)

class CandidateCollector:
    def __init__(self):
        self.candidate_paths: Dict[str, Set[str]] = {}
        self.resolved_paths: Dict[str, str] = {}
        self.node_type_map: Dict[str, str] = {}
        self.imported_paths: Set[str] = set()
        self.orphan_methods: List[Tuple[Block, FunctionNode, str]] = []
        self.pending_method_hints: List[Tuple[str, str, str]] = []
        self.class_hints_by_block: Dict[str, str] = {}

    def register_candidate(self, identifier: str, full_path: str, node_type: str):
        if identifier not in self.candidate_paths:
            self.candidate_paths[identifier] = set()
        self.candidate_paths[identifier].add(full_path)

    def register_candidate_from_path(self, full_path: str, node_type: str = 'module'):
        identifier = make_identifier_from_path(full_path, node_type)
        if identifier:
            self.register_candidate(identifier, full_path, node_type)

    def collect_explicit_candidates(self, blocks: List[Block], text_blocks_by_pair: Dict[str, Dict[int, str]]):
        logger.info("  === ФАЗА 1: Сбор явных кандидатов ===")
        for block in blocks:
            hint = extract_module_hint(block)
            if hint:
                self.register_candidate_from_path(hint, node_type='module')

        for block in blocks:
            if block.module_hint:
                continue
            pair_index = block.pair_index
            if pair_index not in text_blocks_by_pair:
                continue
            prev_text = self._get_previous_text_block(block.block_idx, text_blocks_by_pair[pair_index])
            if prev_text:
                path_match = self._extract_module_path_from_text(prev_text)
                if path_match:
                    self.register_candidate_from_path(path_match, node_type='module')
                class_match = re.search(r'класс[еауы]?\s+[`\'"]?([A-Za-z_]+)[`\'"]?', prev_text, re.IGNORECASE)
                if class_match:
                    self.class_hints_by_block[block.id] = class_match.group(1)

        for block in blocks:
            if block.code_tree:
                imports = extract_imports_from_block(block.content, block.module_hint)
                for imp in imports:
                    if not imp.is_relative:
                        self.imported_paths.add(imp.target_fullname)
                        self.register_candidate_from_path(imp.target_fullname, node_type='module')
                        if imp.target_type in ('class', 'function'):
                            identifier = make_identifier_from_path(imp.target_fullname, imp.target_type)
                            if identifier:
                                self.register_candidate(identifier, imp.target_fullname, imp.target_type)
        logger.info(f"  Всего идентификаторов после фазы 1: {len(self.candidate_paths)}")

    def collect_from_resolved_blocks(self, blocks: List[Block]):
        logger.info("  === ФАЗА 3: Сбор кандидатов из размеченных блоков ===")
        before = len(self.candidate_paths)
        for block in blocks:
            if block.module_hint and block.code_tree:
                self._collect_identifiers_from_code_node(block.code_tree, block.module_hint, block)
        after = len(self.candidate_paths)
        logger.info(f"  Добавлено кандидатов: {after - before}, всего: {after}")

    def _collect_identifiers_from_code_node(self, node: CodeNode, base_path: str, block: Block):
        if isinstance(node, ClassNode):
            full_path = f"{base_path}.{node.name}"
            self.register_candidate_from_path(full_path, node_type='class')
            for child in node.children:
                self._collect_identifiers_from_code_node(child, full_path, block)

        elif isinstance(node, FunctionNode) and not isinstance(node, MethodNode):
            parent_class = find_parent_class(node)
            if has_self_parameter(node):
                if parent_class:
                    class_full_path = f"{base_path}.{parent_class.name}"
                    full_path = f"{class_full_path}.{node.name}"
                    self.register_candidate_from_path(full_path, node_type='method')
                    self.register_candidate_from_path(class_full_path, node_type='class')
                    logger.debug(f"  Метод {node.name} внутри класса {parent_class.name} -> {full_path}")
                else:
                    full_path = f"{base_path}.{node.name}"
                    identifier = make_identifier_from_path(full_path, 'function')
                    if identifier:
                        self.register_candidate(identifier, full_path, node_type='function')
                    self.orphan_methods.append((block, node, base_path))
                    logger.info(f"  Метод-сирота (FunctionNode) добавлен: {node.name} из {base_path}")
            else:
                full_path = f"{base_path}.{node.name}"
                self.register_candidate_from_path(full_path, node_type='function')
                logger.debug(f"  Функция {node.name} (без self/cls) -> {full_path}")

        elif isinstance(node, MethodNode):
            # Пропускаем MethodNode, родитель которого не является классом (ошибочный дубликат)
            if not isinstance(node.parent, ClassNode):
                logger.debug(f"  Пропускаем MethodNode {node.name} (родитель {type(node.parent).__name__})")
                return

            parent_class = find_parent_class(node)
            if parent_class:
                full_path = f"{base_path}.{node.name}"
                self.register_candidate_from_path(full_path, node_type='method')
                logger.debug(f"  MethodNode {node.name} внутри класса {parent_class.name} -> {full_path}")
            else:
                full_path = f"{base_path}.{node.name}"
                identifier = make_identifier_from_path(full_path, 'function')
                if identifier:
                    self.register_candidate(identifier, full_path, node_type='function')
                self.orphan_methods.append((block, node, base_path))
                logger.info(f"  MethodNode-сирота добавлен: {node.name} из {base_path}")

        elif isinstance(node, ImportNode):
            imports = extract_imports_from_block(node.statement, base_path)
            for imp in imports:
                abs_path = imp.target_fullname
                if not abs_path:
                    continue
                self.imported_paths.add(abs_path)
                self.register_candidate_from_path(abs_path, node_type=imp.target_type)
                identifier = abs_path.split('.')[-1]
                if identifier not in self.resolved_paths:
                    self.resolved_paths[identifier] = abs_path
                    self.node_type_map[abs_path] = imp.target_type
        else:
            for child in node.children:
                self._collect_identifiers_from_code_node(child, base_path, block)

    @staticmethod
    def _get_previous_text_block(block_idx: int, text_blocks: Dict[int, str]) -> Optional[str]:
        prev_idx = None
        for idx in text_blocks:
            if idx < block_idx and (prev_idx is None or idx > prev_idx):
                prev_idx = idx
        return text_blocks.get(prev_idx) if prev_idx is not None else None

    @staticmethod
    def _extract_module_path_from_text(text: str) -> Optional[str]:
        pattern = r"[`'\"]([a-z_]+(?:[\/.\\][a-z_]+)*\.py)[`'\"]"
        matches = re.findall(pattern, text)
        for match in matches:
            module_path = match.replace('/', '.').replace('\\', '.')
            if module_path.endswith('.py'):
                module_path = module_path[:-3]
            return module_path
        return None