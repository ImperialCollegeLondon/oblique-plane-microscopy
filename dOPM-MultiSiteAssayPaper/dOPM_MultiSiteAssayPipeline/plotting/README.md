# Plotting

This folder contains the Python scripts and combined CSV files used to generate the paper-style plots from the processed quantification tables.

The plotting code is included as a snapshot of the analysis used for the paper, not as a general plotting package.

## Main scripts

- `combine_csvs.py`  
  Combines the site-level `main_quantification.csv` files into `master_cross_partner.csv`, adds site labels, maps plate rows to treatment conditions, and creates spheroid identifiers.

- `violin_plots.py`  
  Generates the spheroid-level violin plots used for the main readouts:
  - KTR sensor ratio per spheroid;
  - number of segmented cells per spheroid.

- `plot_nuc_and_ktr_intensity_across_sites.py`  
  Generates summary plots for nuclear and KTR intensity measurements across sites and conditions.

## Included generated outputs

This folder also contains generated CSVs and figure files, including:

- `master_cross_partner.csv`
- `combined_sensor_ratio_per_spheroid.csv`
- `combined_spheroid_size_per_spheroid.csv`
- `combined_intensity_data.csv`
- `Fig5a.png`
- `Fig5b.png`
- `SuppFig3.png`

These files are derived from the processed site-level CSVs in `../data/`.

## Site labels

The plotting scripts use anonymised site labels:

| Label | Site |
|---:|---|
| 1 | IRB |
| 2 | IGC |
| 3 | Crick |
| 4 | ICR |

Site 3 is used as the reference site in the downstream statistical analysis.

## Important notes

Some scripts contain hard-coded local paths from the original analysis environment. To rerun them, update the file paths to point to the local copies of the CSV files.

The plotting logic follows the figure logic described in the accompanying paper: per-cell measurements are aggregated to spheroid-level summaries for the main biological readouts, while raw intensity summaries are plotted separately to assess signal differences across sites.