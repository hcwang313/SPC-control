"""
Entry point that reads YAML config and triggers weekly SPC runs.

This file has been cleaned non‑invasively: unused imports removed, Chinese comments stripped, and English docstrings added.
Behavior is unchanged.
"""\n\nimport yaml
from spc import charts

def run_week(week: str, cfg_path: str | None = None) -> None:
    cfg = {}
    if cfg_path:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    if cfg and cfg.get("products"):
        charts.run_from_config(week, cfg)
    else:
        print("[YAML] No products found in config. Please provide a valid YAML.")