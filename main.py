# main.py
import logging

from aichat_search.gui import run_gui

def main():
    logging.basicConfig(level=logging.DEBUG)
    run_gui()


if __name__ == "__main__":
    main()
