# code_structure/module_resolution/services/block_resolver.py
import logging
from typing import List, Dict, Set, Tuple, Optional
from code_structure.models.block import Block
from code_structure.models.code_node import FunctionNode, MethodNode
from .tree_utils import extract_class_names, extract_function_names, extract_method_names
from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level=logging.DEBUG)


class BlockResolver:
    def __init__(self, resolved_paths: Dict[str, str], class_hints_by_block: Dict[str, str]):
        self.resolved_paths = resolved_paths
        self.class_hints_by_block = class_hints_by_block

    def resolve_blocks(self, blocks: List[Block], assign_and_replace):
        for i, block in enumerate(blocks):
            if block.module_hint is not None:
                continue
            if not block.code_tree:
                continue

            if block.id in self.class_hints_by_block:
                class_name = self.class_hints_by_block[block.id]
                if class_name in self.resolved_paths:
                    class_full_path = self.resolved_paths[class_name]
                    module_path = '.'.join(class_full_path.split('.')[:-1])
                    assign_and_replace(block, module_path, "TextHint", blocks, i)
                    continue

            classes = extract_class_names(block.code_tree)
            functions = extract_function_names(block.code_tree)
            methods = extract_method_names(block.code_tree)

            module_candidates = set()
            class_candidates = set()

            for class_name in classes:
                if class_name in self.resolved_paths:
                    full_path = self.resolved_paths[class_name]
                    module_path = '.'.join(full_path.split('.')[:-1])
                    module_candidates.add(module_path)
                    class_candidates.add(full_path)

            if module_candidates:
                chosen = next(iter(module_candidates))
                assign_and_replace(block, chosen, "TreeResolution", blocks, i)
                continue

            for func_name in functions:
                for ident, full_path in self.resolved_paths.items():
                    if ident.endswith(f'.{func_name}'):
                        module_path = '.'.join(full_path.split('.')[:-1])
                        module_candidates.add(module_path)
                        break

            if module_candidates:
                chosen = next(iter(module_candidates))
                assign_and_replace(block, chosen, "TreeResolution", blocks, i)
                continue

            for method_name in methods:
                for ident, full_path in self.resolved_paths.items():
                    if ident.endswith(f'.{method_name}'):
                        class_path = '.'.join(full_path.split('.')[:-1])
                        class_candidates.add(class_path)
                        break

            if class_candidates:
                chosen = next(iter(class_candidates))
                assign_and_replace(block, chosen, "TreeResolution", blocks, i)
                continue

    def resolve_orphan_methods(self, blocks: List[Block], orphan_methods: List[Tuple[Block, FunctionNode, str]], assign_and_replace):
        logger.info("  === ФАЗА 7: Разрешение отложенных методов-сирот ===")
        resolved_classes = {}
        for identifier, full_path in self.resolved_paths.items():
            if '.' not in identifier and identifier and identifier[0].isupper():
                resolved_classes[identifier] = full_path
        logger.info(f"  Найдено разрешённых классов: {len(resolved_classes)}")
        if not orphan_methods:
            logger.info("  Нет отложенных методов-сирот.")
            return
        logger.info(f"  Всего отложенных методов-сирот: {len(orphan_methods)}")

        for block, func_node, base_path in orphan_methods:
            method_name = func_node.name
            method_module = base_path.split('.')[-1] if base_path else ''
            best_match = None
            best_score = 0
            for class_name, class_full_path in resolved_classes.items():
                parts = class_full_path.split('.')
                class_module = parts[-2] if len(parts) >= 2 else ''
                score = 0
                if class_module == method_module:
                    score += 10
                method_identifier = f"{class_name}.{method_name}"
                if method_identifier in self.resolved_paths:
                    score += 5
                if self._is_class_in_block(class_name, block):
                    score += 3
                if score > best_score:
                    best_score = score
                    best_match = (class_name, class_full_path)

            if best_match and best_score >= 10:
                class_name, class_full_path = best_match
                full_path = f"{class_full_path}.{method_name}"
                identifier = f"{class_name}.{method_name}"
                self.resolved_paths[identifier] = full_path

                # Удаляем старый путь функции (по полному пути)
                old_path = f"{base_path}.{method_name}"
                keys_to_remove = [k for k, v in self.resolved_paths.items() if v == old_path]
                for k in keys_to_remove:
                    del self.resolved_paths[k]
                    logger.debug(f"  Удалён старый путь функции: {k} -> {old_path}")

                logger.info(f"  Метод-сирота '{method_name}' привязан к классу '{class_name}' -> {full_path}")
                if block.module_hint is None:
                    module_path = '.'.join(class_full_path.split('.')[:-1])
                    try:
                        idx = blocks.index(block)
                        assign_and_replace(block, module_path, "OrphanMethodResolution", blocks, idx)
                    except ValueError:
                        logger.warning(f"Блок {block.id} не найден в списке")
            else:
                logger.debug(f"  Метод-сирота '{method_name}' не привязан к классу, остаётся функцией")

    def resolve_pending_method_hints(self, pending_hints: List[Tuple[str, str, str]], candidate_paths: Dict[str, Set[str]], blocks: List[Block], assign_and_replace):
        logger.info("  === Разрешение отложенных подсказок методов ===")
        for class_name, method_name, block_id in pending_hints:
            if class_name in self.resolved_paths:
                class_full_path = self.resolved_paths[class_name]
                full_path = f"{class_full_path}.{method_name}"
                identifier = f"{class_name}.{method_name}"
                self.resolved_paths[identifier] = full_path
                if identifier in candidate_paths:
                    candidate_paths[identifier].discard(f"__pending__.{class_name}.{method_name}")
                    candidate_paths[identifier].add(full_path)
                else:
                    candidate_paths[identifier] = {full_path}
                logger.info(f"  Подсказка метода: {identifier} -> {full_path}")

                # Удаляем старый путь функции, если он есть
                for i, blk in enumerate(blocks):
                    if blk.id == block_id:
                        if blk.module_hint:
                            old_path = f"{blk.module_hint}.{method_name}"
                            keys_to_remove = [k for k, v in self.resolved_paths.items() if v == old_path]
                            for k in keys_to_remove:
                                del self.resolved_paths[k]
                                logger.debug(f"  Удалён старый путь функции: {k} -> {old_path}")
                        if blk.module_hint is None:
                            module_path = '.'.join(class_full_path.split('.')[:-1])
                            assign_and_replace(blk, module_path, "PendingMethodHint", blocks, i)
                            logger.info(f"    Назначен module_hint {module_path} блоку {blk.id}")
                        break
            else:
                logger.debug(f"  Класс {class_name} ещё не разрешён, временный путь для {method_name} остаётся")

    @staticmethod
    def _is_class_in_block(class_name: str, block: Block) -> bool:
        if not block.code_tree:
            return False
        return class_name in extract_class_names(block.code_tree)