# code_structure/module_resolution/core/module_identifier.py

import logging
import re
from typing import Dict, List, Optional, Set, Tuple

from code_structure.models.block import Block
from code_structure.models.code_node import (
    CodeNode, ClassNode, FunctionNode, MethodNode, CodeBlockNode, ImportNode
)
from code_structure.models.versioned_node import SourceRef, VersionInfo
from code_structure.module_resolution.models.identifier_models import (
    ModuleInfo, ClassInfo, MethodInfo, FunctionInfo
)
from code_structure.imports.models.import_models import ImportInfo
from code_structure.utils.logger import get_logger

logger = get_logger(__name__, level=logging.WARNING)


class ModuleIdentifier:
    def __init__(self):
        self._modules: Dict[str, ModuleInfo] = {}
        self._imported: Dict[str, Dict[str, ImportInfo]] = {}

    # ---------- Работа с CodeNode (новые методы) ----------
    def collect_from_code_node(self, code_node: CodeNode, block: Block, module_name: str, class_hint: Optional[str] = None):
        module = self._modules.setdefault(module_name, ModuleInfo(name=module_name))
        self._collect_code_node(code_node, module, block, class_hint)

    def _collect_code_node(self, code_node: CodeNode, module: ModuleInfo, block: Block, class_hint: Optional[str] = None):
        for child in code_node.children:
            if isinstance(child, ClassNode):
                class_name = class_hint if class_hint else child.name
                self._add_class_from_code_node(child, module, class_name, block)
            elif isinstance(child, FunctionNode) and not isinstance(child, MethodNode):
                self._add_function_from_code_node(child, module, class_hint, block)
            elif isinstance(child, MethodNode):
                self._add_method_from_code_node(child, module, class_hint, block)
            else:
                self._collect_code_node(child, module, block, class_hint)

    def _add_class_from_code_node(self, class_node: ClassNode, module: ModuleInfo, class_name: str, block: Block):
        version_info = self._create_version_info_from_code_node(class_node, block)
        if version_info is None:
            return

        if class_name in module.classes:
            existing_class = module.classes[class_name]
            for v in existing_class.versions:
                if v.normalized_code == version_info.normalized_code:
                    for src in version_info.sources:
                        v.add_source(src)
                    return
            existing_class.versions.append(version_info)
        else:
            class_info = ClassInfo(name=class_name)
            class_info.versions.append(version_info)
            module.classes[class_name] = class_info

        for child in class_node.children:
            if isinstance(child, MethodNode):
                self._add_method_from_code_node(child, module, class_name, block)

    def _add_function_from_code_node(self, func_node: FunctionNode, module: ModuleInfo, class_hint: Optional[str], block: Block):
        version_info = self._create_version_info_from_code_node(func_node, block)
        if version_info is None:
            return

        def strip_whitespace(s: str) -> str:
            return re.sub(r'\s', '', s)

        if class_hint:
            if class_hint not in module.classes:
                module.classes[class_hint] = ClassInfo(name=class_hint)
            class_info = module.classes[class_hint]

            if func_node.name in class_info.methods:
                existing_method = class_info.methods[func_node.name]
                # Точное сравнение
                for v in existing_method.versions:
                    if v.normalized_code == version_info.normalized_code:
                        for src in version_info.sources:
                            v.add_source(src)
                        return
                # Сравнение без учёта пробелов
                new_no_ws = strip_whitespace(version_info.normalized_code)
                for v in existing_method.versions:
                    if strip_whitespace(v.normalized_code) == new_no_ws:
                        for src in version_info.sources:
                            v.add_source(src)
                        return
                existing_method.versions.append(version_info)
            else:
                sig = self._extract_signature_from_code_node(func_node)
                method = MethodInfo(name=func_node.name, signature=sig, class_name=class_hint)
                method.versions.append(version_info)
                class_info.methods[func_node.name] = method
        else:
            if func_node.name in module.functions:
                existing_func = module.functions[func_node.name]
                for v in existing_func.versions:
                    if v.normalized_code == version_info.normalized_code:
                        for src in version_info.sources:
                            v.add_source(src)
                        return
                new_no_ws = strip_whitespace(version_info.normalized_code)
                for v in existing_func.versions:
                    if strip_whitespace(v.normalized_code) == new_no_ws:
                        for src in version_info.sources:
                            v.add_source(src)
                        return
                existing_func.versions.append(version_info)
            else:
                sig = self._extract_signature_from_code_node(func_node)
                func = FunctionInfo(name=func_node.name, signature=sig)
                func.versions.append(version_info)
                module.functions[func_node.name] = func

    def _add_method_from_code_node(self, method_node: MethodNode, module: ModuleInfo, class_name: str, block: Block):
        version_info = self._create_version_info_from_code_node(method_node, block)
        if version_info is None:
            return

        def strip_whitespace(s: str) -> str:
            return re.sub(r'\s', '', s)

        if class_name not in module.classes:
            module.classes[class_name] = ClassInfo(name=class_name)
        class_info = module.classes[class_name]

        if method_node.name in class_info.methods:
            existing_method = class_info.methods[method_node.name]
            for v in existing_method.versions:
                if v.normalized_code == version_info.normalized_code:
                    for src in version_info.sources:
                        v.add_source(src)
                    return
            new_no_ws = strip_whitespace(version_info.normalized_code)
            for v in existing_method.versions:
                if strip_whitespace(v.normalized_code) == new_no_ws:
                    for src in version_info.sources:
                        v.add_source(src)
                    return
            existing_method.versions.append(version_info)
        else:
            sig = self._extract_signature_from_code_node(method_node)
            method = MethodInfo(name=method_node.name, signature=sig, class_name=class_name)
            method.versions.append(version_info)
            class_info.methods[method_node.name] = method

    def _create_version_info_from_code_node(self, code_node: CodeNode, block: Block) -> Optional[VersionInfo]:
        norm = code_node.normalized_content()
        src = SourceRef(block.id, code_node.start_line, code_node.end_line, block.timestamp)
        return VersionInfo(norm, [src])

    def _extract_signature_from_code_node(self, node: CodeNode) -> Tuple[bool, List[str]]:
        if node.node_type not in ('function', 'method'):
            return False, []
        signature = node.signature.strip('()')
        if not signature:
            return False, []
        params = []
        for param in signature.split(','):
            param = param.strip()
            if param:
                if ':' in param:
                    param = param.split(':')[0].strip()
                if '=' in param:
                    param = param.split('=')[0].strip()
                param = param.lstrip('*')
                params.append(param)
        has_self = len(params) > 0 and params[0] in ('self', 'cls')
        return has_self, params

    # ---------- Методы работы с импортированными объектами ----------
    def add_imported_item(self, module_name: str, import_info: ImportInfo):
        if import_info.target_type == 'module' and '.' in import_info.target_fullname:
            target_name = import_info.target_fullname.split('.')[-1]
            if target_name and target_name[0].isupper():
                logger.debug(f"Исправлен тип для {target_name}: module -> class")
                import_info.target_type = 'class'

        if module_name not in self._imported:
            self._imported[module_name] = {}
        self._imported[module_name][import_info.target_fullname] = import_info

        target = import_info.target_fullname
        if '.' in target:
            target_module, target_name = target.rsplit('.', 1)
        else:
            target_module = target
            target_name = target

        if import_info.target_type in ('class', 'function') and target_name:
            mod = self._modules.setdefault(target_module, ModuleInfo(name=target_module))
            mod.is_imported = True
            if import_info.target_type == 'class':
                if target_name not in mod.classes:
                    mod.classes[target_name] = ClassInfo(name=target_name)
                    logger.debug(f"Добавлен импортированный класс {target_name} в модуль {target_module}")
            elif import_info.target_type == 'function':
                if target_name not in mod.functions:
                    mod.functions[target_name] = FunctionInfo(name=target_name, signature=(False, []))
                    logger.debug(f"Добавлена импортированная функция {target_name} в модуль {target_module}")

        if import_info.target_type == 'module' and '.' not in target:
            mod = self._modules.setdefault(target, ModuleInfo(name=target))
            mod.is_imported = True

    def add_import_version(self, module_name: str, version_info: VersionInfo):
        module = self._modules.setdefault(module_name, ModuleInfo(name=module_name))
        module.import_versions.append(version_info)

    def add_code_block_version(self, module_name: str, version_info: VersionInfo):
        module = self._modules.setdefault(module_name, ModuleInfo(name=module_name))
        module.code_block_versions.append(version_info)

    # ---------- Методы поиска ----------
    def find_imported_class(self, class_name: str) -> Optional[str]:
        for mod_name, imports in self._imported.items():
            for fullname, info in imports.items():
                if info.target_type == 'class' and fullname.endswith(f".{class_name}"):
                    return fullname.rsplit('.', 1)[0]
        return None

    def find_imported_function(self, func_name: str) -> Optional[str]:
        for mod_name, imports in self._imported.items():
            for fullname, info in imports.items():
                if info.target_type == 'function' and fullname.endswith(f".{func_name}"):
                    return fullname.rsplit('.', 1)[0]
        return None

    def find_module_by_imported_name(self, name: str) -> Optional[str]:
        for mod_name, imports in self._imported.items():
            for fullname, info in imports.items():
                if fullname == name or fullname.endswith('.' + name):
                    return fullname.rsplit('.', 1)[0]
        return None

    def find_module_for_class(self, class_name: str) -> Optional[str]:
        for mod_name, mod in self._modules.items():
            if class_name in mod.classes:
                return mod_name
        return None

    # ---------- Доступ к данным ----------
    def get_module_info(self, module_name: str) -> Optional[ModuleInfo]:
        return self._modules.get(module_name)

    def get_all_module_names(self) -> Set[str]:
        return set(self._modules.keys())

    def get_temp_modules(self) -> List[str]:
        return [name for name in self._modules if name.startswith('temp_')]

    def remove_temp_modules(self):
        to_remove = self.get_temp_modules()
        logger.info(f"Удаление временных модулей: {to_remove}")
        for name in to_remove:
            del self._modules[name]

    def get_known_modules(self) -> Set[str]:
        return self.get_all_module_names()