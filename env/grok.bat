@echo off
setlocal EnableDelayedExpansion

:: This script is used to communicate with Grok by terminal command.

:: $ grok will poll the existing messages and send to your terminal
:: $ grok "your message" will send message to grok and wait for reply,
:: then print the reply in terminal.

set "workspace=E:\_Workspace\Trok"
set "reply=%workspace%\fcomm\reply.grok"
set "msg=%workspace%\fcomm\msg.grok"
set "endkey=<GROK status=end/>"
set "rxkey=<GROK status=done/>"
set "txkey=^<GROK status=start/^>"

:: check if there is message from Grok, if so print the message and remove the file.
if exist %reply% (
	echo Grok has message.
	powershell -NoProfile -Command "Get-Content -LiteralPath '%reply%' | Where-Object { $_.Trim() -notmatch '^(<GROK status=done/>|<GROK status=end/>)$' }"
	del %reply%
) else (
	echo Grok is not ready.
)

:: only when there is message from terminal, send the message to Grok and wait for reply.
if "%~1" equ "" (
	exit /b 0
)

:: if there is message from terminal, send the message to Grok and wait for reply.
echo %* > %msg%
echo %txkey% >> %msg%

:: when done flag is received, print the message in terminal.
:WAIT
if not exist %reply% goto :WAIT
findstr /C:"%endkey%" %reply% >nul && goto :QUIT
findstr /C:"%rxkey%" %reply% >nul || goto :WAIT
powershell -NoProfile -Command "Get-Content -LiteralPath '%reply%' | Where-Object { $_.Trim() -notmatch '^(<GROK status=done/>|<GROK status=end/>)$' }"
del %reply%
goto :WAIT

:: when end flag is received, stop waiting and exit.
:QUIT
powershell -NoProfile -Command "Get-Content -LiteralPath '%reply%' | Where-Object { $_.Trim() -notmatch '^(<GROK status=done/>|<GROK status=end/>)$' }"
del %reply%
exit /b 0
