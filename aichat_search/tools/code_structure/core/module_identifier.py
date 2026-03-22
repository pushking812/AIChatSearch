# aichat_search/tools/code_structure/core/module_identifier.py

from typing import Dict, List, Optional, Set, Tuple
import logging
from aichat_search.tools.code_structure.models.node import Node
from aichat_search.tools.code_structure.core.signature_utils import extract_function_signature
from aichat_search.tools.code_structure.models.identifier_models import (
    ModuleInfo, ClassInfo, MethodInfo, FunctionInfo, Signature
)
from aichat_search.tools.code_structure.models.import_models import ImportInfo

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ModuleIdentifier:
    def __init__(self):
        self._modules: Dict[str, ModuleInfo] = {}
        self._imported: Dict[str, Dict[str, ImportInfo]] = {}  # module_name -> {fullname: ImportInfo}

    # ---------- Сбор данных ----------
    def collect_from_tree(self, node: Node, module_name: str):
        module = self._modules.setdefault(module_name, ModuleInfo(name=module_name))
        self._collect_node(node, module)

    def _collect_node(self, node: Node, module: ModuleInfo):
        for child in node.children:
            if child.node_type == "class":
                self._add_class(child, module)
            elif child.node_type == "function":
                self._add_function(child, module)
            elif child.node_type == "method":
                self._add_method_as_function(child, module)
            else:
                self._collect_node(child, module)

    def _add_class(self, class_node: Node, module: ModuleInfo):
        class_info = ClassInfo(name=class_node.name)
        for method_node in class_node.children:
            if method_node.node_type == "method":
                sig = extract_function_signature(method_node)
                method = MethodInfo(
                    name=method_node.name,
                    signature=sig,
                    class_name=class_node.name
                )
                if method.name in class_info.methods:
                    existing = class_info.methods[method.name]
                    if existing.signature == sig:
                        logger.debug(f"Метод {class_node.name}.{method.name} с такой сигнатурой уже существует, пропускаем")
                        continue
                class_info.methods[method.name] = method
        module.classes[class_info.name] = class_info

    def _add_function(self, func_node: Node, module: ModuleInfo):
        sig = extract_function_signature(func_node)
        func = FunctionInfo(name=func_node.name, signature=sig)
        if func.name in module.functions:
            existing = module.functions[func.name]
            if existing.signature == sig:
                logger.debug(f"Функция {func.name} с такой сигнатурой уже существует, пропускаем")
                return
        module.functions[func.name] = func

    def _add_method_as_function(self, method_node: Node, module: ModuleInfo):
        sig = extract_function_signature(method_node)
        func = FunctionInfo(name=method_node.name, signature=sig)
        if func.name in module.functions:
            existing = module.functions[func.name]
            if existing.signature == sig:
                logger.debug(f"Метод {method_node.name} вне класса с такой сигнатурой уже существует, пропускаем")
                return
        module.functions[func.name] = func

    # ---------- Импортированные объекты ----------
    def add_imported_item(self, module_name: str, import_info: ImportInfo):
        if module_name not in self._imported:
            self._imported[module_name] = {}
        self._imported[module_name][import_info.target_fullname] = import_info

    def get_imported_info(self, module_name: str) -> Optional[Dict[str, ImportInfo]]:
        return self._imported.get(module_name)

    def find_imported_class(self, class_name: str) -> Optional[str]:
        for mod_name, imports in self._imported.items():
            for fullname, info in imports.items():
                if info.target_type == 'class' and fullname.endswith(f".{class_name}"):
                    return mod_name
        return None

    def find_imported_function(self, func_name: str) -> Optional[str]:
        for mod_name, imports in self._imported.items():
            for fullname, info in imports.items():
                if info.target_type == 'function' and fullname.endswith(f".{func_name}"):
                    return mod_name
        return None

    def find_module_by_imported_name(self, name: str) -> Optional[str]:
        """
        Ищет модуль, который содержит импортированный объект с именем name.
        name может быть полным (myapp.models.User) или простым (User).
        """
        for mod_name, imports in self._imported.items():
            for fullname, info in imports.items():
                if fullname == name or fullname.endswith('.' + name):
                    return mod_name
        return None

    # ---------- Методы поиска ----------
    def find_module_for_class(self, class_name: str) -> Optional[str]:
        for mod_name, mod in self._modules.items():
            if class_name in mod.classes:
                return mod_name
        return None

    def find_module_for_method(self, method_name: str, signature: Signature) -> Optional[str]:
        for mod_name, mod in self._modules.items():
            for cls in mod.classes.values():
                method = cls.methods.get(method_name)
                if method and method.signature == signature:
                    return mod_name
        return None

    def find_module_for_method_with_class(self, method_name: str, signature: Signature, class_name: Optional[str] = None) -> Optional[str]:
        for mod_name, mod in self._modules.items():
            for cls_name, cls in mod.classes.items():
                if class_name and cls_name != class_name:
                    continue
                method = cls.methods.get(method_name)
                if method and method.signature == signature:
                    return mod_name
        return None

    def find_module_for_function(self, func_name: str, signature: Signature) -> Optional[str]:
        for mod_name, mod in self._modules.items():
            func = mod.functions.get(func_name)
            if func and func.signature == signature:
                return mod_name
        return None

    def find_modules_by_method_name(self, method_name: str) -> List[Tuple[str, str]]:
        results = []
        for mod_name, mod in self._modules.items():
            for cls_name, cls in mod.classes.values():
                if method_name in cls.methods:
                    results.append((mod_name, cls_name))
        return results

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

    def merge_temp_module(self, temp_name: str, target_name: str) -> bool:
        if temp_name not in self._modules or target_name not in self._modules:
            logger.error(f"Не удалось найти модули: {temp_name} -> {target_name}")
            return False
        temp = self._modules[temp_name]
        target = self._modules[target_name]

        for class_name, class_info in temp.classes.items():
            if class_name not in target.classes:
                target.classes[class_name] = ClassInfo(name=class_name)
            target_class = target.classes[class_name]
            for method_name, method_info in class_info.methods.items():
                if method_name in target_class.methods:
                    existing = target_class.methods[method_name]
                    if existing.signature == method_info.signature:
                        logger.debug(f"Метод {class_name}.{method_name} уже существует, пропускаем")
                        continue
                target_class.methods[method_name] = method_info

        for func_name, func_info in temp.functions.items():
            if func_name in target.functions:
                existing = target.functions[func_name]
                if existing.signature == func_info.signature:
                    logger.debug(f"Функция {func_name} уже существует, пропускаем")
                    continue
            target.functions[func_name] = func_info

        del self._modules[temp_name]
        logger.info(f"Модуль {temp_name} успешно объединён в {target_name}")
        return True

    # ---------- Обратная совместимость ----------
    def get_known_modules(self) -> Set[str]:
        return self.get_all_module_names()