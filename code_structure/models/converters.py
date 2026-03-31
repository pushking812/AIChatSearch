# code_structure/models/converters.py

from typing import Optional

from code_structure.models.block import Block
from code_structure.models.code_node import (
    CodeNode, ModuleNode, ClassNode, FunctionNode, MethodNode,
    CodeBlockNode, CommentNode, ImportNode
)
from code_structure.parsing.models.node import (
    Node, ModuleNode as OldModuleNode, ClassNode as OldClassNode,
    FunctionNode as OldFunctionNode, MethodNode as OldMethodNode,
    CodeBlockNode as OldCodeBlockNode
)
from code_structure.module_resolution.models.block_info import MessageBlockInfo
from aichat_search.services.block_parser import MessageBlock


def code_node_to_old_node(code_node: CodeNode, class_hint: Optional[str] = None) -> Node:
    if isinstance(code_node, ModuleNode):
        old_node = OldModuleNode(name=code_node.name, lineno_start=code_node.start_line, lineno_end=code_node.end_line)
    elif isinstance(code_node, ClassNode):
        old_node = OldClassNode(name=code_node.name, bases=code_node.bases, lineno_start=code_node.start_line, lineno_end=code_node.end_line)
    elif isinstance(code_node, FunctionNode) and not isinstance(code_node, MethodNode):
        if class_hint:
            old_node = OldMethodNode(name=code_node.name, args=code_node.signature.strip('()'),
                                     lineno_start=code_node.start_line, lineno_end=code_node.end_line)
        else:
            old_node = OldFunctionNode(name=code_node.name, args=code_node.signature.strip('()'),
                                       lineno_start=code_node.start_line, lineno_end=code_node.end_line)
    elif isinstance(code_node, MethodNode):
        old_node = OldMethodNode(name=code_node.name, args=code_node.signature.strip('()'),
                                 lineno_start=code_node.start_line, lineno_end=code_node.end_line)
    elif isinstance(code_node, CodeBlockNode):
        old_node = OldCodeBlockNode(name=code_node.name, line_range=f"{code_node.start_line}-{code_node.end_line}",
                                    lineno_start=code_node.start_line, lineno_end=code_node.end_line)
    else:
        old_node = Node(name=code_node.name, node_type=code_node.node_type,
                        lineno_start=code_node.start_line, lineno_end=code_node.end_line)
    for child in code_node.children:
        old_node.add_child(code_node_to_old_node(child, None))
    return old_node


def block_to_old_block_info(block: Block) -> MessageBlockInfo:
    msg_block = MessageBlock(
        language=block.language,
        content=block.content,
        index=block.block_idx
    )
    old = MessageBlockInfo(
        block=msg_block,
        language=block.language,
        content=block.content,
        block_id=block.id,
        global_index=block.global_index,
        module_hint=block.module_hint,
        metadata={
            'chat_id': block.chat.id,
            'chat_title': block.chat.title,
            'pair_index': block.pair_index
        },
        timestamp=block.timestamp,
        block_idx=block.block_idx
    )
    if block.code_tree:
        old.tree = code_node_to_old_node(block.code_tree, None)
    return old