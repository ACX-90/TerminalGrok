@echo off
setlocal EnableDelayedExpansion

set "workspace=E:\_Workspace\TerminalGrok"

if not exist %workspace% (
    mkdir %workspace%
)

if not exist %workspace%\grok.token (
    set /p token=Place your Token in %workspace%\grok.token, press enter when done
)

if not exist %workspace%\venv (
    py -m venv %workspace%\venv
    %workspace%\venv\Scripts\pip install openai
    %workspace%\venv\Scripts\pip install httpx[socks]
)

if not %cd% equ %workspace% (
    xcopy "*.py" "%workspace%\" /q /y
    xcopy "*.bat" "%workspace%\" /q /y
)

set "target=grok.bat"
powershell -Command "(Get-Content '%target%') -replace '^set \"workspace=.*\"$', 'set \"workspace=%workspace%\"' | Set-Content '%target%'"
xcopy "%target%" "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312" /q /y

echo Start Grok
cd %workspace%
%workspace%\venv\Scripts\python %workspace%\main.py

pause
