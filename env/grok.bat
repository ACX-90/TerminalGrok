@echo off
setlocal EnableDelayedExpansion

set "workspace=E:\_Workspace\GitHub\TerminalGrok"
set "reply=%workspace%\fcomm\reply.grok"
set "msg=%workspace%\fcomm\msg.grok"
set "endkey=<GROK status=END></GROK>"
set "rxkey=<GROK status=DONE></GROK>"
set "txkey=^<GROK status=start^>^</GROK^>"

:: poll
if "%~1" equ "" (
	if exist %reply% (
		echo Grok has message
		powershell -NoProfile -Command "Get-Content -LiteralPath '%reply%' | Where-Object { $_.Trim() -notmatch '^(<GROK status=DONE></GROK>|<GROK status=END></GROK>)$' }"
		del %reply%
	) else (
		echo Grok is not ready
	)
	exit /b 0
)

:: delete previous grok output
if exist %reply% del "%reply%"

:: send message to grok
echo %* > %msg%
echo %txkey% >> %msg%

:WAIT
if not exist %reply% goto :WAIT
findstr /C:"%endkey%" %reply% >nul && goto :QUIT
findstr /C:"%rxkey%" %reply% >nul || goto :WAIT
powershell -NoProfile -Command "Get-Content -LiteralPath '%reply%' | Where-Object { $_.Trim() -notmatch '^(<GROK status=DONE></GROK>|<GROK status=END></GROK>)$' }"
del %reply%
goto :WAIT

:QUIT
powershell -NoProfile -Command "Get-Content -LiteralPath '%reply%' | Where-Object { $_.Trim() -notmatch '^(<GROK status=DONE></GROK>|<GROK status=END></GROK>)$' }"
del %reply%
exit /b 0
