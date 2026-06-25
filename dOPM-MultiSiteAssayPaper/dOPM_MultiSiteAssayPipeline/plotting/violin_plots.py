"""
analyze_cross_site_violin_plots.py
----------------------------------
Create matched violin plots for:

1) Spheroid size
   - per-spheroid value = number of objects per (Well_ID, tile, Condition)

2) Cyt/Nuc sensor ratio
   - per-spheroid value = median cyt_nuc_ratio_sensor per (Well_ID, tile, Condition)

For each metric:
- 6 conditions
- 4 sites per condition
- violin = distribution of per-spheroid values
- dots = individual spheroids
- horizontal lines = Q1, median, Q3

Designed to match the general sizing/font style of the earlier scripts.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# ---------------------------------------------------------------------
# Input configuration
# ---------------------------------------------------------------------
files_with_mappings = [
    {
        "file_path": r'./data/IRB/main_quantification.csv',
        "row_to_condition_mapping": {
            'B': 'DMSO',
            'C': '100 nM TPA',
            'D': '20 nM Binimetinib',
            'E': '60 nM Binimetinib',
            'F': '200 nM Binimetinib',
            'G': '3.5 µM Binimetinib'
        },
        "label_anon": "1"
    },
    {
        "file_path": r'./data/IGC/main_quantification.csv',
        "row_to_condition_mapping": {
            'B': 'DMSO',
            'G': '100 nM TPA',
            'F': '20 nM Binimetinib',
            'E': '60 nM Binimetinib',
            'D': '200 nM Binimetinib',
            'C': '3.5 µM Binimetinib'
        },
        "label_anon": "2"
    },
    {
        "file_path": r'./data/Crick/main_quantification.csv',
        "row_to_condition_mapping": {
            'B': 'DMSO',
            'C': '100 nM TPA',
            'D': '20 nM Binimetinib',
            'E': '60 nM Binimetinib',
            'F': '200 nM Binimetinib',
            'G': '3.5 µM Binimetinib'
        },
        "label_anon": "3"
    },
    {
        "file_path": r'./data/ICR/main_quantification.csv',
        "row_to_condition_mapping": {
            'B': 'DMSO',
            'C': '100 nM TPA',
            'D': '20 nM Binimetinib',
            'E': '60 nM Binimetinib',
            'F': '200 nM Binimetinib',
            'G': '3.5 µM Binimetinib'
        },
        "label_anon": "4"
    }
]

condition_order = [
    '100 nM TPA',
    'DMSO',
    '20 nM Binimetinib',
    '60 nM Binimetinib',
    '200 nM Binimetinib',
    '3.5 µM Binimetinib'
]

site_order = ['1', '2', '3', '4']
site_colors = {
    '1': 'blue',
    '2': 'magenta',
    '3': 'green',
    '4': 'red'
}

# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------
def extract_row(filename):
    """Extract row letter (A–G) from filename like B3_tile_0_fused_tp_0..."""
    match = re.match(r'^([A-Z])\d+_tile_\d+_fused_tp_\d+', str(filename))
    return match.group(1) if match else None

def extract_well(filename):
    """Extract full well name (e.g. B3, C6)."""
    match = re.match(r'^([A-Z]\d+)_tile_\d+_fused_tp_\d+', str(filename))
    return match.group(1) if match else None

def wrap_label(label):
    """Wrap long labels for plotting."""
    return label.replace(' Binimetinib', '\nBinimetinib')

def clean_condition_text(s):
    """Remove accidental trailing spaces and normalize text."""
    if pd.isna(s):
        return s
    return str(s).strip()

# ---------------------------------------------------------------------
# Load and prepare per-spheroid datasets
# ---------------------------------------------------------------------
all_spheroid_size = []
all_sensor_ratio = []

for file_info in files_with_mappings:
    df = pd.read_csv(file_info["file_path"]).copy()
    mapping = {k: clean_condition_text(v) for k, v in file_info["row_to_condition_mapping"].items()}
    site_label = file_info["label_anon"]

    df['Row_Letter'] = df['filename'].apply(extract_row)
    df['Well_ID'] = df['filename'].apply(extract_well)
    df['Condition'] = df['Row_Letter'].map(mapping)
    df['Condition'] = df['Condition'].apply(clean_condition_text)

    df = df[df['Condition'].isin(condition_order)].copy()

    # -------------------------
    # Per-spheroid size
    # -------------------------
    spheroid_sizes = (
        df.groupby(['Well_ID', 'tile', 'Condition'])['filename']
        .count()
        .reset_index(name='value')
    )
    spheroid_sizes['Site'] = site_label
    spheroid_sizes['Metric'] = 'spheroid_size'
    all_spheroid_size.append(spheroid_sizes)

    # -------------------------
    # Per-spheroid biosensor ratio
    # -------------------------
    grouped_ratio = (
        df.groupby(['Well_ID', 'tile', 'Condition'])['cyt_nuc_ratio_sensor']
        .median()
        .reset_index(name='value')
    )
    grouped_ratio['Site'] = site_label
    grouped_ratio['Metric'] = 'cyt_nuc_ratio_sensor'
    all_sensor_ratio.append(grouped_ratio)

spheroid_size_df = pd.concat(all_spheroid_size, ignore_index=True)
sensor_ratio_df = pd.concat(all_sensor_ratio, ignore_index=True)

# Optional save of combined downstream data
spheroid_size_df.to_csv('combined_spheroid_size_per_spheroid.csv', index=False)
sensor_ratio_df.to_csv('combined_sensor_ratio_per_spheroid.csv', index=False)

# ---------------------------------------------------------------------
# Plot helper
# ---------------------------------------------------------------------
def plot_grouped_violins(
    df,
    value_col,
    ylabel,
    title,
    output_path,
    ylim=None,
    figsize=(10, 7),
    violin_width=0.13,
    point_size=18,
    point_alpha=0.45,
    seed=12345
):
    """
    Plot grouped violins:
    - x groups = conditions
    - 4 site-specific violins per condition
    - narrow violins
    - individual points overlaid
    - Q1, median, Q3 shown as horizontal lines
    """
    rng = np.random.default_rng(seed)

    fig, ax = plt.subplots(figsize=figsize)

    # Layout: 6 conditions, 4 sites within each condition
    centers = np.arange(len(condition_order))
    offsets = np.array([-0.24, -0.08, 0.08, 0.24])  # spacing for 4 sites per condition

    # For legend
    legend_handles = [Line2D([0], [0], color=site_colors[s], lw=2) for s in site_order]

    for cond_idx, cond in enumerate(condition_order):
        for site_idx, site in enumerate(site_order):
            xpos = centers[cond_idx] + offsets[site_idx]

            sub = df[(df['Condition'] == cond) & (df['Site'] == site)].copy()
            vals = sub[value_col].dropna().values

            if len(vals) == 0:
                continue

            color = site_colors[site]

            # Violin
            violin = ax.violinplot(
                dataset=[vals],
                positions=[xpos],
                widths=violin_width,
                showmeans=False,
                showmedians=False,
                showextrema=False
            )

            for body in violin['bodies']:
                body.set_facecolor(color)
                body.set_edgecolor(color)
                body.set_alpha(0.20)
                body.set_linewidth(1.0)

            # Jittered points
            jitter = rng.uniform(-violin_width * 0.32, violin_width * 0.32, size=len(vals))
            ax.scatter(
                np.full(len(vals), xpos) + jitter,
                vals,
                s=point_size,
                color=color,
                alpha=point_alpha,
                linewidths=0,
                zorder=3
            )

            # Quartiles + median
            q1, med, q3 = np.percentile(vals, [25, 50, 75])

            # Q1/Q3 thinner
            ax.hlines(q1, xpos - violin_width * 0.34, xpos + violin_width * 0.34,
                      color=color, linewidth=1.2, zorder=4)
            ax.hlines(q3, xpos - violin_width * 0.34, xpos + violin_width * 0.34,
                      color=color, linewidth=1.2, zorder=4)

            # Median thicker
            ax.hlines(med, xpos - violin_width * 0.42, xpos + violin_width * 0.42,
                      color=color, linewidth=2.6, zorder=5)

    ax.set_xticks(centers)
    ax.set_xticklabels([wrap_label(c) for c in condition_order], fontsize=14)
    ax.tick_params(axis='y', labelsize=14)
    ax.set_ylabel(ylabel, fontsize=14)
    ax.set_title(title, fontsize=15, pad=14)

    if ylim is not None:
        ax.set_ylim(*ylim)

    ax.legend(
        legend_handles,
        site_order,
        title='Sites',
        title_fontsize=14,
        fontsize=13,
        loc='upper right',
        frameon=False
    )

    ax.set_xlim(-0.5, len(condition_order) - 0.5)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.show()

# ---------------------------------------------------------------------
# Make matched pair of plots
# ---------------------------------------------------------------------
plot_grouped_violins(
    df=spheroid_size_df,
    value_col='value',
    ylabel='Per-spheroid size (object count)',
    title='Per-Spheroid Size Across Conditions and Sites\nViolin = per-spheroid distribution, lines = median and IQR',
    output_path='cross_site_spheroid_size_violin.png',
    ylim=None,  # set manually if you want, e.g. (0, 120)
    figsize=(10, 7),
    violin_width=0.13,
    point_size=18,
    point_alpha=0.45,
    seed=12345
)

plot_grouped_violins(
    df=sensor_ratio_df,
    value_col='value',
    ylabel='Per-spheroid median cyt/nuc ratio',
    title='Per-Spheroid cyt_nuc_ratio_sensor Across Conditions and Sites\nViolin = per-spheroid distribution, lines = median and IQR',
    output_path='cross_site_sensor_ratio_violin.png',
    ylim=(0.3, 0.6),  # matches your earlier biosensor plot
    figsize=(10, 7),
    violin_width=0.13,
    point_size=18,
    point_alpha=0.45,
    seed=12345
)

print("Saved: Fig5b.png")
print("Saved: Fig5a.png")
print("Saved: combined_spheroid_size_per_spheroid.csv")
print("Saved: combined_sensor_ratio_per_spheroid.csv")