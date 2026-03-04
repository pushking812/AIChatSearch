# TODO: Реализация поддержки нескольких источников данных

## Итерация 3 "Сохранение и восстановление сессии"
Модули: `persistence.py` (новый), `controller.py`, `gui_components/application.py`
- [ ] **Подзадача 3.1** "Создать модуль `persistence.py` с функциями `save_session(sources, path)` и `load_session(path)` на основе `pickle`."
- [ ] **Подзадача 3.2** "В `ChatController` добавить атрибут `session_path` (по умолчанию `config/session.pkl`) и методы `save_session()`, `load_session()`."
- [ ] **Подзадача 3.3** "В `Application.__init__()` после создания контроллера вызвать `self.controller.load_session()` и обновить список чатов."
- [ ] **Подзадача 3.4** "В `Application._on_closing()` вызвать `self.controller.save_session()`."
- [ ] **Подзадача 3.5** "После успешного добавления архива (в `add_archive`) вызывать `self.controller.save_session()` для автосохранения."
- [ ] **Подзадача 3.6** "После сохранения изменений в сообщении (`save_current_pair`) также вызывать `save_session()` (опционально, по желанию)."

---

## Условные обозначения
- [ ] – задача запланирована
- [V] – выполнено
- [~] – выполнено частично
- [-] – отложено
- [Х] – не будет реализовано