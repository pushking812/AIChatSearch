
from aichat_search import main

def test_main_runs_without_error(monkeypatch):
    monkeypatch.setattr("aichat_search.main.run_gui", lambda: None)
    main.main()
