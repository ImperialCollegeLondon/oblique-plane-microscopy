@echo off
REM Minimal example: process raw data after bead registration (Windows)
SET CONFIG=%~1
IF "%CONFIG%"=="" SET CONFIG=deskewing_pipeline\configs\example_raw.yaml
python deskewing_pipeline\scripts\process_plate.py --config "%CONFIG%"
echo Processing complete. Check output paths defined in %CONFIG%.
