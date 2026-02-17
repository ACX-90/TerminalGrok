@echo off
set "workspace=E:\_Workspace\TerminalGrok"
set "reply=%workspace%\reply.grok"
set "msg=%workspace%\msg.grok"

:: poll
if "%~1" equ "" (
	echo Poll status
	if exist %reply% (
		for /f %%i in (%reply%) do echo %%i
		exit /b 0
	) else (
		echo Grok is not ready
	)
)

:: delete previous grok output
if exist %reply% (
	echo Delete prev file
	del "%reply%"
)

echo "%*" > %msg%

:WAIT

if not exist %reply% (
	TIMEOUT /t 7
	echo Waiting
	::goto WAIT
)



