# aichat_search/tools/code_structure/controller.py

from typing import List, Tuple
from aichat_search.model import Chat, MessagePair
from aichat_search.tools.code_structure.ui.code_structure import CodeStructureView
from aichat_search.tools.code_structure.ui.code_structure.main_window_presenter import CodeStructurePresenter
from aichat_search.tools.code_structure.facades import (
    StructureDataProvider, ModuleAssignmentManager, PersistenceManager
)


class CodeStructureController:
    def __init__(self, parent, items: List[Tuple[Chat, MessagePair]]):
        # Создаём провайдеры
        data_provider = StructureDataProvider(items)
        module_manager = ModuleAssignmentManager(
            data_provider.block_service,
            data_provider.module_service
        )
        persistence_manager = PersistenceManager(
            data_provider.block_service,
            data_provider.module_service,
            data_provider.import_service  # нужно будет добавить импорт в StructureDataProvider
        )

        # Создаём View и Presenter
        self.view = CodeStructureView(parent)
        self.presenter = CodeStructurePresenter(
            self.view,
            data_provider,
            module_manager,
            persistence_manager
        )
        self.view.set_presenter(self.presenter)