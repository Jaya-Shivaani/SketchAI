@echo off
setlocal enabledelayedexpansion
title SketchAI Collaborative Drawing Game Server
cd /d "%~dp0"

echo ================================================================
echo   Starting SketchAI Collaborative Drawing Game Platform
echo ================================================================
echo.

:: 1. Check if virtualenv exists in D:\env or project venv
if exist "D:\env\Scripts\python.exe" (
    echo [OK] Found Virtualenv at D:\env\Scripts\python.exe
    "D:\env\Scripts\python.exe" Backend\main.py
    goto end
)

if exist "%~dp0venv\Scripts\python.exe" (
    echo [OK] Found project venv at %~dp0venv\Scripts\python.exe
    "%~dp0venv\Scripts\python.exe" Backend\main.py
    goto end
)

if exist "%~dp0env\Scripts\python.exe" (
    echo [OK] Found project env at %~dp0env\Scripts\python.exe
    "%~dp0env\Scripts\python.exe" Backend\main.py
    goto end
)

:: 2. Check if python is in PATH
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Using system python from PATH...
    python Backend\main.py
    goto end
)

:: 3. Check if Python Launcher (py) is available
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Using Python Launcher (py)...
    py Backend\main.py
    goto end
)

:: 4. Fallback: check typical Windows install locations
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    echo [OK] Found Python 3.13 in LocalAppData...
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" Backend\main.py
    goto end
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    echo [OK] Found Python 3.12 in LocalAppData...
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" Backend\main.py
    goto end
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    echo [OK] Found Python 3.11 in LocalAppData...
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" Backend\main.py
    goto end
)

if exist "C:\Python313\python.exe" (
    echo [OK] Found C:\Python313\python.exe...
    "C:\Python313\python.exe" Backend\main.py
    goto end
)

echo.
echo [ERROR] Python was not found on your system PATH or default directories.
echo Please install Python 3.10+ from https://www.python.org/ and check "Add Python to PATH".
echo.

:end
pause
