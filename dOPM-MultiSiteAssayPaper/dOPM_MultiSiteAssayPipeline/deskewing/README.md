# dOPM Processing

Python tools for converting dual-view oblique plane microscopy dOPM ND2 datasets into BDV XML/HDF5 datasets, applying geometric deskew transforms, optional bead-based registration transforms, and Fiji/BigStitcher fusion.

## Repository layout

```text
src/dopm/
    Core Python package:
    - DataConverter
    - Metadata parsing
    - BDV XML/HDF5 writing/editing
    - Fiji bridge

deskewing_pipeline/
    Pipeline configs and command-line wrappers.

```

## Main workflows

### 1. Geometric deskew

Sample ND2 files are converted directly to a BDV dataset using calculated dOPM geometric affines.

```text
sample ND2 -> BDV XML/H5
```

### 2. Bead-registered deskew

Bead ND2 files are first converted into a bead BDV dataset. Fiji/BigStitcher registers this bead dataset and writes registration transforms back into the bead XML. Sample data are then converted using those bead-derived transforms.

```text
bead ND2 -> bead BDV XML/H5 -> Fiji registration
sample ND2 + registered bead XML -> registered sample BDV XML/H5
```

### 3. Fusion

Registered or geometric BDV datasets can be fused using Fiji/BigStitcher into TIFF stacks.

```text
BDV XML/H5 -> fused TIFF stacks
```

See `deskewing_pipeline/README.md` for the expected local test-data layout and configuration details.

## Notes

* Fiji/ImageJ must be available at the path specified in the YAML configs.
* Bead and sample data may use either `__WellXX` filename suffixes or well-less filenames, provided the corresponding config enables `allow_wellless_filenames: true`.

## Cluster use

The pipeline is designed so that conversion and fusion steps can be run from command-line scripts, making it suitable for execution on a workstation or an HPC cluster.

Typical cluster usage is to split work by well, tile, timepoint, or processing stage. For example:


1. Convert bead data and run bead registration once.
2. Reuse the registered bead XML for multiple sample wells.
3. Submit sample deskew jobs per well or plate region.
4. Submit Fiji/BigStitcher fusion jobs per BDV dataset or tile.

- input_path and output_path point to shared storage visible to compute nodes
- fiji_executable_path points to the cluster Fiji/ImageJ installation
- each job writes to a separate output directory
- generated bead XML files are treated as shared registration inputs for downstream sample jobs

## References

Relevant upstream tools and publications include:

- BigStitcher: https://github.com/JaneliaSciComp/BigStitcher
- npy2bdv: https://github.com/nvladimus/npy2bdv
- BigDataViewer: Pietzsch et al., “BigDataViewer: visualization and processing for large image data sets”, Nature Methods, 2015.
- BigStitcher: Hörl et al., “BigStitcher: reconstructing high-resolution image datasets of cleared and expanded samples”, Nature Methods, 2019.
- Bead-based SPIM registration: Preibisch et al., “Software for bead-based registration of selective plane illumination microscopy data”, Nature Methods, 2010.
