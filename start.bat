@echo off
setlocal EnableDelayedExpansion
cd %~dp0

set "workspace=E:\_Workspace\GitHub\TerminalGrok"
::set "workspace=E:\_Workspace\TerminalGrok"

if not exist %workspace% (
    mkdir %workspace%
)

if not exist %workspace%\token\grok.token (
    set /p token=Copy your openrouter API KEY, press enter when done $ 
    if not exist %workspace%\token (
        mkdir %workspace%\token
    )
    echo !token! > %workspace%\token\grok.token
)

if not exist %workspace%\venv (
    py -m venv %workspace%\venv
    %workspace%\venv\Scripts\pip install openai
    %workspace%\venv\Scripts\pip install httpx[socks]
)

if not %cd% equ %workspace% (
    xcopy "%~dp0\src\" "%workspace%\src\" /q /y
    xcopy "%~dp0\*.bat" "%workspace%\" /q /y
)

set "target=%~dp0\env\grok.bat"
powershell -Command "(Get-Content '%target%') -replace '^set \"workspace=.*\"$', 'set \"workspace=%workspace%\"' | Set-Content '%target%'"
xcopy "%target%" "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312" /q /y

echo Start Grok
cd %workspace%
:RESTART
%workspace%\venv\Scripts\python %workspace%\src\main.py
echo Restart Grok
goto :RESTART
