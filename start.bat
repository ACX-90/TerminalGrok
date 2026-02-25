@echo off
setlocal EnableDelayedExpansion
cd %~dp0

:: general workspace path, you can change it to any path you want
set "workspace=E:\_Workspace\Trok"

:: create workspace
if not exist %workspace% (
    mkdir %workspace%
)

:: enter OpenRouter API key for Grok
if not exist %workspace%\tokens\grok.token (
    set /p token=Copy your openrouter API KEY, press enter when done $ 
    if not exist %workspace%\tokens (
        mkdir %workspace%\tokens
    )
    echo !token! > %workspace%\tokens\grok.token
)

:: enter Telegram API key for bot service
if not exist %workspace%\tokens\agent00.token (
    set /p token=Copy your Telegram API KEY, press enter when done $ 
    if not exist %workspace%\tokens (
        mkdir %workspace%\tokens
    )
    echo !token! > %workspace%\tokens\agent00.token
)

:: copy files to workspace
if not %cd% equ %workspace% (
    xcopy "%~dp0\config\" "%workspace%\config\" /q /y
    xcopy "%~dp0\src\" "%workspace%\src\" /q /y
    xcopy "%~dp0\src\tools\" "%workspace%\src\tools\" /q /y
    xcopy "%~dp0\src\ai\" "%workspace%\src\ai\" /q /y
    xcopy "%~dp0\*.bat" "%workspace%\" /q /y
)

:: setup python virtual environment and dependencies
if not exist %workspace%\venv (
    py -m venv %workspace%\venv
    %workspace%\venv\Scripts\pip install openai
    %workspace%\venv\Scripts\pip install xai_sdk
    %workspace%\venv\Scripts\pip install httpx[socks]
    %workspace%\venv\Scripts\pip install python-telegram-bot
    %workspace%\venv\Scripts\pip install python-telegram-bot[job-queue]
)

:: modify grok.bat to workspace path and copy to Python directory
:: enable to call grok anywhere in terminal
set "target=%~dp0\env\grok.bat"
powershell -Command "(Get-Content '%target%') -replace '^set \"workspace=.*\"$', 'set \"workspace=%workspace%\"' | Set-Content '%target%'"
xcopy "%target%" "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312" /q /y

:: start a grok instance
echo Start Grok
cd %workspace%
:RESTART
%workspace%\venv\Scripts\python %workspace%\src\main.py
echo Restart Grok
goto :RESTART
