# aichat_search/exporters/factory.py

from typing import Type
from .exporters.base import Exporter
from .exporters.text_exporter import TextExporter


class ExporterFactory:
    """Фабрика для получения экземпляров экспортёров по имени формата."""

    _exporters = {
        'txt': TextExporter,
        # в будущем можно добавить 'json': JsonExporter, 'csv': CsvExporter и т.д.
    }

    @classmethod
    def get_exporter(cls, format_name: str) -> Exporter:
        """Возвращает экспортёр для указанного формата."""
        exporter_class = cls._exporters.get(format_name.lower())
        if exporter_class is None:
            raise ValueError(f"Unsupported export format: {format_name}")
        return exporter_class()