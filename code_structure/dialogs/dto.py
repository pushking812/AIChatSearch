# code_structure/dialogs/dto.py

"""
Data Transfer Objects (DTO) для обмена данными между UI-слоем и бизнес-логикой.

Все DTO являются простыми dataclass-объектами, не содержащими бизнес-логики.
Они используются для передачи информации между View, Presenter и фасадами,
обеспечивая изоляцию UI от внутренних моделей (MessageBlockInfo, Container и др.).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional

# ----------------------------------------------------------------------
# DTO для ErrorBlockDialog
# ----------------------------------------------------------------------
@dataclass
class ErrorBlockInput:
    """
    Входные данные для диалога исправления синтаксической ошибки.
    
    Attributes:
        block_id: Идентификатор блока кода.
        original_code: Исходный код блока (с ошибкой).
        language: Язык программирования (например, "python").
    """
    block_id: str
    original_code: str
    language: str

@dataclass
class ErrorBlockOutput:
    """
    Результат работы диалога исправления ошибки.
    
    Attributes:
        fixed_code: Исправленный код (None, если пользователь отменил).
    """
    fixed_code: Optional[str] = None

# ----------------------------------------------------------------------
# DTO для ModuleAssignmentDialog
# ----------------------------------------------------------------------
@dataclass
class UnknownBlockInfo:
    """
    Информация о блоке, которому не удалось автоматически назначить модуль.
    
    Attributes:
        id: Уникальный идентификатор блока (например, "chat_..._block3").
        display_name: Человекочитаемое имя для отображения в списке.
        content: Исходный код блока.
    """
    id: str
    display_name: str
    content: str

@dataclass
class KnownModuleInfo:
    """
    Информация об известном модуле (уже определённом в системе).
    
    Attributes:
        name: Полное имя модуля (с точками, например, "myapp.models").
        source: Описание источника (например, "из блока abc").
        code: Пример кода из модуля для предпросмотра.
    """
    name: str
    source: Optional[str]
    code: str

@dataclass
class TreeDisplayNode:
    """
    Узел дерева для отображения иерархии модулей/классов/методов/версий.
    Используется в главном окне и в диалоге назначения модулей.
    
    Attributes:
        text: Отображаемое имя узла.
        type: Тип узла ("module", "class", "method", "function", "version", ...).
        signature: Сигнатура (для функций/методов).
        version: Строковое представление версии (например, "v3").
        sources: Информация об источниках (блок, строки).
        full_name: Полное имя узла (для поиска в бэкенде).
        block_id: Идентификатор блока (только для версий).
        start_line: Начальная строка в блоке (только для версий).
        end_line: Конечная строка в блоке (только для версий).
        children: Список дочерних узлов.
    """
    text: str
    type: str
    signature: str = ""
    version: str = ""
    sources: str = ""
    full_name: str = ""
    block_id: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    children: List['TreeDisplayNode'] = field(default_factory=list)

@dataclass
class ModuleAssignmentInput:
    """
    Входные данные для диалога назначения модулей.
    
    Attributes:
        unknown_blocks: Список неопределённых блоков.
        known_modules: Список известных модулей.
        module_tree: Корневой узел дерева модулей для отображения.
    """
    unknown_blocks: List[UnknownBlockInfo]
    known_modules: List[KnownModuleInfo]
    module_tree: TreeDisplayNode

@dataclass
class ModuleAssignmentOutput:
    """
    Результат работы диалога назначения модулей.
    
    Attributes:
        assignments: Словарь {block_id: module_name}.
        updated_module_tree: Обновлённое дерево модулей (если создавались новые).
    """
    assignments: Dict[str, str]
    updated_module_tree: TreeDisplayNode

# ----------------------------------------------------------------------
# DTO для главного окна
# ----------------------------------------------------------------------
@dataclass
class FlatListItem:
    """
    Элемент плоского списка в главном окне (справа от дерева).
    
    Attributes:
        block_id: Идентификатор блока.
        block_name: Имя блока.
        node_path: Путь к узлу в дереве.
        parent_path: Путь родительского узла.
        lines: Диапазон строк (например, "10-15").
        module: Имя модуля, к которому привязан блок (или пусто).
        class_name: Имя класса, если узел является методом, иначе "-".
        strategy: Стратегия, использованная для назначения модуля.
    """
    block_id: str
    block_name: str
    node_path: str
    parent_path: str
    lines: str
    module: str
    class_name: str
    strategy: str

@dataclass
class CodeStructureInitDTO:
    """
    Начальные данные для инициализации главного окна.
    
    Attributes:
        languages: Список языков программирования, присутствующих в блоках.
        tree: Корневой узел дерева модулей.
        flat_items: Плоский список элементов.
        has_unknown_blocks: Флаг наличия неопределённых блоков.
    """
    languages: List[str]
    tree: TreeDisplayNode
    flat_items: List[FlatListItem]
    has_unknown_blocks: bool

@dataclass
class CodeStructureRefreshDTO:
    """
    Обновлённые данные после изменения фильтра (например, local_only).
    
    Attributes:
        tree: Обновлённое дерево модулей.
        flat_items: Обновлённый плоский список.
    """
    tree: TreeDisplayNode
    flat_items: List[FlatListItem]