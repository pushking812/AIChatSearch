# deepseek/gui_components/window_state.py

"""Менеджер сохранения и восстановления состояния окна и панелей."""

import json
import os
import tkinter as tk

from .constants import (
    CONFIG_DIR, 
    CONFIG_FILE, 
    DEFAULT_HEIGHT, 
    DEFAULT_WIDTH, 
    MIN_LEFT_WIDTH, 
    MIN_RIGHT_WIDTH, 
    MIN_TOP_HEIGHT, 
    MIN_BOTTOM_HEIGHT, 
    MIN_REQUEST_HEIGHT, 
    MIN_RESPONSE_HEIGHT
    )

class WindowStateManager:
    """Отвечает за сохранение и загрузку геометрии окна и пропорций панелей."""

    def __init__(self, app):
        self.app = app
        self.config_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', CONFIG_DIR))
        print("windows_state", self.config_dir)
        self.config_path = os.path.abspath(os.path.join(self.config_dir, CONFIG_FILE))
        print("windows_state", self.config_path)
        
        # config_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', CONFIG_DIR))
        # self.session_path = os.path.abspath(os.path.join(config_dir, PKL_FILE))

    def save(self):
        """Сохранить текущее состояние в JSON."""
        os.makedirs(self.config_dir, exist_ok=True)

        win_width = self.app.winfo_width()
        win_height = self.app.winfo_height()

        # Вычисляем пропорции для каждой панели
        left_prop = self._get_sash_proportion(
            self.app.main_paned, 0, orient='horizontal'
        )
        top_prop = self._get_sash_proportion(
            self.app.right_paned, 0, orient='vertical'
        )
        req_prop = self._get_sash_proportion(
            self.app.text_paned, 0, orient='vertical'
        )

        config = {
            "window_size": {"width": win_width, "height": win_height},
            "proportions": {
                "main_horizontal": left_prop,
                "right_vertical": top_prop,
                "text_vertical": req_prop
            }
        }

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения состояния: {e}")

    def load_and_apply(self):
        """Загрузить состояние из JSON и применить к окну."""
        if not os.path.exists(self.config_path):
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки состояния: {e}")
            return

        # Восстанавливаем размер окна
        win_size = config.get("window_size", {})
        width = win_size.get("width", DEFAULT_WIDTH)
        height = win_size.get("height", DEFAULT_HEIGHT)
        self.app.geometry(f"{width}x{height}")

        self.app.update_idletasks()

        # Применяем пропорции
        props = config.get("proportions", {})
        if props:
            self.app.after(50, self._apply_proportions, props)

    def _get_sash_proportion(self, paned, index, orient):
        """Вычислить долю позиции саша относительно доступного пространства."""
        try:
            if orient == 'horizontal':
                pos = paned.sash_coord(index)[0]
                total = paned.winfo_width()
            else:
                pos = paned.sash_coord(index)[1]
                total = paned.winfo_height()
            sash_width = paned.cget('sashwidth')
            available = total - sash_width
            if available <= 0:
                return 0.25 if orient == 'horizontal' else 0.5
            return pos / available
        except:
            return 0.25 if orient == 'horizontal' else 0.5

    def _apply_proportions(self, props):
        """Применить пропорции с учётом минимальных размеров."""
        # Главная горизонтальная панель
        left_prop = props.get("main_horizontal")
        if left_prop is not None:
            self._set_sash_proportion(
                self.app.main_paned, 0, left_prop,
                orient='horizontal',
                minsize1=MIN_LEFT_WIDTH,
                minsize2=MIN_RIGHT_WIDTH
            )

        # Вертикальная панель справа
        top_prop = props.get("right_vertical")
        if top_prop is not None:
            self._set_sash_proportion(
                self.app.right_paned, 0, top_prop,
                orient='vertical',
                minsize1=MIN_TOP_HEIGHT,
                minsize2=MIN_BOTTOM_HEIGHT
            )

        # Текстовая панель
        req_prop = props.get("text_vertical")
        if req_prop is not None:
            self._set_sash_proportion(
                self.app.text_paned, 0, req_prop,
                orient='vertical',
                minsize1=MIN_REQUEST_HEIGHT,
                minsize2=MIN_RESPONSE_HEIGHT
            )

    def _set_sash_proportion(self, paned, index, proportion, orient, minsize1, minsize2):
        """Установить саш в соответствии с пропорцией и ограничениями."""
        if orient == 'horizontal':
            total = paned.winfo_width()
        else:
            total = paned.winfo_height()
        sash_width = paned.cget('sashwidth')
        available = total - sash_width
        desired = int(proportion * available)

        # Корректировка по минимальным размерам
        if desired < minsize1:
            desired = minsize1
        if available - desired < minsize2:
            desired = available - minsize2

        if desired <= 0 or desired >= available:
            return

        try:
            if orient == 'horizontal':
                paned.sash_place(index, desired, 0)
            else:
                paned.sash_place(index, 0, desired)
        except Exception as e:
            print(f"Ошибка установки саша {orient}: {e}")
