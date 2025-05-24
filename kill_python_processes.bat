@echo off
echo Looking for Python processes to terminate...
tasklist /fi "imagename eq python.exe" /fo table

echo.
set /p confirm=Are you sure you want to kill all Python processes? (Y/N): 
if /i "%confirm%" neq "Y" goto :end

echo.
echo Terminating all Python processes...
taskkill /f /im python.exe

echo.
echo Looking for Python w/ Modules (pythonw.exe)...
tasklist /fi "imagename eq pythonw.exe" /fo table

echo.
set /p confirm=Kill pythonw.exe processes too? (Y/N): 
if /i "%confirm%" neq "Y" goto :end

echo.
echo Terminating all pythonw.exe processes...
taskkill /f /im pythonw.exe

:end
echo.
echo Done. Press any key to exit.
pause > nul 