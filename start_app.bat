@echo off
title FITGIRL Games Downloader
echo Starting FITGIRL Games Downloader...
python main.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo Application exited with an error.
    pause
)
