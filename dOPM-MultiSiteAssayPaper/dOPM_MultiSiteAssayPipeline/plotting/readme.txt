
## README – master_cross_partner.csv

This file contains all measurements from the Cross-Partner assay combined into one table. Each row is one segmented cell (or object) from a spheroid. The table also includes information about where the spheroid came from (which site, which well, which tile) and the treatment condition for that well.

---

## How to read the key columns

Site
The partner lab that produced the data (IRB, IGC, Crick, ICR).

Condition
The treatment applied in that well. This is the main field to use for biological comparisons.

filename
The original image name from which the cell was segmented.

well
The plate well the spheroid was taken from (e.g. B5). This is plate layout information, not a cell property.

Row_Letter and column
Plate row and plate column. These come from the well name and describe the plate position only.

tile
The tile inside the well. Each tile generally corresponds to one spheroid.

Spheroid
A simple combined label (well + tile) identifying each spheroid. All rows with the same Spheroid value belong to the same spheroid.

index
The object index inside the segmented image. This is per cell.

---

## Shape and position measurements (per cell)

Columns such as N_voxels, Area, Volume, shape_factor, Xc/Yc/Zc, Rg, Solidity, Ellipticity, and the principal-axis ratios describe the 3D size and shape of each segmented cell.

---

## Neighbourhood features (per cell)

Fields like number_of_neighbours, average_distance_to_neighbour, minimal_distance_to_neighbour, and is_internal describe how the cell sits relative to nearby cells.

---

## Intensity statistics (per cell)

For each cell, the table includes mean, standard deviation, skewness, kurtosis, and quartiles of intensity for different masks (nucleus, collar/cytoplasm, membrane, sensor). These are taken directly from voxel values inside those regions.

---

## Cytoplasm-to-nucleus ratios

cyt_nuc_ratio_sensor, cyt_nuc_ratio_membrane, cyt_nuc_ratio_nucleus
These provide simple per-cell ratios comparing cytoplasmic and nuclear signal levels.

---

## Summary

Use Condition for treatment comparisons.
Use Spheroid to group cells from the same spheroid.
well, Row_Letter, and column describe plate layout rather than biological differences.


