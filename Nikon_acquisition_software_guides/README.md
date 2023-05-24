# dOPM_Shared_NIS_binaries #

Use the pdfs hyperlinked below as guides while running NIS-elements and having imported the binaries.

This readme needs directions on how to organise a JOBS database. 

worth noting that this is all Nikon NIS-Elements functionality so can be looked up in NIS-Elements help documentation.

## Introduction
The screenshot below shows JOBS explorer within NIS-Elements. Familiarise youreself with this and the use of JOBS scripts by using the help documentation within NIS-Elements.

The scripts in the screenshots are some simple routines we routinely use.

A typical acquisition would consist of the following in this order:

With x4/10x/20x, long working distance, air objectives:
1 - get plate z profile: uses GetPlateZProfile.bin
2 - do prefind with brightfield wide-field imaging
3 - manually select regions of interest from prefind data

Switch to water immersion 60X objective
4 - adjust prefind position list of regions of interest so all regions are centred in xyz on microscopes frames dOPM acquisition volume space: uses PrefindPoints.bin
5 - image beads before acquisition: uses dOPM_acquisition.bin
6 - do brightfield 60x images of region of interest point list: uses Brightfield.bin
7 - do dOPM timelapse acquisition of region of interest point list: uses dOPM_acquisition.bin
8 - do brightfield 60x images of region of interest point list: uses Brightfield.bin
9 - image beads after acquisition: uses dOPM_acquisition.bin

Notes to worry about for another day:
Ideally the multiwell plate will have a well with beads in 3D
Ideally some sample will not be timelapse imaged so you can control for light-dose 


<img src="https://github.com/ImperialCollegeLondon/oblique-plane-microscopy/blob/main/Nikon_acquisition_software_guides/pictures/JOBsExplorer.PNG" width="400" height="400">


## How to import and export .bin files

### Import
Use the yellow icon with the arrow to import .bin files from this repo into NIS-Elements 

<img src="https://github.com/ImperialCollegeLondon/oblique-plane-microscopy/tree/main/Nikon_acquisition_software_guides/pictures/JOBsExplorerImportJOBDefinitions.PNG" width="400" height="100">


### Export
Right click on the JOBS scripts explorer window space to export .bin files from NIS0-Elements

<img src="https://github.com/ImperialCollegeLondon/oblique-plane-microscopy/tree/main/Nikon_acquisition_software_guides/pictures/JOBsExplorer_ExportJOBDefinitions.PNG" width="400" height="400">


## Guides to using the scripts in this repo:

* [Get Plate Z Profile](https://github.com/ImperialCollegeLondon/oblique-plane-microscopy/tree/main/Nikon_acquisition_software_guides/GetPlateZProfile.pdf)
: uses GetPlateZProfile.bin

* [Generate point list from prefind acquisition - tile scan, zstacks of wells of interest](https://github.com/ImperialCollegeLondon/oblique-plane-microscopy/tree/main/Nikon_acquisition_software_guides/Prefind_JOBS_script.pdf)
: uses PrefindPoints.bin

* [Collect brightfield images of regions of interest from point list](https://github.com/ImperialCollegeLondon/oblique-plane-microscopy/tree/main/Nikon_acquisition_software_guides/Brightfield.pdf)
: uses Brightfield.bin

* [Acquire beads for dOPM view registration - beads](https://github.com/ImperialCollegeLondon/oblique-plane-microscopy/tree/main/Nikon_acquisition_software_guides/Acquisition_beads_JOBS_script.pdf)
: uses dOPM_acquisition.bin

* [Acquire data, multipoint, dOPM, multicolor timelapse acquisition - data](https://github.com/ImperialCollegeLondon/oblique-plane-microscopy/tree/main/Nikon_acquisition_software_guides/Acquisition_JOBS_script.pdf)
: uses dOPM_acquisition.bin

* [Adjust focus on points - refine point list for dOPM](https://github.com/ImperialCollegeLondon/oblique-plane-microscopy/tree/main/Nikon_acquisition_software_guides/Adjust_focus_on_points_guide.pdf)
: uses AdjustFocusOnPoints.bin
