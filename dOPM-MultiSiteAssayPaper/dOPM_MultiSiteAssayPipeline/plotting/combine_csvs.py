import pandas as pd
import re

# ---------------------------
# file list + row→condition maps
# ---------------------------

files_with_mappings = [
    {
        "file_path": '.data/IRB/main_quantification.csv',
        "row_to_condition_mapping": {
            'B': 'DMSO',
            'C': '100 nM TPA +ve control',
            'D': '20 nM Binimetinib',
            'E': '60 nM Binimetinib',
            'F': '200 nM Binimetinib',
            'G': '3.5 µM Binimetinib -ve control'
        },
        "Site": "IRB"
    },
    {
        "file_path": '.data/IGC/main_quantification.csv',
        "row_to_condition_mapping": {
            'B': 'DMSO',
            'G': '100 nM TPA +ve control',
            'F': '20 nM Binimetinib',
            'E': '60 nM Binimetinib',
            'D': '200 nM Binimetinib',
            'C': '3.5 µM Binimetinib -ve control'
        },
        "Site": "IGC"
    },
    {
        "file_path": '.data/Crick/main_quantification.csv',
        "row_to_condition_mapping": {
            'B': 'DMSO',
            'C': '100 nM TPA +ve control',
            'D': '20 nM Binimetinib',
            'E': '60 nM Binimetinib',
            'F': '200 nM Binimetinib',
            'G': '3.5 µM Binimetinib -ve control'
        },
        "Site": "Crick"
    },
    {
        "file_path": '.data/ICR/main_quantification.csv',
        "row_to_condition_mapping": {
            'B': 'DMSO',
            'C': '100 nM TPA +ve control',
            'D': '20 nM Binimetinib',
            'E': '60 nM Binimetinib',
            'F': '200 nM Binimetinib',
            'G': '3.5 µM Binimetinib -ve control'
        },
        "Site": "ICR"
    }
]


# ---------------------------
# helpers
# ---------------------------

def extract_row(fn):
    m = re.match(r'^([A-Z])\d+_tile_\d+_fused_tp_\d+', fn)
    return m.group(1) if m else None


def extract_well(fn):
    m = re.match(r'^([A-Z]\d+)_tile_\d+_fused_tp_\d+', fn)
    return m.group(1) if m else None


# ---------------------------
# combine all
# ---------------------------

all_data = []

for info in files_with_mappings:
    df = pd.read_csv(info["file_path"])

    # parse row and well from filename
    df['Row_Letter'] = df['filename'].apply(extract_row)
    df['well'] = df['filename'].apply(extract_well)

    # map row → canonical biological condition
    df['Condition'] = df['Row_Letter'].map(info["row_to_condition_mapping"])

    # add site column
    df['Site'] = info["Site"]

    # keep only valid rows
    df = df[df['Condition'].notna()]

    # numeric well column (3,4,5,6...)
    df['column'] = df['well'].str.extract(r'(\d+)').astype(int)

    # spheroid = well+tile for downstream grouping
    df['Spheroid'] = df['well'].astype(str) + '_t' + df['tile'].astype(str)

    all_data.append(df)

# merge everything
df_all = pd.concat(all_data, ignore_index=True)

# write to master CSV
df_all.to_csv("master_cross_partner.csv", index=False)

print("Wrote master_cross_partner.csv with", len(df_all), "rows.")
