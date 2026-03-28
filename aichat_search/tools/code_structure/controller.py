# aichat_search/tools/code_structure/controller.py

from typing import List, Tuple

from aichat_search.model import Chat, MessagePair
from aichat_search.tools.code_structure.ui.code_structure import CodeStructureView
from aichat_search.tools.code_structure.ui.code_structure.main_window_presenter import CodeStructurePresenter

class CodeStructureController:
    def __init__(self, parent, items: List[Tuple[Chat, MessagePair]]):
        self.view = CodeStructureView(parent)
        self.presenter = CodeStructurePresenter(self.view, items)
        self.view.set_presenter(self.presenter)