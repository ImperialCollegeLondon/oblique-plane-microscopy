@echo off
REM Run bead BDV conversion and Fiji registration (Windows)
SET CONFIG=%~1
IF "%CONFIG%"=="" SET CONFIG=deskewing_pipeline\configs\example_raw.yaml
python deskewing_pipeline\scripts\register_beads_pipeline.py --config "%CONFIG%"
echo Registration complete. Bead BDV XML should match registration.registered_bead_xml_path in config.
