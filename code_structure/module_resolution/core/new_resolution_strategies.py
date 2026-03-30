# code_structure/module_resolution/core/new_resolution_strategies.py

"""
Адаптированные стратегии разрешения модулей для CodeNode.
"""
from typing import Optional, Set, List, Dict, Tuple
from code_structure.models.code_node import CodeNode, ClassNode, FunctionNode, MethodNode
from code_structure.models.versioned_node import VersionedNode
from code_structure.parsing.core.signature_utils import extract_function_signature
from code_structure.imports.core.import_analyzer import extract_imports_from_block


class ResolutionStrategy:
    """Базовый класс стратегии."""
    def resolve(self, node: CodeNode, context) -> Optional[str]:
        raise NotImplementedError


class ClassStrategy(ResolutionStrategy):
    """Стратегия на основе имён классов."""
    def resolve(self, node: CodeNode, context) -> Optional[str]:
        # Ищем классы в узле и его детях
        classes = self._extract_classes(node)
        if not classes:
            return None
        # В контексте должен быть доступ к ранее определённым модулям
        identifier = context.get('identifier')
        if identifier is None:
            return None
        for class_name in classes:
            module = identifier.find_module_for_class(class_name)
            if module:
                return module
            module = identifier.find_imported_class(class_name)
            if module:
                return module
        return None

    def _extract_classes(self, node: CodeNode) -> Set[str]:
        classes = set()
        if isinstance(node, ClassNode):
            classes.add(node.name)
        for child in node.children:
            classes.update(self._extract_classes(child))
        return classes


class MethodStrategy(ResolutionStrategy):
    """Стратегия на основе методов (ищет self/cls в параметрах)."""
    def resolve(self, node: CodeNode, context) -> Optional[str]:
        methods, funcs_with_self = self._extract_methods_and_funcs_with_self(node)
        if not methods and not funcs_with_self:
            return None
        # Собираем сигнатуры методов и функций с self/cls
        sigs = self._collect_signatures(node, methods | funcs_with_self)
        # Получаем контекст
        identifier = context.get('identifier')
        if identifier is None:
            return None
        common_module = None
        for name in methods | funcs_with_self:
            sig = sigs.get(name)
            if not sig:
                continue
            # Проверяем, что есть self/cls
            has_self, params = sig
            if not (has_self and params and params[0] in ('self', 'cls')):
                continue
            target_params_count = len(params) - 1
            candidates = set()
            for mod_name in identifier.get_all_module_names():
                module = identifier.get_module_info(mod_name)
                if not module:
                    continue
                for class_info in module.classes.values():
                    method_info = class_info.methods.get(name)
                    if not method_info:
                        continue
                    cand_sig = method_info.signature
                    if not (cand_sig[0] and cand_sig[1] and cand_sig[1][0] in ('self', 'cls')):
                        continue
                    cand_params_count = len(cand_sig[1]) - 1
                    if target_params_count == cand_params_count:
                        candidates.add(mod_name)
            if not candidates:
                continue
            # Если несколько кандидатов, пытаемся выбрать неимпортированный
            if len(candidates) > 1:
                non_imported = [m for m in candidates if not identifier.get_module_info(m).is_imported]
                if len(non_imported) == 1:
                    candidates = set(non_imported)
                else:
                    return None
            module_for_name = next(iter(candidates))
            if common_module is None:
                common_module = module_for_name
            elif common_module != module_for_name:
                return None
        return common_module

    def _extract_methods_and_funcs_with_self(self, node: CodeNode) -> Tuple[Set[str], Set[str]]:
        methods = set()
        funcs_with_self = set()
        if isinstance(node, MethodNode):
            methods.add(node.name)
        elif isinstance(node, FunctionNode):
            # Проверим, есть ли self/cls в сигнатуре (можно извлечь позже)
            funcs_with_self.add(node.name)
        for child in node.children:
            m, f = self._extract_methods_and_funcs_with_self(child)
            methods.update(m)
            funcs_with_self.update(f)
        return methods, funcs_with_self

    def _collect_signatures(self, node: CodeNode, names: Set[str]) -> Dict[str, Tuple[bool, List[str]]]:
        sigs = {}
        for name in names:
            found = self._find_node(node, name, ('method', 'function'))
            if found:
                # У FunctionNode и MethodNode есть signature в строковом виде
                # Извлекаем has_self и параметры
                has_self, params = extract_function_signature_from_code_node(found)
                sigs[name] = (has_self, params)
        return sigs

    def _find_node(self, node: CodeNode, name: str, node_types: tuple) -> Optional[CodeNode]:
        if node.name == name and node.node_type in node_types:
            return node
        for child in node.children:
            found = self._find_node(child, name, node_types)
            if found:
                return found
        return None


