@echo off
title Digital Sentinel
color 0A

echo.
echo  ==========================================
echo   DIGITAL SENTINEL
echo   Personal Security ^& Career Orchestrator
echo  ==========================================
echo.
echo  Starting server...
echo  Browser will open automatically in 3 seconds.
echo.
echo  To stop: close this window or press Ctrl+C
echo.

cd /d "C:\Users\Edwin Olaez\digital-sentinel"
call .sentinel_env\Scripts\activate

python app.py
