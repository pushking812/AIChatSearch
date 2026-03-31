# code_structure/module_resolution/core/module_identifier.py

import logging
from typing import Dict, List, Optional, Set, Tuple

from code_structure.parsing.models.node import Node
from code_structure.parsing.core.signature_utils import extract_function_signature
from code_structure.module_resolution.models.identifier_models import (
    ModuleInfo, ClassInfo, MethodInfo, FunctionInfo
)
from code_structure.imports.models.import_models import ImportInfo
from code_structure.module_resolution.models.containers import Version
from code_structure.parsing.core.version_comparator import VersionComparator

from code_structure.utils.logger import get_logger
logger = get_logger(__name__, level=logging.WARNING)


class ModuleIdentifier:
    def __init__(self):
        self._modules: Dict[str, ModuleInfo] = {}
        self._imported: Dict[str, Dict[str, ImportInfo]] = {}

    # ---------- Вспомогательные методы ----------
    def _create_version(self, node: Node, block_info=None) -> Optional[Version]:
        if not block_info:
            return None
        return Version(node, block_info.block_id, block_info.global_index, block_info.content,
                      block_info.timestamp, block_info.block_idx)

    def _add_version_to_object(self, versions: List[Version], new_version: Version):
        existing = VersionComparator.find_existing(versions, new_version)
        if existing:
            existing.add_source(*new_version.sources[0])
        else:
            versions.append(new_version)

    def _add_or_update_class(self, module: ModuleInfo, class_name: str, class_node: Node, block_info=None):
        version = self._create_version(class_node, block_info)
        if version is None:
            return

        if class_name in module.classes:
            existing_class = module.classes[class_name]
            self._add_version_to_object(existing_class.versions, version)
        else:
            class_info = ClassInfo(name=class_name)
            class_info.versions.append(version)
            module.classes[class_name] = class_info

        for method_node in class_node.children:
            if method_node.node_type == "method":
                self._add_or_update_callable(module, method_node.name, method_node, block_info, class_name=class_name)

    def _add_or_update_callable(self, module: ModuleInfo, name: str, node: Node, block_info=None,
                                class_name: Optional[str] = None):
        version = self._create_version(node, block_info)
        if version is None:
            return

        if class_name:
            if class_name not in module.classes:
                module.classes[class_name] = ClassInfo(name=class_name)
            class_info = module.classes[class_name]

            if name in class_info.methods:
                existing_method = class_info.methods[name]
                self._add_version_to_object(existing_method.versions, version)
            else:
                sig = extract_function_signature(node)
                method = MethodInfo(name=name, signature=sig, class_name=class_name)
                method.versions.append(version)
                class_info.methods[name] = method
        else:
            sig = extract_function_signature(node)
            if name in module.functions:
                existing_func = module.functions[name]
                self._add_version_to_object(existing_func.versions, version)
            else:
                func = FunctionInfo(name=name, signature=sig)
                func.versions.append(version)
                module.functions[name] = func

    # ---------- Публичные методы ----------
    def collect_from_tree(self, node: Node, module_name: str, class_hint: Optional[str] = None, block_info=None):
        module = self._modules.setdefault(module_name, ModuleInfo(name=module_name))
        self._collect_node(node, module, class_hint, block_info)
        if block_info and not block_info.module_hint:
            block_info.module_hint = module_name
            logger.debug(f"[IDENTIFIER] Блоку {block_info.block_id} назначен модуль {module_name}")

    def _collect_node(self, node: Node, module: ModuleInfo, class_hint: Optional[str] = None, block_info=None):
        for child in node.children:
            if child.node_type == "class":
                class_name = class_hint if class_hint else child.name
                self._add_class(child, module, class_name, block_info)
            elif child.node_type == "function":
                self._add_function(child, module, class_hint, block_info)
            elif child.node_type == "method":
                self._add_method_as_function(child, module, class_hint, block_info)
            else:
                self._collect_node(child, module, class_hint, block_info)

    def _add_class(self, class_node: Node, module: ModuleInfo, class_name: str, block_info):
        self._add_or_update_class(module, class_name, class_node, block_info)

    def _add_function(self, func_node: Node, module: ModuleInfo, class_hint: Optional[str], block_info):
        self._add_or_update_callable(module, func_node.name, func_node, block_info, class_name=class_hint)

    def _add_method_as_function(self, method_node: Node, module: ModuleInfo, class_hint: Optional[str], block_info):
        self._add_or_update_callable(module, method_node.name, method_node, block_info, class_name=class_hint)

    # ---------- Методы работы с импортированными объектами ----------
    def add_imported_item(self, module_name: str, import_info: ImportInfo):
        """Добавляет информацию об импортированном объекте."""
        if module_name not in self._imported:
            self._imported[module_name] = {}
        self._imported[module_name][import_info.target_fullname] = import_info

        # Принудительное исправление типа для имён с заглавной
        target_name = import_info.target_fullname.split('.')[-1]
        if import_info.target_type == 'module' and target_name and target_name[0].isupper():
            logger.debug(f"Исправлен тип для {target_name}: module -> class")
            import_info.target_type = 'class'

        target = import_info.target_fullname
        # Если импортируется модуль (type='module'), то создаём запись в _modules
        if import_info.target_type == 'module':
            # Импорт модуля: target может быть именем модуля (например, 'constants')
            # или полным путём (например, 'deepseek.gui_components.constants')
            mod = self._modules.setdefault(target, ModuleInfo(name=target))
            mod.is_imported = True
            logger.debug(f"Добавлен импортированный модуль {target} из {module_name}")
            return

        # Иначе это импорт класса или функции
        if '.' in target:
            target_module, target_name = target.rsplit('.', 1)
        else:
            target_module = target
            target_name = target

        # Добавляем запись в _modules для модуля, содержащего класс/функцию
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

    # ---------- Методы поиска (добавлены для совместимости с новым кодом) ----------
    def find_imported_class(self, class_name: str) -> Optional[str]:
        logger.debug(f"find_imported_class: searching for {class_name}")
        for mod_name, imports in self._imported.items():
            for fullname, info in imports.items():
                if info.target_type == 'class' and fullname.endswith(f".{class_name}"):
                    logger.debug(f"  found: {fullname} in {mod_name}")
                    return fullname.rsplit('.', 1)[0]
        logger.debug(f"find_imported_class: not found for {class_name}. Current imports:")
        for mod_name, imports in self._imported.items():
            for fullname, info in imports.items():
                logger.debug(f"  {fullname} ({info.target_type}) from {mod_name}")
        return None

    def find_imported_function(self, func_name: str) -> Optional[str]:
        """Ищет модуль, в котором объявлена импортированная функция."""
        for mod_name, imports in self._imported.items():
            for fullname, info in imports.items():
                if info.target_type == 'function' and fullname.endswith(f".{func_name}"):
                    return fullname.rsplit('.', 1)[0]
        return None

    def find_module_by_imported_name(self, name: str) -> Optional[str]:
        """Ищет модуль, из которого импортирован объект с заданным именем."""
        for mod_name, imports in self._imported.items():
            for fullname, info in imports.items():
                if fullname == name or fullname.endswith('.' + name):
                    return fullname.rsplit('.', 1)[0]
        return None

    def find_module_for_class(self, class_name: str) -> Optional[str]:
        logger.debug(f"find_module_for_class: searching for {class_name}")
        for mod_name, mod in self._modules.items():
            if class_name in mod.classes:
                logger.debug(f"find_module_for_class: found in {mod_name}")
                return mod_name
        logger.debug(f"find_module_for_class: not found for {class_name}")
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