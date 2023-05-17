powershell.exe -ExecutionPolicy Bypass -File ".\record-nfc.ps1" -AudioInputName "Mic in at rear panel (Pink) (Realtek(R) Audio)" -OutputDirectory "Q:\birdrecordings\NFC-recordings" -SunsetOffset .5 -SunriseOffset -1.5
@rem when not DST
@REM powershell.exe -ExecutionPolicy Bypass -File ".\record-nfc.ps1" -AudioInputName "Line In (Realtek(R) Audio)" -OutputDirectory "Q:\birdrecordings\NFC-recordings" -SunsetOffset 1.5 -SunriseOffset -0.5
