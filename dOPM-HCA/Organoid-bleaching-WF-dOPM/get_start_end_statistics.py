import os
import pandas as pd
import numpy as np

# Path to folder containing CSVs for each tile
total_signals_directory = r"D:\data\final_temp_240326_live_Emerald_photobleaching_plate\analysis_v2\Total_Signals_faster_no_labels"

# Tile indices for each modality
WF_tiles = [2, 5, 8, 11, 14, 17, 20, 23]
dOPM_tiles = [0, 1, 2, 3, 4, 5, 6, 7]

# Helper to load and normalize signal
def load_normalized_signal(file_path):
    df = pd.read_csv(file_path)
    df = df.sort_values(by='Timepoint').reset_index(drop=True)
    return df['Total Signal'] / df['Total Signal'].iloc[0]

# Lists to collect per-tile final signal drops
wf_drops = []
dopm_drops = []

# Process WF tiles
for tile in WF_tiles:
    path = os.path.join(total_signals_directory, f'Total_Signal_WF_Tile{tile}.csv')
    if os.path.exists(path):
        norm_signal = load_normalized_signal(path)
        signal_drop = 1.0 - norm_signal.iloc[-1]
        wf_drops.append(signal_drop)

# Process dOPM tiles
for tile in dOPM_tiles:
    path = os.path.join(total_signals_directory, f'Total_Signal_dOPM_Tile{tile}.csv')
    if os.path.exists(path):
        norm_signal = load_normalized_signal(path)
        signal_drop = 1.0 - norm_signal.iloc[-1]
        dopm_drops.append(signal_drop)

# Convert to NumPy arrays
wf_drops = np.array(wf_drops)
dopm_drops = np.array(dopm_drops)

# Compute median ± IQR
wf_median = np.median(wf_drops)
wf_iqr = np.percentile(wf_drops, 75) - np.percentile(wf_drops, 25)

dopm_median = np.median(dopm_drops)
dopm_iqr = np.percentile(dopm_drops, 75) - np.percentile(dopm_drops, 25)

# Print results
print(f"WF drop: {wf_median:.3f} ± {wf_iqr:.3f}")
print(f"dOPM drop: {dopm_median:.3f} ± {dopm_iqr:.3f}")
