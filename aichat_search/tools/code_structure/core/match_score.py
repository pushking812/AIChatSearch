# aichat_search/tools/code_structure/core/match_score.py

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class MatchScore:
    """Хранит веса различных признаков соответствия модулю."""
    
    # Точные совпадения
    exact_class_match: int = 0      # +100: класс полностью совпадает
    exact_method_match: int = 0      # +30: метод совпадает по сигнатуре
    exact_function_match: int = 0    # +25: функция совпадает по сигнатуре
    
    # Частичные совпадения
    partial_class_match: int = 0     # +50: класс частично совпадает
    similar_method: int = 0          # +10: метод похож
    similar_function: int = 0        # +8: функция похожа
    
    # Контекстные подсказки
    import_hint: int = 0             # +5: есть импорт из этого модуля
    naming_convention: int = 0       # +2: имя соответствует стилю модуля
    self_usage: int = 0              # +15: использование self указывает на метод
    
    # Метаданные для отладки
    debug_info: Dict[str, List[Any]] = field(default_factory=dict)
    
    def total(self) -> int:
        """Возвращает общий вес всех признаков."""
        return sum([
            self.exact_class_match,
            self.exact_method_match,
            self.exact_function_match,
            self.partial_class_match,
            self.similar_method,
            self.similar_function,
            self.import_hint,
            self.naming_convention,
            self.self_usage
        ])
    
    def is_confident(self, threshold: int = 30) -> bool:
        """
        Проверяет, достаточно ли уверенности в соответствии.
        
        Args:
            threshold: пороговое значение уверенности
            
        Returns:
            True если общий вес >= threshold
        """
        return self.total() >= threshold
    
    def get_breakdown(self) -> Dict[str, int]:
        """
        Возвращает детальную разбивку по категориям.
        Полезно для отладки и отображения пользователю.
        """
        return {
            'exact_class': self.exact_class_match,
            'exact_method': self.exact_method_match,
            'exact_function': self.exact_function_match,
            'partial_class': self.partial_class_match,
            'similar_method': self.similar_method,
            'similar_function': self.similar_function,
            'import_hint': self.import_hint,
            'naming': self.naming_convention,
            'self_usage': self.self_usage,
            'total': self.total()
        }
    
    def get_top_matches(self, n: int = 3) -> List[str]:
        """
        Возвращает топ-N наиболее значимых совпадений из debug_info.
        """
        all_matches = []
        
        for category, items in self.debug_info.items():
            for item in items:
                if category == 'exact_classes':
                    all_matches.append(f"класс {item}")
                elif category == 'partial_classes':
                    all_matches.append(f"похожий класс {item}")
                elif category == 'exact_methods':
                    all_matches.append(f"метод {item}")
                elif category == 'exact_functions':
                    all_matches.append(f"функция {item}")
                elif category == 'method_as_function':
                    all_matches.append(f"метод как функция")
                elif category == 'similar_methods':
                    all_matches.append(f"похожий метод {item}")
                elif category == 'similar_functions':
                    all_matches.append(f"похожая функция {item}")
                elif category == 'imports':
                    all_matches.append(f"импорт {item}")
        
        return all_matches[:n]
    
    def merge(self, other: 'MatchScore') -> 'MatchScore':
        """
        Объединяет два объекта MatchScore.
        Полезно при агрегации результатов от нескольких блоков.
        """
        result = MatchScore()
        
        result.exact_class_match = self.exact_class_match + other.exact_class_match
        result.exact_method_match = self.exact_method_match + other.exact_method_match
        result.exact_function_match = self.exact_function_match + other.exact_function_match
        result.partial_class_match = self.partial_class_match + other.partial_class_match
        result.similar_method = self.similar_method + other.similar_method
        result.similar_function = self.similar_function + other.similar_function
        result.import_hint = self.import_hint + other.import_hint
        result.naming_convention = self.naming_convention + other.naming_convention
        result.self_usage = self.self_usage + other.self_usage
        
        # Объединяем debug_info
        for key, values in self.debug_info.items():
            result.debug_info[key] = values.copy()
        
        for key, values in other.debug_info.items():
            if key in result.debug_info:
                result.debug_info[key].extend(values)
            else:
                result.debug_info[key] = values.copy()
        
        return result
    
    def normalize(self, factor: float = 1.0) -> 'MatchScore':
        """
        Нормализует веса (например, для усреднения).
        """
        result = MatchScore()
        
        result.exact_class_match = int(self.exact_class_match * factor)
        result.exact_method_match = int(self.exact_method_match * factor)
        result.exact_function_match = int(self.exact_function_match * factor)
        result.partial_class_match = int(self.partial_class_match * factor)
        result.similar_method = int(self.similar_method * factor)
        result.similar_function = int(self.similar_function * factor)
        result.import_hint = int(self.import_hint * factor)
        result.naming_convention = int(self.naming_convention * factor)
        result.self_usage = int(self.self_usage * factor)
        
        # debug_info не нормализуем, копируем как есть
        result.debug_info = self.debug_info.copy()
        
        return result
    
    def __str__(self) -> str:
        """Строковое представление для отладки."""
        parts = []
        total = self.total()
        
        if self.exact_class_match:
            count = self.exact_class_match // 100
            parts.append(f"классы:{count}")
        if self.exact_method_match:
            count = self.exact_method_match // 30
            parts.append(f"методы:{count}")
        if self.exact_function_match:
            count = self.exact_function_match // 25
            parts.append(f"функции:{count}")
        if self.partial_class_match:
            count = self.partial_class_match // 50
            parts.append(f"похожие_классы:{count}")
        if self.similar_method:
            count = self.similar_method // 10
            parts.append(f"похожие_методы:{count}")
        if self.similar_function:
            count = self.similar_function // 8
            parts.append(f"похожие_функции:{count}")
        if self.import_hint:
            parts.append(f"импорты:+{self.import_hint}")
        if self.self_usage:
            parts.append(f"self:+{self.self_usage}")
        
        return f"Score({total}: " + ", ".join(parts) + ")"
    
    def __repr__(self) -> str:
        """Подробное представление для отладки."""
        return (f"MatchScore(total={self.total()}, "
                f"classes={self.exact_class_match//100}, "
                f"methods={self.exact_method_match//30}, "
                f"functions={self.exact_function_match//25})")


