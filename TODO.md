# TODO: Разработка приложения для поиска по архиву чатов DeepSeek (скорректированная версия)

Следуй инструкциям SYSTEM_INSTRUCTIONS_FOR_CHATGPT.md.

Вносим изменения в текущую версию проекта: 
ЭТАП1. Сохранение состояния окна 
1.1. Что сохраняем root.geometry() root.winfo_x(), winfo_y() sashpos основного PanedWindow sashpos вложенного PanedWindow 
2.2. Формат хранения (предлагаю JSON) { "geometry": "1200x800+100+100", "main_sash": 300, "text_sash": 400 } 
3.3. Новый модуль? Нет. Добавить методы в Application: save_window_state() load_window_state()

ЭТАП 2. Меню 
В меню Файл добавить: 
«Сохранить состояние окна» (опционально) 
«Загрузить состояние окна»

в т.ч. должны сохранятся и восстанавливаться следующие параметры:
left_frame, right_paned, top_frame, bottom_frame, request_container, response_container
ширина и высота главного окна

