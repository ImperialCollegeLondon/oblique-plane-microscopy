import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
from matplotlib.lines import Line2D

# --- File paths and condition mappings ---
files_with_mappings = [
    {
        "file_path": '.data/IRB/main_quantification.csv',
        "row_to_condition_mapping": {
            'B': 'DMSO', 'C': '100 nM TPA', 'D': '20 nM Binimetinib',
            'E': '60 nM Binimetinib', 'F': '200 nM Binimetinib', 'G': '3.5 µM Binimetinib'
        },
        "label_anon": "1"
    },
    {
        "file_path": '.data/IGC/main_quantification.csv',
        "row_to_condition_mapping": {
            'B': 'DMSO', 'G': '100 nM TPA', 'F': '20 nM Binimetinib',
            'E': '60 nM Binimetinib', 'D': '200 nM Binimetinib', 'C': '3.5 µM Binimetinib'
        },
        "label_anon": "2"
    },
    {
        "file_path": '.data/Crick/main_quantification.csv',
        "row_to_condition_mapping": {
            'B': 'DMSO', 'C': '100 nM TPA', 'D': '20 nM Binimetinib',
            'E': '60 nM Binimetinib', 'F': '200 nM Binimetinib', 'G': '3.5 µM Binimetinib'
        },
        "label_anon": "3"
    },
    {
        "file_path": '.data/ICR/main_quantification.csv',
        "row_to_condition_mapping": {
            'B': 'DMSO', 'C': '100 nM TPA', 'D': '20 nM Binimetinib',
            'E': '60 nM Binimetinib', 'F': '200 nM Binimetinib', 'G': '3.5 µM Binimetinib'
        },
        "label_anon": "4"
    }
]

condition_order = [
    '100 nM TPA', 'DMSO', '20 nM Binimetinib',
    '60 nM Binimetinib', '200 nM Binimetinib', '3.5 µM Binimetinib'
]

# --- Utilities ---
def extract_row(well_val):
    """Extract row letter from 'B5', 'C10', etc."""
    if pd.isna(well_val):
        return None
    match = re.match(r'^([A-Z])', str(well_val))
    return match.group(1) if match else None

def wrap_label(label):
    return label.replace(' Binimetinib', '\nBinimetinib')

def bootstrap_ci(data, n_boot=1000, ci=95):
    data = np.array(data[~np.isnan(data)])
    if len(data) < 3:
        return np.nan, np.nan
    medians = [np.median(np.random.choice(data, size=len(data), replace=True)) for _ in range(n_boot)]
    return (
        np.percentile(medians, (100 - ci) / 2),
        np.percentile(medians, 100 - (100 - ci) / 2)
    )

# --- Plot Setup ---
metrics = ['q_50_nuc_nucleus', 'q_50_nuc_sensor', 'q_50_collar_sensor']
titles = [
    'A. Nuclear Intensity (Nucleus Channel)',
    'B. Nuclear Intensity (Sensor Channel)',
    'C. Collar Intensity (Sensor Channel)'
]

fig, axes = plt.subplots(3, 1, figsize=(12, 16), sharex=True)
colors = ['blue', 'magenta', 'green', 'red']
combined_data = []

# --- Main Loop ---
for i, file_info in enumerate(files_with_mappings):
    print(f"Processing Site {file_info['label_anon']}...")
    df = pd.read_csv(file_info["file_path"])

    # Mapping
    df['Row_Letter'] = df['well'].apply(extract_row)
    df['Condition'] = df['Row_Letter'].map(file_info["row_to_condition_mapping"])
    df = df[df['Condition'].notna()]

    for ax_idx, metric in enumerate(metrics):
        ax = axes[ax_idx]
        summary_list = []

        for cond in condition_order:
            subset = df[df['Condition'] == cond][metric]
            if not subset.empty:
                low, high = bootstrap_ci(subset)
                summary_list.append({
                    'Condition': cond,
                    'Label': wrap_label(cond),
                    'Median': subset.median(),
                    'Lower': low,
                    'Upper': high
                })

        summary_df = pd.DataFrame(summary_list)

        # Split TPA vs dose-response
        summary_tpa = summary_df[summary_df['Condition'] == '100 nM TPA']
        summary_dose = summary_df[summary_df['Condition'].isin(condition_order[1:])]

        # Plot TPA as single point
        ax.errorbar(
            summary_tpa['Label'],
            summary_tpa['Median'],
            yerr=[
                summary_tpa['Median'] - summary_tpa['Lower'],
                summary_tpa['Upper'] - summary_tpa['Median']
            ],
            fmt='o',
            capsize=5,
            markersize=8,
            color=colors[i],
            alpha=0.8
        )

        # Plot connected dose-response only
        ax.errorbar(
            summary_dose['Label'],
            summary_dose['Median'],
            yerr=[
                summary_dose['Median'] - summary_dose['Lower'],
                summary_dose['Upper'] - summary_dose['Median']
            ],
            fmt='o-',
            capsize=5,
            markersize=8,
            color=colors[i],
            alpha=0.8,
            label=f"{file_info['label_anon']}" if ax_idx == 0 else None
        )

    # Save for combined export
    df['Site'] = file_info['label_anon']
    combined_data.append(df[['Site', 'Condition'] + metrics])

# --- Refine Plot ---
for idx, ax in enumerate(axes):
    ax.set_title(titles[idx], fontsize=16, fontweight='bold', loc='left')
    ax.set_ylabel('Median (q50) ± 95% CI', fontsize=13)
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    if idx == 0:
        ax.legend(title="Sites", frameon=False, fontsize=11)

plt.xticks(fontsize=12)
plt.tight_layout()
plt.savefig('SuppFig3.png', dpi=300, bbox_inches='tight')
plt.show()

# Export combined data
pd.concat(combined_data, ignore_index=True).to_csv('combined_intensity_data.csv', index=False)
print("Done! Saved 'cross_partner_intensity_3x1.png' and 'combined_intensity_data.csv'")