# aichat_search/tools/code_structure/core/structure_builder_base.py
"""Базовые классы для StructureBuilder"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, List


class StructureBuilderLogger:
    """Логирование состояния StructureBuilder"""
    
    def __init__(self, name: str = "StructureBuilder"):
        self.logger = logging.getLogger(f"structure_builder.{name}")
        self.operation_stack: List[Dict[str, Any]] = []
        self.decisions: List[Dict[str, Any]] = []
        self._enabled = True
    
    def enable(self, enabled: bool = True):
        """Включение/отключение логирования"""
        self._enabled = enabled
    
    def start_operation(self, operation: str, params: Dict[str, Any]):
        """Начало операции"""
        if not self._enabled:
            return
            
        entry = {
            'operation': operation,
            'params': params,
            'timestamp': datetime.now().isoformat()
        }
        self.operation_stack.append(entry)
        self.logger.debug(f"▶ START {operation} | params: {self._safe_json(params)}")
    
    def end_operation(self, operation: str, result: Any = None):
        """Завершение операции"""
        if not self._enabled:
            return
            
        if self.operation_stack:
            self.operation_stack.pop()
        self.logger.debug(f"◀ END {operation} | result: {result}")
    
    def log_decision(self, decision: str, context: Dict[str, Any], reason: str):
        """Логирование ключевого решения"""
        if not self._enabled:
            return
            
        decision_record = {
            'decision': decision,
            'context': context,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
        self.decisions.append(decision_record)
        self.logger.info(f"⚖️ DECISION: {decision} | reason: {reason} | context: {self._safe_json(context)}")
    
    def _safe_json(self, obj: Any) -> str:
        """Безопасное преобразование в JSON"""
        try:
            return json.dumps(obj, default=str, ensure_ascii=False)
        except:
            return str(obj)
    
    def get_state_snapshot(self) -> Dict[str, Any]:
        """Снимок текущего состояния логгера"""
        return {
            'operation_stack': [op['operation'] for op in self.operation_stack],
            'decisions_count': len(self.decisions),
            'last_decision': self.decisions[-1] if self.decisions else None,
            'timestamp': datetime.now().isoformat()
        }


class StatefulProcessor:
    """Базовый класс для процессоров с сохранением состояния"""
    
    def __init__(self):
        self.logger = StructureBuilderLogger(self.__class__.__name__)
        self.stats = {
            'processed_nodes': 0,
            'created_containers': 0,
            'created_versions': 0,
            'found_existing': 0,
            'skipped_nodes': 0
        }
        self._reset_stats()
    
    def _reset_stats(self):
        """Сброс статистики"""
        for key in self.stats:
            self.stats[key] = 0
    
    def _update_stats(self, **kwargs):
        """Обновление статистики"""
        for key, value in kwargs.items():
            if key in self.stats:
                self.stats[key] += value
    
    def log_state(self) -> Dict[str, Any]:
        """Возвращает текущее состояние для отладки"""
        return {
            'stats': self.stats.copy(),
            'logger_state': self.logger.get_state_snapshot()
        }
    
    def print_stats(self):
        """Вывод статистики в лог"""
        self.logger.logger.info("📊 Statistics:")
        for key, value in self.stats.items():
            self.logger.logger.info(f"  - {key}: {value}")
    
    def reset(self):
        """Сброс состояния процессора"""
        self._reset_stats()
        self.logger = StructureBuilderLogger(self.__class__.__name__)