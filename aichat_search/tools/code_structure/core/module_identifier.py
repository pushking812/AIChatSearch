# aichat_search/tools/code_structure/core/module_identifier.py

from typing import Dict, List, Optional, Set, Tuple
import logging
from aichat_search.tools.code_structure.models.node import Node
from aichat_search.tools.code_structure.core.signature_utils import extract_function_signature
from aichat_search.tools.code_structure.models.identifier_models import (
    ModuleInfo, ClassInfo, MethodInfo, FunctionInfo, Signature
)
from aichat_search.tools.code_structure.models.import_models import ImportInfo
from aichat_search.tools.code_structure.models.containers import Version
from aichat_search.tools.code_structure.core.version_comparator import VersionComparator

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ModuleIdentifier:
    def __init__(self):
        self._modules: Dict[str, ModuleInfo] = {}
        self._imported: Dict[str, Dict[str, ImportInfo]] = {}

    # ---------- Сбор данных ----------
    def collect_from_tree(self, node: Node, module_name: str, class_hint: Optional[str] = None, block_info=None):
        module = self._modules.setdefault(module_name, ModuleInfo(name=module_name))
        self._collect_node(node, module, class_hint, block_info)

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

    def _create_version(self, node, block_info):
        if not block_info:
            return None
        return Version(node, block_info.block_id, block_info.global_index, block_info.content,
                      block_info.timestamp, block_info.block_idx)

    def _add_class(self, class_node: Node, module: ModuleInfo, class_name: str, block_info):
        version = self._create_version(class_node, block_info)
        if version is None:
            return

        if class_name in module.classes:
            existing_class = module.classes[class_name]
            existing = VersionComparator.find_existing(existing_class.versions, version)
            if existing:
                existing.add_source(*version.sources[0])
                # Блок добавлен как источник к существующей версии класса
                if block_info and not block_info.module_hint:
                    block_info.module_hint = module.name
                    logger.debug(f"[КЛАСС] Блоку {block_info.block_id} назначен модуль {module.name} (существующая версия класса)")
            else:
                existing_class.versions.append(version)
                if block_info and not block_info.module_hint:
                    block_info.module_hint = module.name
                    logger.debug(f"[КЛАСС] Блоку {block_info.block_id} назначен модуль {module.name} (новая версия класса)")
            # Обрабатываем методы внутри класса
            for method_node in class_node.children:
                if method_node.node_type == "method":
                    sig = extract_function_signature(method_node)
                    method = MethodInfo(
                        name=method_node.name,
                        signature=sig,
                        class_name=class_name
                    )
                    method_version = self._create_version(method_node, block_info)
                    if method_version:
                        existing_method = existing_class.methods.get(method.name)
                        if existing_method:
                            existing = VersionComparator.find_existing(existing_method.versions, method_version)
                            if existing:
                                existing.add_source(*method_version.sources[0])
                                # Метод добавлен как источник – блок уже помечен выше, но на всякий случай
                            else:
                                existing_method.versions.append(method_version)
                        else:
                            method.versions.append(method_version)
                            existing_class.methods[method.name] = method
        else:
            class_info = ClassInfo(name=class_name)
            class_info.versions.append(version)
            if block_info and not block_info.module_hint:
                block_info.module_hint = module.name
                logger.debug(f"[КЛАСС] Блоку {block_info.block_id} назначен модуль {module.name} (новый класс)")
            for method_node in class_node.children:
                if method_node.node_type == "method":
                    sig = extract_function_signature(method_node)
                    method = MethodInfo(
                        name=method_node.name,
                        signature=sig,
                        class_name=class_name
                    )
                    method_version = self._create_version(method_node, block_info)
                    if method_version:
                        method.versions.append(method_version)
                    class_info.methods[method.name] = method
            module.classes[class_name] = class_info

        # Защита: если вдруг module_hint не был установлен, принудительно ставим
        if block_info and not block_info.module_hint:
            block_info.module_hint = module.name
            logger.warning(f"[КЛАСС] Принудительно назначен модуль {module.name} блоку {block_info.block_id}")

        logger.debug(f"Обновлён класс {class_name} в модуле {module.name}")


    def _add_function(self, func_node: Node, module: ModuleInfo, class_hint: Optional[str] = None, block_info=None):
        sig = extract_function_signature(func_node)
        version = self._create_version(func_node, block_info)
        if version is None:
            return

        if class_hint and sig[0]:
            class_name = class_hint
            if class_name not in module.classes:
                module.classes[class_name] = ClassInfo(name=class_name)
            class_info = module.classes[class_name]
            method = MethodInfo(
                name=func_node.name,
                signature=sig,
                class_name=class_name
            )
            if method.name in class_info.methods:
                existing_method = class_info.methods[method.name]
                existing = VersionComparator.find_existing(existing_method.versions, version)
                if existing:
                    existing.add_source(*version.sources[0])
                    if block_info and not block_info.module_hint:
                        block_info.module_hint = module.name
                        logger.debug(f"[ФУНКЦИЯ-МЕТОД] Блоку {block_info.block_id} назначен модуль {module.name} (существующая версия метода)")
                else:
                    existing_method.versions.append(version)
                    if block_info and not block_info.module_hint:
                        block_info.module_hint = module.name
                        logger.debug(f"[ФУНКЦИЯ-МЕТОД] Блоку {block_info.block_id} назначен модуль {module.name} (новая версия метода)")
            else:
                method.versions.append(version)
                class_info.methods[method.name] = method
                if block_info and not block_info.module_hint:
                    block_info.module_hint = module.name
                    logger.debug(f"[ФУНКЦИЯ-МЕТОД] Блоку {block_info.block_id} назначен модуль {module.name} (новый метод)")
            logger.debug(f"Добавлен метод {method.name} в класс {class_name} модуля {module.name}")
        else:
            func = FunctionInfo(name=func_node.name, signature=sig)
            if func.name in module.functions:
                existing_func = module.functions[func.name]
                existing = VersionComparator.find_existing(existing_func.versions, version)
                if existing:
                    existing.add_source(*version.sources[0])
                    if block_info and not block_info.module_hint:
                        block_info.module_hint = module.name
                        logger.debug(f"[ФУНКЦИЯ] Блоку {block_info.block_id} назначен модуль {module.name} (существующая версия функции)")
                else:
                    existing_func.versions.append(version)
                    if block_info and not block_info.module_hint:
                        block_info.module_hint = module.name
                        logger.debug(f"[ФУНКЦИЯ] Блоку {block_info.block_id} назначен модуль {module.name} (новая версия функции)")
            else:
                func.versions.append(version)
                module.functions[func.name] = func
                if block_info and not block_info.module_hint:
                    block_info.module_hint = module.name
                    logger.debug(f"[ФУНКЦИЯ] Блоку {block_info.block_id} назначен модуль {module.name} (новая функция)")
            logger.debug(f"Добавлена функция {func.name} в модуль {module.name}")

        if block_info and not block_info.module_hint:
            block_info.module_hint = module.name
            logger.warning(f"[ФУНКЦИЯ] Принудительно назначен модуль {module.name} блоку {block_info.block_id}")


    def _add_method_as_function(self, method_node: Node, module: ModuleInfo, class_hint: Optional[str] = None, block_info=None):
        sig = extract_function_signature(method_node)
        version = self._create_version(method_node, block_info)
        if version is None:
            return

        if class_hint:
            class_name = class_hint
            if class_name not in module.classes:
                module.classes[class_name] = ClassInfo(name=class_name)
            class_info = module.classes[class_name]
            method = MethodInfo(
                name=method_node.name,
                signature=sig,
                class_name=class_name
            )
            if method.name in class_info.methods:
                existing_method = class_info.methods[method.name]
                existing = VersionComparator.find_existing(existing_method.versions, version)
                if existing:
                    existing.add_source(*version.sources[0])
                    if block_info and not block_info.module_hint:
                        block_info.module_hint = module.name
                        logger.debug(f"[МЕТОД-КАК-ФУНКЦИЯ] Блоку {block_info.block_id} назначен модуль {module.name} (существующая версия метода)")
                else:
                    existing_method.versions.append(version)
                    if block_info and not block_info.module_hint:
                        block_info.module_hint = module.name
                        logger.debug(f"[МЕТОД-КАК-ФУНКЦИЯ] Блоку {block_info.block_id} назначен модуль {module.name} (новая версия метода)")
            else:
                method.versions.append(version)
                class_info.methods[method.name] = method
                if block_info and not block_info.module_hint:
                    block_info.module_hint = module.name
                    logger.debug(f"[МЕТОД-КАК-ФУНКЦИЯ] Блоку {block_info.block_id} назначен модуль {module.name} (новый метод)")
            logger.debug(f"Добавлен метод {method.name} в класс {class_name} модуля {module.name}")
        else:
            func = FunctionInfo(name=method_node.name, signature=sig)
            if func.name in module.functions:
                existing_func = module.functions[func.name]
                existing = VersionComparator.find_existing(existing_func.versions, version)
                if existing:
                    existing.add_source(*version.sources[0])
                    if block_info and not block_info.module_hint:
                        block_info.module_hint = module.name
                        logger.debug(f"[МЕТОД-КАК-ФУНКЦИЯ] Блоку {block_info.block_id} назначен модуль {module.name} (существующая версия функции)")
                else:
                    existing_func.versions.append(version)
                    if block_info and not block_info.module_hint:
                        block_info.module_hint = module.name
                        logger.debug(f"[МЕТОД-КАК-ФУНКЦИЯ] Блоку {block_info.block_id} назначен модуль {module.name} (новая версия функции)")
            else:
                func.versions.append(version)
                module.functions[func.name] = func
                if block_info and not block_info.module_hint:
                    block_info.module_hint = module.name
                    logger.debug(f"[МЕТОД-КАК-ФУНКЦИЯ] Блоку {block_info.block_id} назначен модуль {module.name} (новая функция)")
            logger.debug(f"Добавлен метод {method_node.name} как функция в модуль {module.name}")

        if block_info and not block_info.module_hint:
            block_info.module_hint = module.name
            logger.warning(f"[МЕТОД-КАК-ФУНКЦИЯ] Принудительно назначен модуль {module.name} блоку {block_info.block_id}")

    # ---------- Импортированные объекты ----------
    def add_imported_item(self, module_name: str, import_info: ImportInfo):
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

    def get_imported_info(self, module_name: str) -> Optional[Dict[str, ImportInfo]]:
        return self._imported.get(module_name)

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
            for cls_name, cls in mod.classes.items():
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

        # Объединяем классы
        for class_name, class_info in temp.classes.items():
            if class_name not in target.classes:
                target.classes[class_name] = ClassInfo(name=class_name)
            target_class = target.classes[class_name]
            for method_name, method_info in class_info.methods.items():
                if method_name in target_class.methods:
                    for v in method_info.versions:
                        existing = VersionComparator.find_existing(target_class.methods[method_name].versions, v)
                        if existing:
                            existing.add_source(*v.sources[0])
                        else:
                            target_class.methods[method_name].versions.append(v)
                else:
                    target_class.methods[method_name] = method_info
            for v in class_info.versions:
                existing = VersionComparator.find_existing(target_class.versions, v)
                if existing:
                    existing.add_source(*v.sources[0])
                else:
                    target_class.versions.append(v)

        # Объединяем функции
        for func_name, func_info in temp.functions.items():
            if func_name in target.functions:
                for v in func_info.versions:
                    existing = VersionComparator.find_existing(target.functions[func_name].versions, v)
                    if existing:
                        existing.add_source(*v.sources[0])
                    else:
                        target.functions[func_name].versions.append(v)
            else:
                target.functions[func_name] = func_info

        del self._modules[temp_name]
        logger.info(f"Модуль {temp_name} успешно объединён в {target_name}")
        return True

    def add_class_placeholder(self, module_name: str, class_name: str):
        if module_name not in self._modules:
            self._modules[module_name] = ModuleInfo(name=module_name)
        module = self._modules[module_name]
        if class_name not in module.classes:
            module.classes[class_name] = ClassInfo(name=class_name)
            logger.debug(f"Добавлен плейсхолдер класса {class_name} в модуль {module_name}")

    def get_known_modules(self) -> Set[str]:
        return self.get_all_module_names()