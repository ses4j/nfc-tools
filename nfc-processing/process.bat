@setlocal

set SOURCE_WAV=%1
rem set PROCESSED_WAV="%~dp0%~nx1"
set PROCESSED_WAV="%~dp1%~n1-soxxed%~x1"
set OUTPUT_DIR="%~dp1%~n1-soxxed_clips"

REM for oldbird mic
if not exist %PROCESSED_WAV% "c:\Program Files (x86)\sox-14-4-2\sox" %SOURCE_WAV% %PROCESSED_WAV% vol 2 channels 1
REM for my mike
REM if not exist %PROCESSED_WAV% "c:\Program Files (x86)\sox-14-4-2\sox" %SOURCE_WAV% %PROCESSED_WAV% sinc 1500 vol 32 channels 1
"c:\Program Files (x86)\sox-14-4-2\sox" --info %SOURCE_WAV%
"c:\Program Files (x86)\sox-14-4-2\sox" --info %PROCESSED_WAV%
py -m birdvoxdetect -t 40 -c -d 2 -v %PROCESSED_WAV%
explorer %OUTPUT_DIR%
rundll32.exe cmdext.dll,MessageBeepStub
rundll32.exe cmdext.dll,MessageBeepStub
rundll32.exe cmdext.dll,MessageBeepStub
rundll32.exe cmdext.dll,MessageBeepStub
rundll32.exe cmdext.dll,MessageBeepStub
rundll32.exe cmdext.dll,MessageBeepStub
