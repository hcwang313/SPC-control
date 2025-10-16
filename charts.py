"""
Chart orchestration: load data, compute SPC metrics, and render I‑MR panels.
"""

import os
import json
from typing import List, Optional, Dict, Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from .utils import get_ylabel
from .metrics import sigma_to_risk, safe_sigma_text
from .panel import render_text_panel, print_panel_lines
from .memory import MemoryStore

# ----------------- Memory management -----------------
def _ensure_memory(results_dir: str) -> MemoryStore:
    # Memory lives under .../Results/_memory_global/
    root_results = os.path.dirname(os.path.dirname(results_dir))
    mem_dir = os.path.join(root_results, "_memory_global")
    os.makedirs(mem_dir, exist_ok=True)
    return MemoryStore(os.path.join(mem_dir, "spc_memory.json"))

# ----------------- Last-sigma (persisted) -----------------
def _last_sigma_store_path(results_dir: str) -> str:
    root_results = os.path.dirname(os.path.dirname(results_dir))
    mem_dir = os.path.join(root_results, "_memory_global")
    os.makedirs(mem_dir, exist_ok=True)
    return os.path.join(mem_dir, "last_sigma_simple.json")

def _load_last_sigma(results_dir: str, product: str, feature: str):
    path = _last_sigma_store_path(results_dir)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(f"{product}|{feature}")
    except Exception:
        return None

def _save_last_sigma(results_dir: str, product: str, feature: str, sigma: float) -> None:
    path = _last_sigma_store_path(results_dir)
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data[f"{product}|{feature}"] = float(sigma)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

# ----------------- X-axis -----------------
def _apply_xaxis_with_blank(ax, n_points: int):
    step = 1 if n_points <= 20 else (2 if n_points <= 50 else 5)
    xmax = n_points + step
    ticks = list(range(1, n_points + 1, step))
    if ticks and ticks[-1] != n_points:
        ticks.append(n_points)
    elif not ticks:
        ticks = [n_points]
    ax.set_xlim(1, xmax)
    ax.set_xticks(ticks)

