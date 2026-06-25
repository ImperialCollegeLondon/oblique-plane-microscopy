@echo off
REM Create representative summaries for raw and fused outputs (Windows)
SET RAW=%~1
SET FUSED=%~2
IF "%RAW%"=="" SET RAW=path\to\sample\processed
IF "%FUSED%"=="" SET FUSED=path\to\fused\processed
python deskewing_pipeline\src\summary_raw.py "%RAW%" --output summary_raw
python deskewing_pipeline\src\summary_fused.py "%FUSED%" --output summary_fused
echo Summaries created: summary_raw\ and summary_fused\
