# code_structure/imports/core/import_analyzer.py

import re
import logging
from typing import List, Optional, Dict

from code_structure.imports.models.import_models import ImportInfo
from code_structure.models.block import Block

from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level=logging.WARNING)


def extract_imports_from_block(content: str, current_module: Optional[str] = None) -> List[ImportInfo]:
    imports = []
    lines = content.splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        line = line.split('#')[0].strip()
        if not line:
            continue
        if line.startswith('import '):
            imports.extend(_handle_import_statement(line[7:], current_module))
        elif line.startswith('from '):
            imports.extend(_handle_from_import_statement(line, current_module))
    return imports


def _handle_import_statement(import_part: str, current_module: Optional[str]) -> List[ImportInfo]:
    result = []
    parts = re.split(r',\s*', import_part)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        alias = None
        if ' as ' in part:
            module, alias = part.split(' as ', 1)
            module = module.strip()
            alias = alias.strip()
        else:
            module = part
        result.append(ImportInfo(
            source_module=current_module or '',
            target_fullname=module,
            target_type='module',
            is_relative=False,
            original_statement=f"import {part}",
            alias=alias
        ))
    return result


def _handle_from_import_statement(line: str, current_module: Optional[str]) -> List[ImportInfo]:
    match = re.match(r'from\s+(.+?)\s+import\s+(.+)', line)
    if not match:
        return []

    from_part = match.group(1).strip()
    import_part = match.group(2).strip()

    is_relative = from_part.startswith('.')
    base_module = None
    if is_relative:
        if current_module is None:
            return []
        base_module = _resolve_relative_import(from_part, current_module)
    else:
        base_module = from_part

    import_part = import_part.split('#')[0].strip()
    names = re.split(r',\s*', import_part)
    result = []
    for name in names:
        name = name.strip()
        if not name:
            continue
        alias = None
        if ' as ' in name:
            name, alias = name.split(' as ', 1)
            name = name.strip()
            alias = alias.strip()

        if is_relative and len(names) == 1 and not '.' in name:
            target_type = 'module'
        else:
            if name and name[0].isupper():
                target_type = 'class'
            else:
                target_type = 'function'

        fullname = f"{base_module}.{name}" if base_module else name
        result.append(ImportInfo(
            source_module=current_module or '',
            target_fullname=fullname,
            target_type=target_type,
            is_relative=is_relative,
            original_statement=line,
            alias=alias
        ))
    return result


def _resolve_relative_import(relative: str, current_module: str) -> str:
    if not current_module:
        return relative
    parts = current_module.split('.')
    count = 0
    rest = relative
    while rest.startswith('.'):
        count += 1
        rest = rest[1:]
    if count > 0:
        if len(parts) > count:
            base_parts = parts[:-count]
        else:
            base_parts = []
    else:
        base_parts = parts[:-1]
    if rest:
        full_parts = base_parts + [rest]
    else:
        full_parts = base_parts
    return '.'.join(full_parts) if full_parts else ''


def build_imported_items(blocks: List[Block]) -> Dict[str, str]:
    result = {}
    for block in blocks:
        if not block.code_tree or not block.content:
            continue
        current_module = block.module_hint if block.module_hint else None
        imports = extract_imports_from_block(block.content, current_module)
        for imp in imports:
            result[imp.target_fullname] = imp.target_type
            if '.' in imp.target_fullname:
                base = imp.target_fullname.rsplit('.', 1)[0]
                if base not in result:
                    result[base] = 'module'
    return result


def build_imported_items_by_module(blocks: List[Block]) -> Dict[str, List[ImportInfo]]:
    result = {}
    for block in blocks:
        if not block.code_tree or not block.content:
            continue
        current_module = block.module_hint if block.module_hint else None
        if not current_module:
            continue
        imports = extract_imports_from_block(block.content, current_module)
        if imports:
            result.setdefault(current_module, []).extend(imports)
    return result


def is_import_block(content: str) -> bool:
    lines = content.splitlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if not line.startswith(('import ', 'from ')):
            return False
    return True