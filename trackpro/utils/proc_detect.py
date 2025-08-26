# trackpro/utils/proc_detect.py
import psutil

ASSETTO_PROCESSES = {"acs.exe"}  # Assetto Corsa main process (launched by CM or Steam)  # ref: Kunos forums & community docs

def is_assetto_running() -> bool:
    try:
        for p in psutil.process_iter(["name"]):
            n = (p.info.get("name") or "").lower()
            if n in ASSETTO_PROCESSES:
                return True
    except Exception:
        pass
    return False
