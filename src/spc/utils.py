"""
Utilities: week parsing, X‑axis ticks, and Y‑axis label mapping.
"""

from typing import Optional, Tuple, List, Dict
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

def parse_week_range(folder_name: str) -> Tuple[Optional[str], Optional[str]]:
    """'YYYYMMDD-YYYYMMDD' -> (start_str, end_str) or (None, None) if invalid."""
    try:
        a, b = folder_name.split("-")
        datetime.strptime(a, "%Y%m%d")
        datetime.strptime(b, "%Y%m%d")
        return a, b
    except Exception:
        return None, None

def prev_week_ranges(current_data_dir: str) -> List[str]:
    """
    From a data dir that ends with 'YYYYMMDD-YYYYMMDD', return up to two
    previous ranges: [start-7_to_start, start-14_to_start-7].
    """
    base = os.path.basename(current_data_dir)
    s, e = parse_week_range(base)
    if not s or not e:
        return []
    start = datetime.strptime(s, "%Y%m%d").date()
    p1 = (start - timedelta(days=7), start)
    p2 = (start - timedelta(days=14), start - timedelta(days=7))
    def fmt(a, b): return a.strftime("%Y%m%d") + "-" + b.strftime("%Y%m%d")
    return [fmt(*p1), fmt(*p2)]

def apply_xaxis(ax: plt.Axes, n: int) -> None:
    if n <= 20:
        step = 1
    elif n <= 50:
        step = 2
    else:
        step = 5

    xmax = n + step
    ticks = list(range(1, n + 1, step))
    if ticks[-1] != n:
        ticks.append(n)

    ax.set_xlim(1, xmax)
    ax.set_xticks(ticks)

def get_ylabel(display_name: str, overrides: Optional[Dict[str, str]] = None) -> str:
    if overrides:
        # case-insensitive exact match
        for k, v in overrides.items():
            if k.strip().lower() == display_name.strip().lower():
                return v
    name = display_name.lower()
    if "pl" in name: return "PL (nm)"
    if "mesa" in name and "width" in name: return "Mesa Width (\u03bcm)"
    if "etch" in name or "depth" in name: return "Mesa Depth (\u03bcm)"
    if "thickness" in name: return "Final Thickness (\u03bcm)"
    return display_name
