# code_structure/dialogs/ambiguity/ambiguity_presenter.py

from typing import List, Dict, Optional
from code_structure.dialogs.dialog_interfaces import AmbiguityView
from code_structure.dialogs.dto import AmbiguityInfo

class AmbiguityPresenter:
    def __init__(self, view: AmbiguityView, ambiguities: List[AmbiguityInfo]):
        self.view = view
        self.ambiguities = ambiguities

    def initialize(self):
        self.view.set_ambiguities(self.ambiguities)

    def on_ok(self):
        result = {}
        for amb in self.ambiguities:
            chosen = self.view.get_selected_path(amb.name)
            if not chosen:
                # Если пользователь не выбрал, используем первый кандидат
                chosen = amb.candidates[0] if amb.candidates else ""
                if not chosen:
                    self.view.show_error(f"Для '{amb.name}' нет доступных путей")
                    return
            result[amb.name] = chosen
        self.view.close(result)

    def on_cancel(self):
        self.view.close(None)