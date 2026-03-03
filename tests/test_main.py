
from deepseek import main

def test_main_runs_without_error(monkeypatch):
    monkeypatch.setattr("deepseek.main.run_gui", lambda: None)
    main.main()