# ================= I-MR =================
def run_imr_spc(
    file_path: str,
    display_name: str,
    results_dir: str,
    product_name: str = "",
    cfg: Optional[Dict[str, Any]] = None,
    need_ual_lal: bool = False,
) -> None:
    if not os.path.exists(file_path):
        print(f"no data points in the {display_name}")
        return

    cfg = cfg or {}
    threshold = int(cfg.get("threshold", 20))
    history_strategy = (cfg.get("history_strategy") or "all").strip().lower()
    y_overrides: Optional[Dict[str, str]] = cfg.get("y_label_overrides") if isinstance(cfg.get("y_label_overrides"), dict) else None

    mem = _ensure_memory(results_dir)

    df = pd.read_excel(file_path, sheet_name=0)
    x = df.iloc[:, 0]
    y = df.iloc[:, 1]

    # Use this week's limits from Excel
    lsl = df.iloc[0, 31]; usl = df.iloc[0, 33]
    lcl = df.iloc[0, 7];  ucl = df.iloc[0, 3]
    if lsl > usl: lsl, usl = usl, lsl
    if lcl > ucl: lcl, ucl = ucl, lcl

    # special: optionally read UAL/LAL
    ual = lal = None
    if need_ual_lal:
        try:
            ual = df.iloc[0, 25]  # UAL
            lal = df.iloc[0, 27]  # LAL
        except Exception:
            pass

    week = os.path.basename(os.path.dirname(file_path))
    product = product_name or "Product"
    feature = display_name

    # Read previously saved "last plotted sigma" (true previous)
    last_plotted_sigma = _load_last_sigma(results_dir, product, feature)

    cur_vals = y.tolist()

    combined_vals: List[float] = cur_vals
    used_hist_vals: List[float] = []
    used_hist_weeks: List[str] = []

    if len(cur_vals) < threshold:
        need = None if history_strategy != "fill_to_threshold" else max(threshold - len(cur_vals), 0)
        weeks_used, hist_vals = mem.take_imr_until(product, feature, need=need, exclude_week=week)
        used_hist_vals = hist_vals
        used_hist_weeks = weeks_used
        combined_vals = hist_vals + cur_vals
        if len(combined_vals) < threshold:
            mem.add_imr_points(
                product, feature, week,
                ids=list(map(str, x.tolist())),
                values=cur_vals
            )
            print(
                f"Accumulating '{product} | {feature}': "
                f"current({len(cur_vals)}) + history({len(hist_vals)}) "
                f"= {len(combined_vals)}/{threshold} points. No chart yet."
            )
            return

    y_series = np.asarray(combined_vals, dtype=float)
    mean = y_series.mean()
    std  = y_series.std(ddof=1)
    cp   = (usl - lsl) / (6 * std) if std > 0 else float('inf')
    cpk  = min((usl - mean)/(3*std), (mean - lsl)/(3*std)) if std > 0 else float('inf')
    sigma_level = round(cpk * 3, 3) if np.isfinite(cpk) else float('inf')
    risk_level  = sigma_to_risk(sigma_level)

    last_sigma_text = safe_sigma_text(last_plotted_sigma)

    if used_hist_weeks:
        hist_range = (
            used_hist_weeks[0] if used_hist_weeks[0] == used_hist_weeks[-1]
            else f"{used_hist_weeks[0]} … {used_hist_weeks[-1]}"
        )
        note_src = f"Data source: memory({len(used_hist_vals)}) from {hist_range} | current({len(cur_vals)}) from {week}"
    else:
        note_src = f"Data source: current({len(cur_vals)}) from {week}"

    ooc_mask = (y_series > ucl) | (y_series < lcl)
    ooc_ids  = [i+1 for i, flag in enumerate(ooc_mask) if flag]
    x_plot   = list(range(1, len(y_series) + 1))

    summary_lines = [
        f"--- {feature} (I-MR SPC) ---",
        f"Mean: {mean:.3f} | Std Dev: {std:.3f}",
        f"USL: {usl:.3f} | LSL: {lsl:.3f}",
        f"UCL: {ucl:.3f} | LCL: {lcl:.3f}",
    ]
    if ual is not None and lal is not None:
        summary_lines.append(f"UAL: {ual:.3f} | LAL: {lal:.3f}")
    summary_lines += [
        f"Cp: {cp:.3f} | Cpk: {cpk:.3f}",
        f"Sigma Level (≈ Cpk × 3): {sigma_level}",
        f"Risk Level: {risk_level}",
        f"Last Sigma Level: {last_sigma_text}",
        note_src,
        f"OOC points: {ooc_ids if ooc_ids else 'None'}"
    ]
    print(); print_panel_lines(summary_lines)

    # Plot
    fig, (ax_plot, ax_text) = plt.subplots(ncols=2, figsize=(14,6), gridspec_kw={'width_ratios':[3,2]})
    ok_x  = [i for i in x_plot if i not in ooc_ids]
    ok_y  = [y_series[i-1] for i in ok_x]
    ooc_y = [y_series[i-1] for i in ooc_ids]
    ax_plot.scatter(ok_x, ok_y, color='black')
    if ooc_ids:
        ax_plot.scatter(ooc_ids, ooc_y, color='red')
    ax_plot.plot(x_plot, y_series, linestyle='--', color='black', alpha=0.7)
    ax_plot.axhline(mean, color='green', linestyle='--',  label='Mean')
    ax_plot.axhline(ucl, color='red', linestyle='-.', label='UCL')
    ax_plot.axhline(lcl, color='red', linestyle='-.', label='LCL')
    ax_plot.axhline(lsl, color='blue', linestyle='--', label='LSL')
    ax_plot.axhline(usl, color='blue', linestyle='--', label='USL')
    if ual is not None and lal is not None:
        ax_plot.axhline(ual, color='darkgoldenrod', linestyle='--', label='UAL')
        ax_plot.axhline(lal, color='darkgoldenrod', linestyle='--', label='LAL')
    ax_plot.set_xlabel("Wafer/Subgroup Number")
    ax_plot.set_ylabel(get_ylabel(feature, y_overrides))
    ax_plot.set_title(f"{feature} - I-MR SPC Chart")
    ax_plot.grid(True, alpha=0.3); ax_plot.legend()
    _apply_xaxis_with_blank(ax_plot, len(x_plot))

    render_text_panel(ax_text, summary_lines)
    fig.tight_layout()
    os.makedirs(results_dir, exist_ok=True)
    fig.savefig(os.path.join(results_dir, feature + ".png"), dpi=300, bbox_inches='tight')
    plt.show(); plt.close(fig)

    # Persist the sigma we just plotted → becomes "Last Sigma" for the next run
    _save_last_sigma(results_dir, product, feature, sigma_level)

    # Per rule: clear feature memory after plotting with ≥threshold combined points
    mem.clear_feature(product, feature)

# ================= Batch entry from config =================
def run_product(product_name: str, data_dir: str, results_dir: str, imr_files: list[str]) -> None:
    # Backward compatibility for legacy callers (without YAML): unchanged
    os.makedirs(results_dir, exist_ok=True)
    print(f"\n===== RUNNING PRODUCT: {product_name} =====")
    for fname in imr_files:
        from_path = os.path.join(data_dir, fname + ".xlsx")
        run_imr_spc(from_path, fname, results_dir, product_name=product_name)

def run_from_config(week: str, cfg: Dict[str, Any]) -> None:
    data_root = cfg.get("data_root") or r"C:\\Users\\Hancheng_Wang\\Desktop\\Hancheng\\SPD\\Weekly SPC Monitor Report\\Data"
    result_root = cfg.get("result_root") or r"C:\\Users\\Hancheng_Wang\\Desktop\\Hancheng\\SPD\\Weekly SPC Monitor Report\\Results"
    products = cfg.get("products") or []

    for prod in products:
        name = prod.get("name") or "Product"
        data_subdir = prod.get("data_subdir") or name
        results_subdir = prod.get("results_subdir") or name
        features = prod.get("features") or []
        data_dir = os.path.join(data_root, data_subdir, week)
        results_dir = os.path.join(result_root, results_subdir, week)
        os.makedirs(results_dir, exist_ok=True)
        print(f"\n===== RUNNING PRODUCT: {name} =====")
        for f in features:
            display_name = f.get("display_name") or f.get("file_stem")
            stem = f.get("file_stem") or display_name
            need_ual_lal = bool(f.get("need_ual_lal", False))
            from_path = os.path.join(data_dir, stem + ".xlsx")
            run_imr_spc(
                from_path,
                display_name,
                results_dir,
                product_name=name,
                cfg=cfg,
                need_ual_lal=need_ual_lal,
            )