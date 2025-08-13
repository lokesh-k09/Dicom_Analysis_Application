# desktop_app/gui_app.py

import os
import zipfile
import threading
import queue
import shutil
import traceback
from pathlib import Path

# --- make tqdm safe in a windowed frozen app ---
# 1) disable progress bars (optional but safest)
os.environ.setdefault("TQDM_DISABLE", "1")

# 2) ensure sys.stdout / sys.stderr exist so tqdm can write if needed
import sys
class _NullStream:
    def write(self, *args, **kwargs): pass
    def flush(self): pass
    def isatty(self): return False
if sys.stdout is None:
    sys.stdout = _NullStream()
if sys.stderr is None:
    sys.stderr = _NullStream()

# --- plotting backend safe for frozen apps ---
import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

# IMPORTANT: absolute import so PyInstaller bundles it correctly
from desktop_app.process_utils import process_dat_file


def dat_gui_main():
    """
    Tkinter GUI for DAT PPM Processor.
    Wrapped in a function so we can run it in a child process from the main EXE.
    """
    # keep relative paths sane in dev/frozen
    try:
        os.chdir(Path(__file__).parent)
    except Exception:
        pass

    msg_queue: "queue.Queue[tuple[str, str | None]]" = queue.Queue()

    def safe_mkdir(p: str | Path):
        Path(p).mkdir(parents=True, exist_ok=True)

    def worker(input_dir: str, output_dir: str):
        # 1) gather .dat files
        try:
            files = [
                os.path.join(input_dir, f)
                for f in os.listdir(input_dir)
                if f.lower().endswith(".dat")
            ]
        except Exception as e:
            msg_queue.put(("error", f"Failed to list input dir: {e}"))
            msg_queue.put(("done", None))
            return

        if not files:
            msg_queue.put(("error", f"No .dat files in {input_dir}"))
            msg_queue.put(("done", None))
            return

        # 2) make QA folders (all inside user-chosen output_dir)
        qa_dir = os.path.join(output_dir, "QA")
        plotsdir = os.path.join(qa_dir, "PLOTS_PPM")
        exceldir = os.path.join(qa_dir, "Excels")
        for d in (qa_dir, plotsdir, exceldir):
            safe_mkdir(d)

        # error log file (per run)
        errlog_path = os.path.join(qa_dir, "error_trace.txt")
        try:
            with open(errlog_path, "w", encoding="utf-8") as _:
                pass  # truncate/create
        except Exception:
            errlog_path = None  # still show in GUI

        ppm_summary, fft_data_all, GA_labels = [], [], []

        # 3) process each file
        for f in files:
            base = os.path.basename(f)
            msg_queue.put(("log", f"▶ Processing: {base}"))
            try:
                summary, fftdata, ga = process_dat_file(f, plotsdir)

                if summary:
                    ppm_summary.append(summary)
                    fft_data_all.append(fftdata)
                    GA_labels.append(ga)
                    msg_queue.put(("log", f"   ✓ OK: {ga}"))
                else:
                    msg_queue.put(("log", f"   ⚠️ Skipped: no summary returned"))
            except Exception as e:
                # short message in GUI + last lines of traceback
                tb = traceback.format_exc().splitlines()
                tail = "\n".join(tb[-3:])
                msg_queue.put((
                    "log",
                    f"❌ Failed: {base} — {e}\n↳ Trace (last lines):\n{tail}\n"
                ))
                # full traceback to file
                if errlog_path:
                    try:
                        with open(errlog_path, "a", encoding="utf-8") as ef:
                            ef.write(f"\n[File] {base}\n")
                            ef.write(traceback.format_exc())
                            ef.write("\n" + "-" * 80 + "\n")
                    except Exception:
                        pass
                continue

        # 4) write Excel + radar plot if we have any summaries
        if ppm_summary:
            try:
                # DataFrames
                df_sum = pd.DataFrame(ppm_summary, columns=["CF", "FWHM Hz", "FWHM ppm"])
                df_sum.insert(0, "GA_Label", GA_labels)

                df_fft = pd.DataFrame(np.array(fft_data_all).T, columns=GA_labels)
                df_fft.insert(0, "SampleIdx", np.arange(1, len(fft_data_all[0]) + 1))

                # Excel
                excel_path = os.path.join(exceldir, "QA_Results.xlsx")
                with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                    df_sum.to_excel(writer, sheet_name="PPM_Summary", index=False)
                    df_fft.to_excel(writer, sheet_name="PPM_Info_full", index=False)

                # Radar/polar plot
                try:
                    angle_deg = np.array([float(lbl) for lbl in GA_labels])
                    idx = np.argsort(angle_deg)
                    angle_sorted = angle_deg[idx]
                    ppm_sorted = df_sum["FWHM ppm"].values[idx]
                    theta = np.deg2rad(np.append(angle_sorted, angle_sorted[0]))
                    r_ppm = np.append(ppm_sorted, ppm_sorted[0])
                    bound_ppm = 5.0 * np.ones_like(theta)

                    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"polar": True})
                    ax.plot(theta, r_ppm, "k-", linewidth=1)
                    ax.plot(theta, bound_ppm, "r-", linewidth=1)
                    ax.plot(theta[:-1], r_ppm[:-1], "g*", markersize=8)
                    ax.set_title("HOMOGENEITY v. GA", fontweight="bold", y=1.10)
                    ax.set_theta_zero_location("E")
                    ax.set_theta_direction(1)
                    ax.set_rlim(0, 10)
                    ax.set_rticks(np.arange(0, 11, 2))
                    ax.set_thetagrids(angle_sorted)

                    radar_path = os.path.join(plotsdir, "Homogeneity_vs_GA_POLAR_PPM.png")
                    fig.savefig(radar_path, dpi=150, bbox_inches="tight")
                    plt.close(fig)
                except Exception:
                    tb = traceback.format_exc().splitlines()
                    tail = "\n".join(tb[-3:])
                    msg_queue.put(("log", f"⚠️ Plot skipped.\n{tail}\n"))
                    if errlog_path:
                        try:
                            with open(errlog_path, "a", encoding="utf-8") as ef:
                                ef.write("\n[Plot Error]\n")
                                ef.write(traceback.format_exc())
                                ef.write("\n" + "-" * 80 + "\n")
                        except Exception:
                            pass

                # 5) zip everything
                zip_path = os.path.join(output_dir, "QA_Results.zip")
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for rd, _, fs in os.walk(qa_dir):
                        for fn in fs:
                            full = os.path.join(rd, fn)
                            zf.write(full, os.path.relpath(full, qa_dir))

                # cleanup QA folder
                shutil.rmtree(qa_dir, ignore_errors=True)

                msg_queue.put(("log", f"✅ Done! ZIP → {zip_path}"))
                msg_queue.put(("result", zip_path))
            except Exception:
                tb = traceback.format_exc().splitlines()
                tail = "\n".join(tb[-3:])
                msg_queue.put(("error", f"❌ Finalization failed.\n{tail}"))
                if errlog_path:
                    try:
                        with open(errlog_path, "a", encoding="utf-8") as ef:
                            ef.write("\n[Finalize Error]\n")
                            ef.write(traceback.format_exc())
                            ef.write("\n" + "-" * 80 + "\n")
                    except Exception:
                        pass
        else:
            msg_queue.put(("error", "⚠️ No valid files processed"))

        msg_queue.put(("done", None))

    def poll_queue():
        try:
            while True:
                tag, payload = msg_queue.get_nowait()
                if tag == "log":
                    log.insert(tk.END, payload + "\n")
                    log.see(tk.END)
                elif tag == "error":
                    log.insert(tk.END, payload + "\n")
                    log.see(tk.END)
                elif tag == "result":
                    messagebox.showinfo("Finished", f"{payload}")
                elif tag == "done":
                    run_btn.config(state=tk.NORMAL)
        except queue.Empty:
            pass
        finally:
            root.after(100, poll_queue)

    def on_run_clicked():
        in_dir = in_entry.get().strip()
        out_dir = out_entry.get().strip()
        if not (os.path.isdir(in_dir) and os.path.isdir(out_dir)):
            messagebox.showwarning("Missing", "Pick valid input & output folders.")
            return

        run_btn.config(state=tk.DISABLED)
        log.delete(1.0, tk.END)
        threading.Thread(target=worker, args=(in_dir, out_dir), daemon=True).start()

    def select_input_folder():
        d = filedialog.askdirectory(title="Select folder with .dat files")
        if d:
            in_entry.delete(0, tk.END)
            in_entry.insert(0, d)

    def select_output_folder():
        d = filedialog.askdirectory(title="Select output folder")
        if d:
            out_entry.delete(0, tk.END)
            out_entry.insert(0, d)

    # ─── Build GUI ──────────────────────────────────────────────────────────
    root = tk.Tk()
    root.title("DAT Processor")

    frm1 = tk.Frame(root)
    frm1.pack(fill=tk.X, padx=5, pady=5)
    tk.Button(frm1, text="Select input folder", command=select_input_folder).pack(side=tk.LEFT)
    in_entry = tk.Entry(frm1, width=50)
    in_entry.pack(side=tk.LEFT, padx=5)

    frm2 = tk.Frame(root)
    frm2.pack(fill=tk.X, padx=5, pady=5)
    tk.Button(frm2, text="Select output folder", command=select_output_folder).pack(side=tk.LEFT)
    out_entry = tk.Entry(frm2, width=50)
    out_entry.pack(side=tk.LEFT, padx=5)

    frm3 = tk.Frame(root)
    frm3.pack(fill=tk.X, padx=5, pady=5)
    run_btn = tk.Button(frm3, text="Run", command=on_run_clicked)
    run_btn.pack(side=tk.LEFT)
    tk.Button(frm3, text="Exit", command=root.destroy).pack(side=tk.LEFT, padx=5)

    log = scrolledtext.ScrolledText(root, height=20)
    log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    root.after(100, poll_queue)
    root.mainloop()


if __name__ == "__main__":
    dat_gui_main()
