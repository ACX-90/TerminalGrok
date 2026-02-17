@echo off
setlocal EnableDelayedExpansion

set "workspace=E:\_Workspace\TerminalGrok"
set "reply=%workspace%\reply.grok"
set "msg=%workspace%\msg.grok"
set "end=%workspace%\end.grok"
set "rxkey=<GROK status=DONE></GROK>"
set "txkey=^<GROK status=start^>^</GROK^>"

:: poll
if "%~1" equ "" (
	echo Poll status
	if exist %reply% (
		echo Grok has message
		powershell -Command "Get-Content '%reply%' | Where-Object { $_ -ne '<GROK status=DONE></GROK>' }"
		del %reply%
	) else (
		echo Grok is not ready
	)
	exit /b 0
)

:: delete previous grok output
if exist %reply% del "%reply%"
if exist %end% del "%end%"

:: send message to grok
echo %* > %msg%
echo %txkey% >> %msg%

:WAIT
ping 127.0.0.1 -n 1 >nul
if exist %end% goto :QUIT2
if not exist %reply% goto :WAIT
findstr /C:"%rxkey%" %reply% >nul || goto :WAIT
powershell -Command "Get-Content '%reply%' | Where-Object { $_ -ne '<GROK status=DONE></GROK>' }"
del %reply%

if not exist %end% goto :WAIT
:QUIT
del %end%
exit /b 0

:QUIT2
del %end%
if exist %reply% (
	powershell -Command "Get-Content '%reply%' | Where-Object { $_ -ne '<GROK status=DONE></GROK>' }"
	del %reply%
)
exit /b 0
