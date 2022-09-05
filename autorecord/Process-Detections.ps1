function Process-Detections {
    Param(
    # Specifies a path to one or more locations.
    [Parameter(Mandatory=$true,Position=0,ValueFromPipeline=$true,ValueFromPipelineByPropertyName=$true,HelpMessage="Path to NFC.")][Alias("PSPath")][ValidateNotNullOrEmpty()][string]$NFCPath,
    [Int32]$WarnAmount = 1000
        )
        
    If(-not (Test-Path -Path $NFCPath)) {   # If $NFCPath is not a valid path
        Write-Host -ForegroundColor Red "'$NFCPath' Does not exist. Exiting..."
        Exit
        }

    # Get a list of valid NFC*.wav files in the specified subdirectory
    $NFCRegex = "^NFC \d{4}-\d\d-\d\d \d{4}_\d\d_\d\d_\d\d-\d\d_\d\d_\w{4}\.wav$" # Matches typical file pattern:  "NFC YYYY-MM-DD HHMM_HH_MM_SS-MS_%%_SPEC.wav"
    $NFCFiles = Get-ChildItem -Path $NFCPath | Where-Object -FilterScript {$_.Name -match $NFCRegex} | Select-Object -Property "Name"

    Write-Host "Found $($NFCFiles.Length) Files to process..."
        

    ForEach($NFCFile in $NFCFiles) {
      $NFCStartTime = Get-Date -Year ([convert]::ToInt32($NFCFile.name.Substring(4,4), 10)) -Month ([convert]::ToInt32($NFCFile.Name.Substring(9,2), 10)) -Day ([convert]::ToInt32($NFCFile.Name.Substring(12,2), 10)) -Hour ([convert]::ToInt32($NFCFile.Name.Substring(15,2), 10)) -Minute ([convert]::ToInt32($NFCFile.Name.Substring(17,2), 10)) -Second 0
      $NFCFileTime = $NFCStartTime.AddHours([convert]::ToInt32($NFCFile.Name.Substring(20,2), 10)).AddMinutes([convert]::ToInt32($NFCFile.Name.Substring(23,2), 10)).AddSeconds([convert]::ToInt32($NFCFile.Name.Substring(26,2), 10))
      
      # String of the banding code guessed by BirdVoxDetect: $NFCFile.Name.Substring(35,4)

      $NewFilename = "NFC " + $NFCFileTime.ToString("yyyy-MM-dd HH-mm-ss") + " - " + "PASS" + $NFCFile.Name.Substring(39,4)

      If(Test-Path -Path ($NFCPath + "\" + $NewFilename)) {   # If a file created on the same second as this already exists and would overlap, delete that file.
        Remove-Item -Path ($NFCPath + "\" + $NFCFile.Name)
      }
      Else {
        Rename-Item -Path ($NFCPath + "\" + $NFCFile.Name) -NewName $NewFilename
      }


      $AfterFiles = Get-ChildItem -Path $NFCPath -Filter *.wav

      If($AfterFiles.Length -ge $WarnAmount) {
        Write-Warning "Found more than $WarnAmount detection files. There may be an issue with the recording (rain, too much recording time, etc.)."
      }

      Write-Host "Removed $($NFCFiles.Length - $AfterFiles.Length) duplicate files during processing. Final detection count is $($AfterFiles.Length)"



      # Write-Host $NewFilename
        
    }
}


function Process-allNFCs {
  $Detections = Get-ChildItem -Filter NFC*.wav -Recurse -Depth 1
  $Directories = $Detections.DirectoryName | Select-Object -Unique
  Foreach($Directory in $Directories) {
    Write-Host $Directory
    Process-Detections -NFCPath $Directory
  }
}