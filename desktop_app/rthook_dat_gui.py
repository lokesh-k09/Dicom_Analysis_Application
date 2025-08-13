# desktop_app/rthook_dat_gui.py
import sys, os, runpy, tempfile
from pathlib import Path

LOG = Path(os.environ.get("TEMP", ".")) / "dat_hook.log"
def log(msg: str):
    try:
        LOG.write_text((LOG.read_text(encoding="utf-8") if LOG.exists() else "") + msg + "\n", encoding="utf-8")
    except Exception:
        pass

def _is_dat_gui_invocation(argv):
    for a in argv[1:]:
        try:
            if Path(a).name.lower() == "gui_app.py":
                return True
        except Exception:
            pass
        if a == "--dat-gui":
            return True
    return False

log(f"[hook] argv={sys.argv!r}")
if _is_dat_gui_invocation(sys.argv):
    base = Path(getattr(sys, "_MEIPASS", os.getcwd()))
    gui_path = base / "gui_app.py"  # we bundle this as data in the spec
    log(f"[hook] trigger ✓  MEIPASS={base}  gui_exists={gui_path.exists()}  path={gui_path}")
    try:
        runpy.run_path(str(gui_path), run_name="__main__")
    except Exception as e:
        log(f"[hook] error: {e!r}")
    finally:
        os._exit(0)
else:
    log("[hook] not triggered")
