# Get Parameters
Param(
  [Parameter(ValueFromPipeline = $true)][String]$Gain = 10, #Currently Not In Use
  [Parameter(ValueFromPipeline = $true)][String]$AudioInputName = "-d", # -d is default device.  Can list available inputs via `ffmpeg -list_devices true -f dshow -i dummy`
  [Parameter(ValueFromPipeline = $true)][String]$Filetype = "wav",
  [Parameter(ValueFromPipeline = $true)][String]$BirdVoxThreshold = 10,
  [Parameter(ValueFromPipeline = $true)][String]$BirdVoxDuration = 3,
  [Parameter(ValueFromPipeline = $true)][String]$SunriseSunsetFilename = '.\SunriseSunset.csv',
  [Parameter(ValueFromPipeline = $true)][Single]$SunsetOffset = 1.5, # How many hours after sunset do you want recording to start?
  [Parameter(ValueFromPipeline = $true)][Single]$SunriseOffset = -0.5, # How many hours before Sunrise do you want recording to stop?
  [Parameter(ValueFromPipeline = $true)][switch]$Test = $false,
  [Parameter(ValueFromPipeline = $true)][switch]$PauseForInput = $false,
  [Parameter(ValueFromPipeline = $true)][String]$OutputDirectory = '.'
)

. ".\Process-Detections.ps1"

########################################### Auto Start/stop ###########################################

If (Test-Path $SunriseSunsetFilename) {
  # Check for .csv file
  $SunriseSunset = Import-Csv $SunriseSunsetFilename
  $Today = $SunriseSunset | Where-Object -Property "Date" -match (Get-Date -Format "^?M/?d/") | Select-Object -First 1 #Get the line from the csv that matches today's Month/Day. Year does not need to match. There will be minor accuracy errors for year not matching, but not enough to matter for our purposes.
  $Sunset = [datetime]::Parse($Today.Sunset)
  $Sunrise = [datetime]::Parse($Today.Sunrise).AddDays(1)
  $StartRecord = $Sunset.AddHours($SunsetOffset)
  $StopRecord = $Sunrise.AddHours($SunriseOffset)
}
Else {
  #If no CSV File detected, set to default start/end recording times.
  Write-Host -ForegroundColor Yellow "No SunriseSunset.csv file detected, reverting to default times:"
  $StartRecord = Get-Date -Hour 21 -Minute 00 -Second 00
  $StopRecord = (Get-Date -Hour 5 -Minute 00 -Second 00).AddDays(1)
}

Write-Host -ForegroundColor Yellow "Start Time:" $StartRecord.ToString("HH:mm:ss")
Write-Host -ForegroundColor Yellow "End Time:" $StopRecord.ToString("HH:mm:ss")

if ($test) {
  Write-Host -ForegroundColor Yellow "Running Test Recordings."
}
elseif ((New-TimeSpan -end $StartRecord) -ge 0) {
  # If The StartRecord time has not already passed
  Write-Host -ForegroundColor Blue "Will start recording at" $StartRecord.ToString("HH:mm:ss")
  While ((New-TimeSpan -End $StartRecord).TotalSeconds -ge 0) {
    Write-Host -NoNewline "`r$((New-TimeSpan -end $StartRecord).ToString('hh\:mm\:ss')) "
    Start-Sleep -Seconds 1
  }
  Write-Host -ForegroundColor Green "Starting recording."
}
else {
  Write-Host -ForegroundColor Yellow "This script started after the recommended start time. Starting recording immediately."
}


########################################### PM Recording ###########################################
# Establish current date and time and create a filename based on those variables for the PM recording.

$StartPMAt = Get-Date
$StartAMAt = $StartPMAt.AddDays(1).Date

$FullOutputDirectory = $OutputDirectory + "\" + $StartPMAt.ToString("yyyy") + "\" + $StartPMAt.ToString("yyyy-MM-dd")
New-item $FullOutputDirectory -ItemType Directory -force
Write-Host -ForegroundColor Green "Outputting to" $FullOutputDirectory

