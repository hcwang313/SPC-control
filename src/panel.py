"""
Layout helpers for the text panel and colored console printing.
"""

from typing import List
import matplotlib.pyplot as plt

def render_text_panel(ax: plt.Axes, lines: List[str], fontsize=10, line_spacing=1.25) -> None:
    """Right-side text panel; Sigma/Risk red; Last Sigma blue."""
    ax.axis('off')
    y = 0.98
    dy = 0.045 * (fontsize/10) * (line_spacing/1.25)
    for line in lines:
        lower = line.strip().lower()
        if lower.startswith('sigma level') or lower.startswith('risk level'):
            color = 'red'
        elif lower.startswith('last sigma level'):
            color = 'blue'
        else:
            color = 'black'
        ax.text(0.02, y, line, fontsize=fontsize, family='monospace',
                va='top', ha='left', color=color, transform=ax.transAxes)
        y -= dy

def print_panel_lines(lines: List[str]) -> None:
    """Console: Sigma/Risk red; Last Sigma blue."""
    for line in lines:
        head = line.strip().lower()
        if head.startswith('sigma level') or head.startswith('risk level'):
            print(f"\033[91m{line}\033[0m")
        elif head.startswith('last sigma level'):
            print(f"\033[94m{line}\033[0m")
        else:
            print(line)
