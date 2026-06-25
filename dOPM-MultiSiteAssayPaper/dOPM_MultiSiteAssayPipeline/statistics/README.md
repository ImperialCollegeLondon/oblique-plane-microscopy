# Statistics

This folder contains the R Markdown analysis used for the mixed-effects statistical analysis in the paper snapshot.

The statistical analysis in this folder was contributed by Kanad N. Mandke. It was contributed separately from the image-processing and plotting code. For interpretation of the model results, treatment effects and site effects, see the accompanying paper.


## Main files

- `run_lmm_knm_jan26_v2.Rmd`  
  R Markdown notebook for the reproducibility analysis.

- `3D fluorescence microscopy ... results_Jan26.html`  
  Rendered HTML output from the R Markdown analysis.

## Purpose

The statistical analysis assesses reproducibility of the 3D fluorescence microscopy assay across four sites.

In broad terms, the analysis:

1. loads the combined per-cell table;
2. aggregates measurements to the spheroid level;
3. models KTR sensor readout as a function of treatment condition and site;
4. accounts for the experimental structure of wells nested within sites;
5. performs post-hoc comparisons for treatment effects and site differences.

## Input data

The R Markdown notebook expects the combined table generated from the processed quantification data, equivalent to:

```text
../plotting/master_cross_partner.csv
```

The original notebook contains a hard-coded server path from the analysis environment. Update this path before rerunning.

## Link to paper logic

The statistical workflow follows the paper logic: per-cell measurements are first summarised at the spheroid level, then treatment and site effects are assessed using a mixed-effects model.

The paper describes the interpretation of the model, including dose-dependent treatment effects, site-specific offsets, condition-by-site interactions and the conclusion that well-level technical variance was low.

## Important notes

This folder is included to document the statistical analysis used for the paper. It is not intended as a maintained R package.

The notebook should be treated as an analysis record. If rerunning it, check package versions, input paths and factor ordering carefully.