$PMFilename = $FullOutputDirectory + "\NFC-" + $StartPMAt.ToString("yyyy-MM-dd-HHmm")
if ($Test) { $PMRecordTime = "00:00:02" }
else {
  $PMRecordTime = ($StartAMAt - (Get-Date)).ToString("hh\:mm\:ss") # Establish the amount of time until midnight so your PM recording will stop then and your AM recording can begin at midnight.
}

Write-Host -ForegroundColor Green "Starting PM Recording:" (Get-Date -Format "yyyy-MM-dd HH:mm:ss") " - Record Time:" $PMRecordTime $AMFilename " - Filename:" $PMFilename "." "$Filetype"

# & ".\soxrecord.bat" ($PMFilename + "." + "$Filetype") $PMRecordTime # Deprecated batch file method.
Write-Host -ForegroundColor Green 'C:\Program Files (x86)\sox-14-4-2\sox.exe' '-t' 'waveaudio' '-c 1' '-r 22050' $AudioInputName ($PMFilename + "." + "$Filetype") 'trim' "0" "$PMRecordTime"
& 'C:\Program Files (x86)\sox-14-4-2\sox.exe' '-t' 'waveaudio' '-c 1' '-r 22050' $AudioInputName ($PMFilename + "." + "$Filetype") 'trim' "0" "$PMRecordTime"

########################################### AM Recording ###########################################
# Establish current date and time and create a filename based on those variables for the AM recording.

if ($Test) { $AMRecordTime = "00:00:02" }
else {
  $AMRecordTime = ($StopRecord - (Get-Date)).ToString("hh\:mm\:ss") # Establish the amount of time to record until the the offset before sunrise.
}

$AMFilename = $FullOutputDirectory + "\NFC-" + $StartAMAt.ToString("yyyy-MM-dd HHmm")

Write-Host -ForegroundColor Green "Starting AM Recording:" (Get-Date -Format "yyyy-MM-dd HH:mm:ss") "Record Time:" $AMRecordTime $AMFilename

& 'C:\Program Files (x86)\sox-14-4-2\sox.exe' '-t' 'waveaudio' '-c 1' '-r 22050' $AudioInputName ($AMFilename + "." + "$Filetype") 'trim' "0" "$AMRecordTime"

Write-Host -ForegroundColor Green "Recording Complete:" (Get-Date -Format "yyyy-MM-dd HH:mm:ss")

$RunBirdVoxDetect = false
if ($RunBirdVoxDetect) {
  ########################################### BirdVoxDetect ###########################################
  $birdvoxParam = @('-m',
    'birdvoxdetect',
    ('-t ' + $BirdVoxThreshold),
    '-c',
    ('-d ' + $BirdVoxDuration),
    '-v',
    ($PMFilename + "." + "$Filetype"),
    ($AMFilename + "." + "$Filetype")
  )

  & C:\Windows\py.exe $birdvoxParam #Run BirdVoxDetect with above parameters.

  #################################### Process Output of BirdvoxDetect ##################################

  Process-Detections -NFCPath (".\" + $PMFilename + "_clips")
  Process-Detections -NFCPath (".\" + $AMFilename + "_clips")
}


########################################### Convert to FLAC ###########################################

If ($FIletype -eq "WAV") {
  #Convert WAVs to FLAC for reduced storage.
  $OkToDeleteWavs = True
  & "C:\Program Files (x86)\sox-14-4-2\sox.exe" ($PMFilename + "." + $Filetype) ($PMFilename + "." + "flac")
  if ($LastExitCode -ne 0) {
    $OkToDeleteWavs = False
  }
  & "C:\Program Files (x86)\sox-14-4-2\sox.exe" ($AMFilename + "." + $Filetype) ($AMFilename + "." + "flac")
  if ($LastExitCode -ne 0) {
    $OkToDeleteWavs = False
  }

  if ($OkToDeleteWavs) {
    If ((Test-Path ($PMFilename + "." + "flac")) -and (Test-Path ($PMFilename + "." + "flac"))) {
      Remove-Item ($PMFilename + "." + $Filetype)
      Remove-Item ($AMFilename + "." + $Filetype)
    }
    else {
      Write-Warning "Did not find converted flac files... Leaving original recordings."
    }
  }
}


If ($PauseForInput) {
  #Use if you are running from Task Scheduler and want the window to remain open after completion.
  Write-Host 'Press any key to continue...'
  $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
}



