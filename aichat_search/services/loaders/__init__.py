# aichat_search/services/loaders/__init__.py

from .base import ChatLoader
from .deepseek_zip_loader import DeepSeekZipLoader

__all__ = ['ChatLoader', 'DeepSeekZipLoader']