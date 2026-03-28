# aichat_search/tools/code_structure/core/version_comparator.py

from typing import List, Optional
from aichat_search.tools.code_structure.models.containers import Version


class VersionComparator:
    """
    Класс для сравнения версий.
    Содержит логику определения эквивалентности версий.
    """

    @staticmethod
    def are_equal(v1: Version, v2: Version) -> bool:
        """
        Сравнивает две версии.
        Текущая реализация: сравнение по cleaned_content.

        Args:
            v1: первая версия
            v2: вторая версия

        Returns:
            True, если версии эквивалентны
        """
        return v1.cleaned_content == v2.cleaned_content

    @staticmethod
    def find_existing(versions: List[Version], new_version: Version) -> Optional[Version]:
        """
        Ищет среди списка версий версию, эквивалентную new_version.

        Args:
            versions: список существующих версий
            new_version: новая версия

        Returns:
            найденная версия или None
        """
        for v in versions:
            if VersionComparator.are_equal(v, new_version):
                return v
        return None