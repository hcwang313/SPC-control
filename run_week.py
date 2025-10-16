# src/spc/run_week.py
from typing import Optional
import yaml
from spc import charts

def run_week(week: str, cfg_path: Optional[str] = "spc_config.yaml") -> None:
    cfg = {}
    if cfg_path:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    charts.run_from_config(week=week, cfg=cfg)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--week", required=True, help="e.g., 20251007-20251014")
    parser.add_argument("--cfg", default="spc_config.yaml", help="path to YAML config")
    args = parser.parse_args()
    run_week(args.week, args.cfg)
