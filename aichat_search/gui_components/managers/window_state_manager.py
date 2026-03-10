# aichat_search/gui_components/managers/window_state_manager.py

import json
import os
import tkinter as tk

from ..constants import (
    CONFIG_DIR,
    CONFIG_FILE,
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    MIN_LEFT_WIDTH,
    MIN_RIGHT_WIDTH,
    MIN_TOP_HEIGHT,
    MIN_BOTTOM_HEIGHT,
)

class WindowStateManager:
    """Отвечает за сохранение и загрузку геометрии окна, пропорций панелей,
       и ширины колонок деревьев чатов и сообщений."""

    def __init__(self, app):
        self.app = app
        self.config_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..', CONFIG_DIR))
        self.config_path = os.path.abspath(os.path.join(self.config_dir, CONFIG_FILE))

    def save(self):
        """Сохранить текущее состояние в JSON."""
        os.makedirs(self.config_dir, exist_ok=True)

        win_width = self.app.winfo_width()
        win_height = self.app.winfo_height()
        win_x = self.app.winfo_x()
        win_y = self.app.winfo_y()

        left_prop = self._get_sash_proportion(
            self.app.main_paned, 0, orient='horizontal'
        )
        top_prop = self._get_sash_proportion(
            self.app.right_paned, 0, orient='vertical'
        )
        # req_prop удалён, так как text_paned больше нет

        column_widths = self.app.left_tree.get_column_widths()
        tree_column_widths = self.app.tree_panel.get_column_widths()

        config = {
            "window_size": {"width": win_width, "height": win_height},
            "window_position": {"x": win_x, "y": win_y},
            "proportions": {
                "main_horizontal": left_prop,
                "right_vertical": top_prop,
            },
            "column_widths": column_widths,
            "tree_column_widths": tree_column_widths,
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

        win_size = config.get("window_size", {})
        width = win_size.get("width", DEFAULT_WIDTH)
        height = win_size.get("height", DEFAULT_HEIGHT)

        win_pos = config.get("window_position", {})
        x = win_pos.get("x")
        y = win_pos.get("y")

        if x is not None and y is not None:
            geometry = f"{width}x{height}+{x}+{y}"
        else:
            geometry = f"{width}x{height}"

        self.app.geometry(geometry)

        self.app.update_idletasks()

        props = config.get("proportions", {})
        if props:
            self.app.after(50, self._apply_proportions, props)

        col_widths = config.get("column_widths", {})
        if col_widths:
            self.app.left_tree.set_column_widths(col_widths)

        tree_widths = config.get("tree_column_widths", {})
        if tree_widths:
            self.app.tree_panel.set_column_widths(tree_widths)

    def _get_sash_proportion(self, paned, index, orient):
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
        left_prop = props.get("main_horizontal")
        if left_prop is not None:
            self._set_sash_proportion(
                self.app.main_paned, 0, left_prop,
                orient='horizontal',
                minsize1=MIN_LEFT_WIDTH,
                minsize2=MIN_RIGHT_WIDTH
            )

        top_prop = props.get("right_vertical")
        if top_prop is not None:
            self._set_sash_proportion(
                self.app.right_paned, 0, top_prop,
                orient='vertical',
                minsize1=MIN_TOP_HEIGHT,
                minsize2=MIN_BOTTOM_HEIGHT
            )

        # req_prop больше не применяем

    def _set_sash_proportion(self, paned, index, proportion, orient, minsize1, minsize2):
        if orient == 'horizontal':
            total = paned.winfo_width()
        else:
            total = paned.winfo_height()
        sash_width = paned.cget('sashwidth')
        available = total - sash_width
        desired = int(proportion * available)

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