def create_score_from_dict(data: Dict[str, Any]) -> MatchScore:
    """
    Создает объект MatchScore из словаря.
    Полезно для десериализации.
    """
    score = MatchScore()
    
    score.exact_class_match = data.get('exact_class_match', 0)
    score.exact_method_match = data.get('exact_method_match', 0)
    score.exact_function_match = data.get('exact_function_match', 0)
    score.partial_class_match = data.get('partial_class_match', 0)
    score.similar_method = data.get('similar_method', 0)
    score.similar_function = data.get('similar_function', 0)
    score.import_hint = data.get('import_hint', 0)
    score.naming_convention = data.get('naming_convention', 0)
    score.self_usage = data.get('self_usage', 0)
    score.debug_info = data.get('debug_info', {})
    
    return score


def aggregate_scores(scores: List[MatchScore]) -> MatchScore:
    """
    Агрегирует несколько объектов MatchScore в один.
    Полезно при анализе нескольких блоков одного модуля.
    """
    if not scores:
        return MatchScore()
    
    result = MatchScore()
    for score in scores:
        result = result.merge(score)
    
    # Усредняем debug_info (оставляем только уникальные значения)
    for key in result.debug_info:
        # Оставляем только уникальные значения
        result.debug_info[key] = list(set(result.debug_info[key]))
    
    return result


def get_confidence_level(score: MatchScore) -> str:
    """
    Возвращает текстовый уровень уверенности на основе веса.
    """
    total = score.total()
    
    if total >= 100:
        return "очень высокая"
    elif total >= 70:
        return "высокая"
    elif total >= 40:
        return "средняя"
    elif total >= 20:
        return "низкая"
    else:
        return "очень низкая"


def format_score_for_display(score: MatchScore) -> str:
    """
    Форматирует Score для отображения пользователю.
    """
    lines = []
    lines.append(f"Общая уверенность: {score.total()} ({get_confidence_level(score)})")
    
    breakdown = score.get_breakdown()
    details = []
    
    if breakdown['exact_class']:
        details.append(f"точные классы: {breakdown['exact_class']//100}")
    if breakdown['exact_method']:
        details.append(f"точные методы: {breakdown['exact_method']//30}")
    if breakdown['exact_function']:
        details.append(f"точные функции: {breakdown['exact_function']//25}")
    if breakdown['partial_class']:
        details.append(f"похожие классы: {breakdown['partial_class']//50}")
    
    if details:
        lines.append("Детали: " + ", ".join(details))
    
    # Добавляем топ совпадений
    top_matches = score.get_top_matches(3)
    if top_matches:
        lines.append("Основания: " + ", ".join(top_matches))
    
    return "\n".join(lines)