# desktop_gui.py
import sys
import os
import time
import json
import threading
import subprocess
from pathlib import Path

import requests
import pandas as pd
import flet as ft


class MRIAnalysisApp:
    def __init__(self, backend):
        self.backend = backend
        self.backend_url = "http://127.0.0.1:8000"
        self.server_running = False
        self.selected_folder = None

        # Results storage
        self.weekly_results = []
        self.nema_results = {}
        self.torso_results = {}

        # UI components
        self.page = None
        self.folder_text = None
        self.weekly_btn = None
        self.nema_btn = None
        self.torso_btn = None
        self.dat_btn = None
        self.results_container = None

        # Start backend server
        self.start_backend()

    # ---------- helpers ----------
    def _resource_path(self, name: str) -> Path:
        """Return absolute path to a bundled or source file."""
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
        return (base / name).resolve()

    def start_backend(self):
        """Start the backend server in a separate thread."""
        def run_backend():
            try:
                _, actual_port = self.backend.start_server()
                self.backend_url = f"http://127.0.0.1:{actual_port}"
                time.sleep(2)  # give server a sec to boot
                self.server_running = True
                print(f"Backend server started on port {actual_port}")
            except Exception as e:
                print(f"Failed to start backend: {e}")
                self.server_running = False

        threading.Thread(target=run_backend, daemon=True).start()

        # Wait briefly for server
        for _ in range(10):
            try:
                requests.get(f"{self.backend_url}/", timeout=1)
                self.server_running = True
                break
            except Exception:
                time.sleep(1)

    # ---------- file pick & upload ----------
    def pick_folder(self, e):
        def get_directory_result(ev: ft.FilePickerResultEvent):
            if ev.path:
                self.selected_folder = ev.path
                self.folder_text.value = ev.path
                if self.page:
                    self.page.update()

        fp = ft.FilePicker(on_result=get_directory_result)
        self.page.overlay.append(fp)
        self.page.update()
        fp.get_directory_path()

    def clear_previous_results(self):
        self.weekly_results = None
        self.nema_results = None
        self.torso_results = None
        if self.results_container:
            self.results_container.controls.clear()
            if self.page:
                self.page.update()

    def upload_files(self, folder_path):
        """Upload files to backend while preserving folder structure."""
        self.clear_previous_results()

        files = []
        for root, _, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel = os.path.relpath(file_path, folder_path)
                files.append(("files", (rel, open(file_path, "rb"))))

        try:
            resp = requests.post(f"{self.backend_url}/upload-folder/", files=files)
        finally:
            # Always close file handles
            for _, (_, fobj) in files:
                fobj.close()

        return resp.json()

    # ---------- processors ----------
    def process_weekly(self, e):
        if not self.selected_folder:
            return

        def run():
            try:
                self.weekly_btn.disabled = True
                self.weekly_btn.text = "Processing..."
                if self.page: self.page.update()

                self.upload_files(self.selected_folder)
                r = requests.post(f"{self.backend_url}/process-folder/", timeout=300)

                if r.status_code == 200:
                    self.weekly_results = r.json().get("results", [])
                else:
                    self.weekly_results = []
                    print(f"Processing failed: {r.status_code} {r.text}")

                self.update_results_display()
            except Exception as ex:
                print(f"Weekly error: {ex}")
            finally:
                self.weekly_btn.disabled = False
                self.weekly_btn.text = "Process Weekly"
                if self.page: self.page.update()

        threading.Thread(target=run, daemon=True).start()

    def process_nema(self, e):
        if not self.selected_folder:
            return

        def run():
            try:
                self.nema_btn.disabled = True
                self.nema_btn.text = "Processing..."
                if self.page: self.page.update()

                self.upload_files(self.selected_folder)
                r = requests.post(f"{self.backend_url}/process-nema-body/", timeout=300)

                if r.status_code == 200:
                    self.nema_results = r.json().get("results", {})
                else:
                    self.nema_results = {}
                    print(f"NEMA failed: {r.status_code} {r.text}")

                self.update_results_display()
            except Exception as ex:
                print(f"NEMA error: {ex}")
            finally:
                self.nema_btn.disabled = False
                self.nema_btn.text = "Process NEMA Body"
                if self.page: self.page.update()

        threading.Thread(target=run, daemon=True).start()

    def process_torso(self, e):
        if not self.selected_folder:
            return

        def run():
            try:
                self.torso_btn.disabled = True
                self.torso_btn.text = "Processing..."
                if self.page: self.page.update()

                self.upload_files(self.selected_folder)
                r = requests.post(f"{self.backend_url}/process-torso/", timeout=300)

                if r.status_code == 200:
                    self.torso_results = r.json()
                else:
                    self.torso_results = {"combined_results": [], "element_results": []}
                    print(f"Torso failed: {r.status_code} {r.text}")

                self.update_results_display()
            except Exception as ex:
                print(f"Torso error: {ex}")
            finally:
                self.torso_btn.disabled = False
                self.torso_btn.text = "Process Torso"
                if self.page: self.page.update()

        threading.Thread(target=run, daemon=True).start()

    # ---------- .DAT Processor launcher ----------
    def open_dat_gui(self, e):
        """Launch your Tkinter .DAT Processor (gui_app.py) in a separate window."""
        try:
            gui_path = self._resource_path("gui_app.py")
            creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform.startswith("win") else 0
            subprocess.Popen(
                [sys.executable, str(gui_path)],
                cwd=str(gui_path.parent),
                creationflags=creationflags
            )
        except Exception as ex:
            print(f"Failed to launch .DAT GUI: {ex}")

    # ---------- results table & downloads ----------
    def create_table(self, data, headers, title, bgcolor="#1976d2"):
        if not data:
            return ft.Container()

        header_cells = [
            ft.DataCell(ft.Text(h, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD))
            for h in headers
        ]
        header_row = ft.DataRow(cells=header_cells, color=bgcolor)

        rows = [header_row]
        for item in data:
            cells = []
            for h in headers:
                val = item.get(h, "")
                if isinstance(val, float):
                    cells.append(ft.DataCell(ft.Text(f"{val:.2f}")))
                else:
                    cells.append(ft.DataCell(ft.Text(str(val))))
            rows.append(ft.DataRow(cells=cells))

        return ft.Column(
            [
                ft.Text(title, size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLACK),
                ft.DataTable(
                    columns=[ft.DataColumn(ft.Text("")) for _ in headers],
                    rows=rows,
                    border=ft.border.all(1, ft.Colors.GREY_400),
                    bgcolor=ft.Colors.WHITE,
                    heading_row_color=bgcolor,
                ),
            ],
            spacing=10,
        )

    def download_weekly_results(self, e):
        try:
            r = requests.get(f"{self.backend_url}/download-metrics", timeout=30)
            if r.status_code == 200:
                downloads = os.path.join(os.path.expanduser("~"), "Downloads")
                fp = os.path.join(downloads, "weekly_metrics.xlsx")
                with open(fp, "wb") as f:
                    f.write(r.content)
                print(f"Weekly results downloaded to: {fp}")
            else:
                print(f"Download failed: {r.status_code}")
        except Exception as ex:
            print(f"Download error: {ex}")

    def download_nema_results(self, e):
        try:
            r = requests.get(f"{self.backend_url}/download-nema-body", timeout=30)
            if r.status_code == 200:
                downloads = os.path.join(os.path.expanduser("~"), "Downloads")
                fp = os.path.join(downloads, "nema_body_metrics.xlsx")
                with open(fp, "wb") as f:
                    f.write(r.content)
                print(f"NEMA results downloaded to: {fp}")
            else:
                print(f"Download failed: {r.status_code}")
        except Exception as ex:
            print(f"Download error: {ex}")

    def download_torso_results(self, e):
        try:
            r = requests.get(f"{self.backend_url}/download-torso", timeout=30)
            if r.status_code == 200:
                downloads = os.path.join(os.path.expanduser("~"), "Downloads")
                fp = os.path.join(downloads, "torso_coil_analysis.xlsx")
                with open(fp, "wb") as f:
                    f.write(r.content)
                print(f"Torso results downloaded to: {fp}")
            else:
                print(f"Download failed: {r.status_code}")
        except Exception as ex:
            print(f"Download error: {ex}")

    def open_output_folder(self, e):
        """Query backend for outputs folder path (if endpoint exists)."""
        try:
            r = requests.get(f"{self.backend_url}/output-folder-path", timeout=10)
            if r.status_code == 200:
                info = r.json()
                p = info.get("path")
                if p and info.get("exists", False):
                    print(f"Output folder: {p}")
                else:
                    print("Output folder does not exist yet.")
            else:
                print("Failed to get output folder path.")
        except Exception as ex:
            print(f"Error retrieving folder info: {ex}")

    def update_results_display(self):
        if not self.results_container:
            return

        self.results_container.controls.clear()

        # Weekly
        if self.weekly_results is not None:
            if self.weekly_results:
                self.results_container.controls.append(
                    self.create_table(
                        self.weekly_results,
                        ["Filename", "Mean", "Min", "Max", "Sum", "StDev", "SNR", "PIU"],
                        "Weekly Processing Results",
                        ft.Colors.BLUE_600,
                    )
                )
            else:
                self.results_container.controls.append(
                    ft.Text(
                        "Weekly Processing: No valid DICOM files found",
                        size=16,
                        color=ft.Colors.ORANGE_600,
                        weight=ft.FontWeight.BOLD,
                    )
                )
            self.results_container.controls.append(
                ft.ElevatedButton(
                    "Download Weekly Results",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=self.download_weekly_results,
                    bgcolor=ft.Colors.BLUE_600,
                    color=ft.Colors.WHITE,
                    width=200,
                )
            )

        # NEMA
        if self.nema_results is not None:
            if self.nema_results:
                for group_name, group_data in self.nema_results.items():
                    if group_data:
                        self.results_container.controls.append(
                            self.create_table(
                                group_data,
                                ["Orientation", "Type", "Mean", "Min", "Max", "Sum", "StDev", "SNR", "PIU"],
                                f"NEMA Body Results - {group_name}",
                                ft.Colors.PURPLE_600,
                            )
                        )
                if not any(self.nema_results.values()):
                    self.results_container.controls.append(
                        ft.Text(
                            "NEMA Body Processing: No valid DICOM image files found",
                            size=16,
                            color=ft.Colors.ORANGE_600,
                            weight=ft.FontWeight.BOLD,
                        )
                    )
            else:
                self.results_container.controls.append(
                    ft.Text(
                        "NEMA Body Processing: No valid DICOM image files found",
                        size=16,
                        color=ft.Colors.ORANGE_600,
                        weight=ft.FontWeight.BOLD,
                    )
                )
            self.results_container.controls.append(
                ft.ElevatedButton(
                    "Download NEMA Body Results",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=self.download_nema_results,
                    bgcolor=ft.Colors.PURPLE_600,
                    color=ft.Colors.WHITE,
                    width=220,
                )
            )

        # Torso
        if self.torso_results is not None:
            has_results = False

            if self.torso_results.get("combined_results"):
                self.results_container.controls.append(
                    self.create_table(
                        self.torso_results["combined_results"],
                        ["Region", "Signal Max", "Signal Min", "Signal Mean", "Noise SD", "SNR", "Uniformity"],
                        "Torso Results - Combined Views",
                        ft.Colors.GREEN_600,
                    )
                )
                has_results = True

            if self.torso_results.get("element_results"):
                self.results_container.controls.append(
                    self.create_table(
                        self.torso_results["element_results"],
                        ["Element", "Signal Mean", "Noise SD", "SNR"],
                        "Torso Results - Individual Elements",
                        ft.Colors.GREEN_600,
                    )
                )
                has_results = True

            if not has_results:
                self.results_container.controls.append(
                    ft.Text(
                        "Torso Processing: No valid DICOM files found",
                        size=16,
                        color=ft.Colors.ORANGE_600,
                        weight=ft.FontWeight.BOLD,
                    )
                )

            self.results_container.controls.append(
                ft.ElevatedButton(
                    "Download Torso Results",
                    icon=ft.Icons.DOWNLOAD,
                    on_click=self.download_torso_results,
                    bgcolor=ft.Colors.GREEN_600,
                    color=ft.Colors.WHITE,
                    width=200,
                )
            )

        # Open output folder button (if anything has been shown)
        if (
            self.weekly_results is not None
            or self.nema_results is not None
            or self.torso_results is not None
        ):
            self.results_container.controls.append(
                ft.Container(
                    content=ft.ElevatedButton(
                        "Open Output Folder",
                        icon=ft.Icons.FOLDER_OPEN,
                        on_click=self.open_output_folder,
                        bgcolor=ft.Colors.AMBER_600,
                        color=ft.Colors.WHITE,
                        width=200,
                    ),
                    margin=ft.margin.only(top=20),
                )
            )

        if self.page:
            self.page.update()

    # ---------- UI ----------
    def main(self, page: ft.Page):
        self.page = page
        page.title = "MRI DICOM Analysis"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.window_width = 1200
        page.window_height = 800
        page.window_resizable = True
        page.padding = 20
        page.bgcolor = ft.Colors.GREY_100

        self.folder_text = ft.Text("No folder selected", size=14, color=ft.Colors.GREY_600)

        self.weekly_btn = ft.ElevatedButton(
            "Process Weekly",
            on_click=self.process_weekly,
            bgcolor=ft.Colors.BLUE_600,
            color=ft.Colors.WHITE,
            width=200,
            height=50,
        )
        self.nema_btn = ft.ElevatedButton(
            "Process NEMA Body",
            on_click=self.process_nema,
            bgcolor=ft.Colors.PURPLE_600,
            color=ft.Colors.WHITE,
            width=200,
            height=50,
        )
        self.torso_btn = ft.ElevatedButton(
            "Process Torso",
            on_click=self.process_torso,
            bgcolor=ft.Colors.GREEN_600,
            color=ft.Colors.WHITE,
            width=200,
            height=50,
        )
        # NEW: .DAT Processor button
        self.dat_btn = ft.ElevatedButton(
            "DAT PPM Processor",
            on_click=self.open_dat_gui,
            bgcolor=ft.Colors.ORANGE_600,
            color=ft.Colors.WHITE,
            width=200,
            height=50,
        )

        self.results_container = ft.Column(spacing=20, scroll=ft.ScrollMode.AUTO, expand=True)

        page.add(
            ft.Column(
                [
                    ft.Text(
                        "MRI DICOM Analysis",
                        size=32,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLACK,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.ElevatedButton(
                                            "Browse Folder",
                                            icon=ft.Icons.FOLDER_OPEN,
                                            on_click=self.pick_folder,
                                            bgcolor=ft.Colors.BLUE_600,
                                            color=ft.Colors.WHITE,
                                        ),
                                        ft.Container(content=self.folder_text, expand=True, padding=10),
                                    ]
                                )
                            ]
                        ),
                        bgcolor=ft.Colors.WHITE,
                        padding=20,
                        border_radius=10,
                        margin=ft.margin.only(bottom=20),
                    ),
                    # Buttons row (now has 4 buttons)
                    ft.Container(
                        content=ft.Row(
                            [self.weekly_btn, self.nema_btn, self.torso_btn, self.dat_btn],
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=20,
                        ),
                        margin=ft.margin.only(bottom=20),
                    ),
                    ft.Container(
                        content=self.results_container,
                        bgcolor=ft.Colors.WHITE,
                        padding=20,
                        border_radius=10,
                        expand=True,
                    ),
                ],
                spacing=0,
                expand=True,
            )
        )


def main():
    from desktop_backend import backend
    app = MRIAnalysisApp(backend)
    # Use the app's main as target (avoid recursion)
    ft.app(target=app.main, view=ft.AppView.FLET_APP)


if __name__ == "__main__":
    main()
