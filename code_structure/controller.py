# code_structure/controller.py

from typing import List, Tuple
from aichat_search.model import Chat, MessagePair
from code_structure.dialogs.main import CodeStructureView
from code_structure.dialogs.main.main_window_presenter import CodeStructurePresenter
from code_structure.facades import (
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
            data_provider.import_service
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