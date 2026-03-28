# aichat_search/tools/code_structure/models/project_models.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from aichat_search.tools.code_structure.models.import_models import ImportInfo


@dataclass
class ProjectModuleInfo:
    """Информация о модуле в проекте."""
    name: str  # полное имя модуля (с точками)
    children: Dict[str, 'ProjectModuleInfo'] = field(default_factory=dict)
    # Источники информации о модуле
    from_comments: Set[str] = field(default_factory=set)  # блоки, в которых был комментарий с этим модулем
    from_imports: Set[str] = field(default_factory=set)  # блоки, в которых был импорт, указывающий на этот модуль
    definitions: Dict[str, Set[str]] = field(default_factory=dict)  # тип -> множество имён определений


@dataclass
class ProjectInfo:
    """Общая информация о проекте."""
    modules: Dict[str, ProjectModuleInfo] = field(default_factory=dict)
    # Связи: имя класса/функции -> список возможных модулей (из импортов и определений)
    definitions: Dict[str, Dict[str, Set[str]]] = field(default_factory=dict)  # {name: {type: set(modules)}}