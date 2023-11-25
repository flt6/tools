@echo off
:: Check if the script is run as administrator
NET SESSION >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrator permissions...
    goto runAsAdmin
) else (
    goto main
)

:runAsAdmin
:: Request administrator permissions
powershell Start-Process "%0" -Verb RunAs
exit /B

:main
:: Get user input for WifiMaxPeers value
set /p WifiMaxPeersInput="Enter WifiMaxPeers value (decimal): "

:: Validate if the input is a number
set "WifiMaxPeers=%WifiMaxPeersInput%" 2>nul
if not defined WifiMaxPeers (
    echo Invalid input. Please enter a valid decimal number.
    pause
    exit /B
)

:: Set the registry value
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\icssvc\Settings" /v WifiMaxPeers /t REG_DWORD /d %WifiMaxPeers% /f

echo WifiMaxPeers registry value set to %WifiMaxPeers%.

echo Restarting icssvc service.

net stop icssvc
net start icssvc

echo Succeed.
pause
