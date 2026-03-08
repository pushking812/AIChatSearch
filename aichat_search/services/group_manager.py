# aichat_search/services/group_manager.py (полная версия с поддержкой списка групп)

import json
import os
from typing import Dict, List, Optional, Set


class GroupManager:
    """Управляет группами чатов, сохраняя данные в groups.json."""

    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.groups_file = os.path.join(config_dir, "groups.json")
        self._groups: Set[str] = set()          # все когда-либо созданные группы
        self._assignments: Dict[str, str] = {}  # chat_id -> group_name
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.groups_file):
            try:
                with open(self.groups_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._groups = set(data.get("groups", []))
                    self._assignments = data.get("assignments", {})
            except Exception as e:
                print(f"Ошибка загрузки groups.json: {e}")
                self._groups = set()
                self._assignments = {}

    def save(self) -> None:
        os.makedirs(self.config_dir, exist_ok=True)
        data = {
            "groups": list(self._groups),
            "assignments": self._assignments
        }
        try:
            with open(self.groups_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения groups.json: {e}")

    def get_group(self, chat_id: str) -> Optional[str]:
        return self._assignments.get(chat_id)

    def set_group(self, chat_id: str, group_name: Optional[str]) -> None:
        if group_name is None:
            self._assignments.pop(chat_id, None)
        else:
            self._assignments[chat_id] = group_name
            self._groups.add(group_name)
        self.save()

    def rename_group(self, old_name: str, new_name: str) -> bool:
        if not new_name or old_name == new_name:
            return False
        if new_name in self._groups:
            return False  # конфликт имён
        # Обновляем все назначения
        for chat_id, group in list(self._assignments.items()):
            if group == old_name:
                self._assignments[chat_id] = new_name
        self._groups.remove(old_name)
        self._groups.add(new_name)
        self.save()
        return True

    def delete_group(self, group_name: str) -> None:
        # Удаляем все назначения этой группы
        to_delete = [chat_id for chat_id, group in self._assignments.items() if group == group_name]
        for chat_id in to_delete:
            del self._assignments[chat_id]
        self._groups.discard(group_name)
        self.save()

    def add_group(self, group_name: str) -> bool:
        """Добавляет группу в список, если её ещё нет."""
        if not group_name or group_name in self._groups:
            return False
        self._groups.add(group_name)
        self.save()
        return True

    def get_all_groups(self) -> List[str]:
        return sorted(self._groups)

    def apply_to_chat(self, chat) -> None:
        chat.group = self.get_group(chat.id)