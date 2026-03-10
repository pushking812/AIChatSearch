# aichat_search/gui_components/constants.py

"""Константы, используемые в GUI."""

# Минимальные размеры панелей
MIN_LEFT_WIDTH = 150
MIN_RIGHT_WIDTH = 400
MIN_TOP_HEIGHT = 150
# Минимальная высота нижней панели = мин. высота текстовых полей + высота кнопок + отступы
MIN_REQUEST_HEIGHT = 110
MIN_RESPONSE_HEIGHT = 130
BUTTON_HEIGHT = 35
PADDING = 10
MIN_BOTTOM_HEIGHT = MIN_REQUEST_HEIGHT + MIN_RESPONSE_HEIGHT + BUTTON_HEIGHT + PADDING

# Цвета для подсветки
SEARCH_HIGHLIGHT_COLOR = "yellow"

# Толщина разделителя
SASH_WIDTH = 6

# Настройки окна по умолчанию
DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 800

# Путь к конфигурационному файлу (относительно корня проекта)
CONFIG_DIR = ".config"
CONFIG_FILE = "config.json"
SESSION_FILE = "session.pkl"

# Размер шрифта по умолчанию (в пунктах)
FONT_SIZE = 10

# Количество символов для предварительного просмотра в колонках "Запрос" и "Ответ"
PREVIEW_CHARS = 100

# Количество символов контекста вокруг найденного совпадения
CONTEXT_CHARS = 60

# Шаблон имени файла при экспорте одного сообщения
EXPORT_FILENAME_TEMPLATE = "{source_name}_{chat_title}_сообщение_{message_index:03d}.txt"