class FunctionStrategy(ResolutionStrategy):
    """Стратегия на основе функций верхнего уровня (без self/cls)."""
    def resolve(self, node: CodeNode, context) -> Optional[str]:
        func_names = self._extract_functions(node)
        if not func_names:
            return None
        # Собираем сигнатуры
        sigs = self._collect_signatures(node, func_names)
        # Методы из классов (игнорируем, так как они уже обработаны в MethodStrategy)
        identifier = context.get('identifier')
        if identifier is None:
            return None
        # Получаем имена методов из классов (чтобы исключить их)
        method_names = set()
        for mod_name in identifier.get_all_module_names():
            module = identifier.get_module_info(mod_name)
            if not module:
                continue
            for class_info in module.classes.values():
                for method_info in class_info.methods.values():
                    if method_info.signature[0] and method_info.signature[1] and method_info.signature[1][0] in ('self', 'cls'):
                        method_names.add(method_info.name)
        candidates = set()
        for name in func_names:
            if name in method_names:
                continue
            sig = sigs.get(name)
            if not sig:
                continue
            target_params = sig[1]
            if sig[0] and target_params and target_params[0] in ('self', 'cls'):
                target_params = target_params[1:]
            for mod_name in identifier.get_all_module_names():
                module = identifier.get_module_info(mod_name)
                if not module:
                    continue
                func_info = module.functions.get(name)
                if not func_info:
                    continue
                cand_sig = func_info.signature
                cand_params = cand_sig[1]
                if cand_sig[0] and cand_params and cand_params[0] in ('self', 'cls'):
                    cand_params = cand_params[1:]
                if len(target_params) == len(cand_params):
                    candidates.add(mod_name)
            # Ищем импортированную функцию
            imported = identifier.find_imported_function(name)
            if imported:
                candidates.add(imported)
        if len(candidates) == 1:
            return next(iter(candidates))
        elif len(candidates) > 1:
            non_imported = [m for m in candidates if not identifier.get_module_info(m).is_imported]
            if len(non_imported) == 1:
                return non_imported[0]
        return None

    def _extract_functions(self, node: CodeNode) -> Set[str]:
        funcs = set()
        if isinstance(node, FunctionNode) and not isinstance(node, MethodNode):
            funcs.add(node.name)
        for child in node.children:
            funcs.update(self._extract_functions(child))
        return funcs

    def _collect_signatures(self, node: CodeNode, names: Set[str]) -> Dict[str, Tuple[bool, List[str]]]:
        sigs = {}
        for name in names:
            found = self._find_node(node, name, ('function',))
            if found:
                has_self, params = extract_function_signature_from_code_node(found)
                sigs[name] = (has_self, params)
        return sigs

    def _find_node(self, node: CodeNode, name: str, node_types: tuple) -> Optional[CodeNode]:
        if node.name == name and node.node_type in node_types:
            return node
        for child in node.children:
            found = self._find_node(child, name, node_types)
            if found:
                return found
        return None


class ImportStrategy(ResolutionStrategy):
    """Стратегия на основе импортов в блоке."""
    def resolve(self, node: CodeNode, context) -> Optional[str]:
        # Нужно получить исходный код блока (node.block.content)
        content = node.block.content
        if not content:
            return None
        imports = extract_imports_from_block(content, None)
        if not imports:
            return None
        identifier = context.get('identifier')
        if identifier is None:
            return None
        candidates = set()
        for imp in imports:
            module = identifier.find_module_by_imported_name(imp.target_fullname)
            if not module:
                last_part = imp.target_fullname.split('.')[-1]
                module = identifier.find_module_by_imported_name(last_part)
            if module:
                candidates.add(module)
        if len(candidates) == 1:
            return next(iter(candidates))
        elif len(candidates) > 1:
            # неоднозначно, не определяем
            pass
        return None


def extract_function_signature_from_code_node(node: CodeNode) -> Tuple[bool, List[str]]:
    """Извлекает сигнатуру из FunctionNode или MethodNode."""
    if node.node_type not in ('function', 'method'):
        return False, []
    # Сигнатура хранится в node.signature (строка вида "a, b=1")
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