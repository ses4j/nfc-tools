@setlocal

set SOURCE_WAV=%1
set OUTPUT_FILE=%~n1-spectrogram.png
@REM "c:\Program Files (x86)\sox-14-4-2\sox" %SOURCE_WAV% -n rate 20k spectrogram -l -w Dolph -t %~n1 -s -X 300 -m -o %OUTPUT_FILE%
"c:\Program Files (x86)\sox-14-4-2\sox" %SOURCE_WAV% -n rate 20k spectrogram -l -w Dolph -t %~n1  -X 600 -m -S 1.0 -o %OUTPUT_FILE%

@REM "c:\Program Files (x86)\sox-14-4-2\sox" %OUTPUT_DIR%\%~n1-all.wav -n rate 20k spectrogram -l -w Dolph -t %~n1 -s -X 300 -m -o "%OUTPUT_DIR%\%~n1-all-spectrogram.png"
"%OUTPUT_FILE%"
