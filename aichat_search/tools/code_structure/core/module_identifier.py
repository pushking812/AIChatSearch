# aichat_search/tools/code_structure/core/module_identifier.py

from typing import Dict, List, Optional, Set, Tuple
import logging
from aichat_search.tools.code_structure.models.node import Node
from aichat_search.tools.code_structure.core.signature_utils import extract_function_signature
from aichat_search.tools.code_structure.models.identifier_models import (
    ModuleInfo, ClassInfo, MethodInfo, FunctionInfo, Signature
)

logger = logging.getLogger(__name__)


class ModuleIdentifier:
    """
    Собирает и хранит идентификаторы модулей с сигнатурами.
    Использует модели ModuleInfo, ClassInfo, MethodInfo, FunctionInfo.
    """

    def __init__(self):
        self._modules: Dict[str, ModuleInfo] = {}

    # ---------- Сбор данных ----------

    def collect_from_tree(self, node: Node, module_name: str):
        """Рекурсивно собирает все идентификаторы из дерева узлов в указанный модуль."""
        module = self._modules.setdefault(module_name, ModuleInfo(name=module_name))
        self._collect_node(node, module)

    def _collect_node(self, node: Node, module: ModuleInfo):
        """Обходит узел и добавляет информацию в модуль."""
        for child in node.children:
            if child.node_type == "class":
                self._add_class(child, module)
            elif child.node_type == "function":
                self._add_function(child, module)
            elif child.node_type == "method":
                # Метод вне класса – добавляем как функцию (для совместимости)
                self._add_method_as_function(child, module)
            else:
                self._collect_node(child, module)

    def _add_class(self, class_node: Node, module: ModuleInfo):
        """Добавляет класс и все его методы в модуль."""
        class_info = ClassInfo(name=class_node.name)
        for method_node in class_node.children:
            if method_node.node_type == "method":
                sig = extract_function_signature(method_node)
                method = MethodInfo(
                    name=method_node.name,
                    signature=sig,
                    class_name=class_node.name
                )
                # Проверяем дубликат в классе
                if method.name in class_info.methods:
                    existing = class_info.methods[method.name]
                    if existing.signature == sig:
                        logger.debug(f"Метод {class_node.name}.{method.name} с такой сигнатурой уже существует, пропускаем")
                        continue
                class_info.methods[method.name] = method
        module.classes[class_info.name] = class_info

    def _add_function(self, func_node: Node, module: ModuleInfo):
        """Добавляет функцию верхнего уровня."""
        sig = extract_function_signature(func_node)
        func = FunctionInfo(name=func_node.name, signature=sig)
        # Проверяем дубликат
        if func.name in module.functions:
            existing = module.functions[func.name]
            if existing.signature == sig:
                logger.debug(f"Функция {func.name} с такой сигнатурой уже существует, пропускаем")
                return
        module.functions[func.name] = func

    def _add_method_as_function(self, method_node: Node, module: ModuleInfo):
        """Добавляет метод вне класса как функцию."""
        sig = extract_function_signature(method_node)
        func = FunctionInfo(name=method_node.name, signature=sig)
        if func.name in module.functions:
            existing = module.functions[func.name]
            if existing.signature == sig:
                logger.debug(f"Метод {method_node.name} вне класса с такой сигнатурой уже существует, пропускаем")
                return
        module.functions[func.name] = func

    # ---------- Методы поиска ----------

    def find_module_for_class(self, class_name: str) -> Optional[str]:
        """Ищет модуль, содержащий класс с указанным именем."""
        for mod_name, mod in self._modules.items():
            if class_name in mod.classes:
                return mod_name
        return None

    def find_module_for_method(self, method_name: str, signature: Signature) -> Optional[str]:
        """Ищет модуль, содержащий метод с указанным именем и сигнатурой."""
        for mod_name, mod in self._modules.items():
            for cls in mod.classes.values():
                method = cls.methods.get(method_name)
                if method and method.signature == signature:
                    return mod_name
        return None

    def find_module_for_method_with_class(self, method_name: str, signature: Signature, class_name: Optional[str] = None) -> Optional[str]:
        """Ищет модуль, содержащий метод, optionally в указанном классе."""
        for mod_name, mod in self._modules.items():
            for cls_name, cls in mod.classes.items():
                if class_name and cls_name != class_name:
                    continue
                method = cls.methods.get(method_name)
                if method and method.signature == signature:
                    return mod_name
        return None

    def find_module_for_function(self, func_name: str, signature: Signature) -> Optional[str]:
        """Ищет модуль, содержащий функцию с указанным именем и сигнатурой."""
        for mod_name, mod in self._modules.items():
            func = mod.functions.get(func_name)
            if func and func.signature == signature:
                return mod_name
        return None

    def find_modules_by_method_name(self, method_name: str) -> List[Tuple[str, str]]:
        """
        Ищет все модули и классы, содержащие метод с указанным именем.
        Возвращает список (модуль, класс).
        """
        results = []
        for mod_name, mod in self._modules.items():
            for cls_name, cls in mod.classes.items():
                if method_name in cls.methods:
                    results.append((mod_name, cls_name))
        return results

    # ---------- Доступ к данным ----------

    def get_module_info(self, module_name: str) -> Optional[ModuleInfo]:
        """Возвращает информацию о модуле или None."""
        return self._modules.get(module_name)

    def get_all_module_names(self) -> Set[str]:
        """Возвращает множество имён всех модулей."""
        return set(self._modules.keys())

    def get_temp_modules(self) -> List[str]:
        """Возвращает список временных модулей (с префиксом 'temp_')."""
        return [name for name in self._modules if name.startswith('temp_')]

    def remove_temp_modules(self):
        """Удаляет все временные модули."""
        to_remove = self.get_temp_modules()
        logger.info(f"Удаление временных модулей: {to_remove}")
        for name in to_remove:
            del self._modules[name]

    def merge_temp_module(self, temp_name: str, target_name: str) -> bool:
        """
        Переносит методы из временного модуля в целевой.
        При совпадении имени метода и сигнатуры добавляет источник (если нужно).
        Возвращает True в случае успеха.
        """
        if temp_name not in self._modules or target_name not in self._modules:
            logger.error(f"Не удалось найти модули: {temp_name} -> {target_name}")
            return False
        temp = self._modules[temp_name]
        target = self._modules[target_name]

        # Переносим классы (с проверкой дубликатов)
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

        # Переносим функции (если не конфликтуют)
        for func_name, func_info in temp.functions.items():
            if func_name in target.functions:
                existing = target.functions[func_name]
                if existing.signature == func_info.signature:
                    logger.debug(f"Функция {func_name} уже существует, пропускаем")
                    continue
            target.functions[func_name] = func_info

        # Удаляем временный модуль
        del self._modules[temp_name]
        logger.info(f"Модуль {temp_name} успешно объединён в {target_name}")
        return True

    # ---------- Методы для обратной совместимости ----------

    def get_known_modules(self) -> Set[str]:
        """Старый метод, возвращает множество имён модулей."""
        return self.get_all_module_names()