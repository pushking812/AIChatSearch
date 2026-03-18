# aichat_search/tools/code_structure/core/structure_builder_deps.py
"""Фасады для внешних зависимостей StructureBuilder"""

import logging
from typing import Tuple, Optional, Any
from unittest.mock import Mock

logger = logging.getLogger(__name__)


class SignatureUtils:
    """Фасад для работы с сигнатурами функций"""
    
    _instance = None
    _mock_mode = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def set_mock_mode(cls, enabled: bool = True):
        """Включает режим моков для тестирования"""
        cls._mock_mode = enabled
    
    @staticmethod
    def extract_function_signature(node) -> Tuple[bool, str]:
        """
        Извлекает сигнатуру функции и определяет, есть ли параметр self.
        
        Args:
            node: Узел функции (FunctionNode)
            
        Returns:
            Tuple[bool, str]: (has_self, signature)
        """
        # Если включен режим моков, пробуем получить из атрибутов node
        if SignatureUtils._mock_mode:
            return SignatureUtils._extract_from_node(node)
        
        try:
            # Пробуем импортировать реальную функцию
            from aichat_search.tools.code_structure.core.signature_utils import extract_function_signature as real_extract
            return real_extract(node)
        except ImportError as e:
            logger.debug(f"Не удалось импортировать extract_function_signature: {e}")
            return SignatureUtils._extract_from_node(node)
        except Exception as e:
            logger.error(f"Ошибка в extract_function_signature: {e}")
            return (False, "")
    
    @staticmethod
    def _extract_from_node(node) -> Tuple[bool, str]:
        """Извлекает информацию из атрибутов node"""
        has_self = False
        signature = ""
        
        # Логируем для отладки
        logger.debug(f"Extracting from node: type={type(node).__name__}, attrs={dir(node)}")
        
        # Проверяем наличие параметров
        if hasattr(node, 'parameters') and node.parameters:
            has_self = 'self' in node.parameters
            logger.debug(f"  parameters={node.parameters}, has_self={has_self}")
        
        # Проверяем наличие сигнатуры
        if hasattr(node, 'signature'):
            signature = node.signature
            logger.debug(f"  signature={signature}")
        elif hasattr(node, 'name'):
            # Формируем сигнатуру по умолчанию
            params = ', '.join(getattr(node, 'parameters', ['x']))
            signature = f"def {node.name}({params})"
            logger.debug(f"  generated signature={signature}")
        
        # Проверяем тип узла
        if hasattr(node, 'node_type'):
            if node.node_type == 'method':
                has_self = True
                logger.debug(f"  node_type=method, forcing has_self=True")
        
        logger.debug(f"Extracted from node: has_self={has_self}, signature={signature}")
        return (has_self, signature)


class ContainerFactory:
    """Фабрика для создания контейнеров"""
    
    @staticmethod
    def create_container(node_type: str, name: str):
        """
        Создает контейнер соответствующего типа.
        
        Args:
            node_type: Тип узла ('class', 'function', 'method', 'code_block')
            name: Имя контейнера
            
        Returns:
            Container соответствующего типа
        """
        from aichat_search.tools.code_structure.models.containers import (
            ClassContainer, FunctionContainer, MethodContainer, CodeBlockContainer,
            Container
        )
        
        logger.debug(f"Creating container: type={node_type}, name={name}")
        
        if node_type == 'class':
            return ClassContainer(name)
        elif node_type == 'function':
            return FunctionContainer(name)
        elif node_type == 'method':
            return MethodContainer(name)
        elif node_type == 'code_block':
            return CodeBlockContainer(f"CodeBlock_{name}")
        else:
            logger.warning(f"Неизвестный тип контейнера: {node_type}, создаем базовый Container")
            return Container(name, node_type)


class VersionFactory:
    """Фабрика для создания версий"""
    
    @staticmethod
    def create_version(node, block_id: str, global_index: int, content: str):
        """
        Создает новую версию.
        
        Args:
            node: Узел AST
            block_id: ID блока
            global_index: Глобальный индекс
            content: Содержимое блока
            
        Returns:
            Version объект
        """
        from aichat_search.tools.code_structure.models.containers import Version
        
        logger.debug(f"Creating version for block {block_id}, node type: {getattr(node, 'node_type', 'unknown')}")
        return Version(node, block_id, global_index, content)