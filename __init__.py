"""
SPC Weekly Monitor Package
--------------------------
This package provides modules for generating weekly SPC (Statistical Process Control)
charts, calculating Cp/Cpk metrics, and compiling AOI SPD reports.

Modules:
- charts: main workflow for loading data, plotting, and exporting reports
- metrics: statistical functions (Cp, Cpk, sigma-level)
- panel: chart layout and PDF composition
- memory: data memory management between weeks
- utils: helpers for config loading and file handling
- run_week: lightweight CLI entrypoint
"""

__version__ = "1.0.0"

# 可选的快捷导入（方便在 notebook 里直接用）
from . import charts, metrics, panel, memory, utils
