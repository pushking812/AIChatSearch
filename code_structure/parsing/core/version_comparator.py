# code_structure/parsing/core/version_comparator.py

from typing import List, Optional
from code_structure.module_resolution.models.containers import Version


class VersionComparator:
    """
    Класс для сравнения версий.
    Содержит логику определения эквивалентности версий.
    """

    @staticmethod
    def are_equal(v1: Version, v2: Version) -> bool:
        """Сравнивает две версии."""
        return v1.cleaned_content == v2.cleaned_content

    @staticmethod
    def find_existing(versions: List[Version], new_version: Version) -> Optional[Version]:
        """Ищет среди списка версий версию, эквивалентную new_version.        """
        for v in versions:
            if VersionComparator.are_equal(v, new_version):
                return v
        return None