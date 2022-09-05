# nfc-tools

## autorecord

The `autorecord` scripts are just munged/altered from the great work at https://github.com/JoshExmoor/record-nfc.
There are various customizations, you may want to explore the original.

This script will create two WAV or FLAC files, one starting after sunset until midnight, and a second file from midnight to before sunrise.

### Getting Started

To use, you need:
- Windows/Powershell
- SOX: https://sourceforge.net/projects/sox/files/sox/14.4.2/
- SunriseSunset.csv (see https://github.com/JoshExmoor/record-nfc#creating-a-sunrisesunetcsv for details.  The included one is for Washington, DC.)

Open up the go.bat file, change the AudioInputName and OutputDirectory, to suit your needs, and try running it.

To figure out the name of the correct AudioInputName, you can try this command (you may need to [download ffmpeg](https://ffmpeg.org/download.html) first):

`ffmpeg -list_devices true -f dshow -i dummy`

It prints a lot of stuff, but in there are the "DirectShow audio devices" with their names.