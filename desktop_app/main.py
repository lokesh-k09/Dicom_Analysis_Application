#!/usr/bin/env python3
"""
MRI DICOM Analysis Desktop Application
Main entry point for the desktop app
"""

import sys
import os
import logging
from pathlib import Path


def _set_working_dir():
    # Keep this only for data/assets; imports should be absolute.
    if hasattr(sys, "_MEIPASS"):
        os.chdir(sys._MEIPASS)
    else:
        os.chdir(Path(__file__).parent)


def main():
    _set_working_dir()

    # Imports are inside main to avoid side effects during multiprocessing spawn.
    from desktop_app.desktop_backend import backend
    from desktop_app.desktop_gui import MRIAnalysisApp
    import flet as ft

    # Configure logging (file + console).
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
    )

    app = MRIAnalysisApp(backend)
    ft.app(target=app.main, view=ft.AppView.FLET_APP)


if __name__ == "__main__":
    # REQUIRED for Windows/PyInstaller when using multiprocessing
    import multiprocessing

    multiprocessing.freeze_support()
    main()
