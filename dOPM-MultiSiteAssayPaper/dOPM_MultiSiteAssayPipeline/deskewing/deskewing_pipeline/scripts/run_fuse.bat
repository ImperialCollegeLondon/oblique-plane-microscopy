@echo off
REM Minimal example: fuse/process fused stacks after registration/processing (Windows)
SET CONFIG=%~1
IF "%CONFIG%"=="" SET CONFIG=deskewing_pipeline\configs\example_fused.yaml
python deskewing_pipeline\scripts\fuse_plate.py --config "%CONFIG%"
echo Fusing complete. Check fused output paths defined in %CONFIG%.
