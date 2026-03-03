# gui.py
import tkinter as tk

def run_gui():
    app = Application()
    app.mainloop()

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DeepSeek Chat Archive Navigator")
        self.geometry("1200x800")
