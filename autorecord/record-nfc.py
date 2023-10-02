from configparser import ConfigParser
import csv
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
import sys
import time
import click
import pytz

DEFAULT_CFG = 'record-nfc.ini'


def execute(cmd, dry_run=False, failure_mode="EXIT"):
    print(sys.argv[0] + ": execute: ", cmd)
    result = None
    errorlevel = 0

    if not dry_run:
        try:
            p = subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as exc:
            errorlevel = exc.returncode

        print(f"execute: Completed with return code {errorlevel}.")

    if errorlevel != 0:
        click.echo("Command failed (err %d): %s" % (errorlevel, cmd))
        if failure_mode == "EXIT":
            if errorlevel > 127:
                errorlevel = 127
            sys.exit(errorlevel)
        elif failure_mode == "RAISE":
            raise RuntimeError(errorlevel)
        elif failure_mode == "IGNORE":
            pass
        elif failure_mode == "RETURN_ERRORLEVEL":
            result = errorlevel
        else:
            raise NotImplementedError(failure_mode)

    return result


def format_filename(dt, filename_template, timestamp_format='%Y-%m-%d %H%M%z'):
    # 4414-Fessenden-St-NW-Washington-DC-NFC-2023-09-25 0000-0400
    full_timestamp = dt.strftime(timestamp_format)
    ret = filename_template.format(full_timestamp=full_timestamp)
    return ret


def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)


def make_local_timestamp_aware(dt_naive):
    # interpret the dt_naive as a local timezone and stamp it as such
    # this is a bit of a hack, but it works
    return pytz.utc.localize(dt_naive)


def now():
    return utc_to_local(datetime.utcnow())


def format_hhmmss(td):
    return str(td).split('.')[0]


def configure(ctx, param, filename):
    cfg = ConfigParser()
    cfg.read(filename)
    try:
        options = dict(cfg['options'])
    except KeyError:
        options = {}
    ctx.default_map = options


@click.command()
@click.option(
    '-c',
    '--config',
    type=click.Path(dir_okay=False),
    default=DEFAULT_CFG,
    callback=configure,
    is_eager=True,
    expose_value=False,
    help='Read option defaults from the specified INI file',
    show_default=True,
)
@click.option('--audio-input-name', default="-d", help='Audio input name.')
@click.option('--sunrise-sunset-filename', default='SunriseSunset.csv', help='SunriseSunset filename.')
@click.option('--sunset-offset', default=1.5, help='Sunset offset.')
@click.option('--sunrise-offset', default=-0.5, help='Sunrise offset.')
@click.option('--test', is_flag=True, help='Run in test mode.')
@click.option('--output-directory', default='.', help='Output directory.')
@click.option('--cloud-storage-directory')
@click.option('--sox-filepath', default="sox.exe")
@click.option('--filename_template', default="recording-location-NFC-{full_timestamp}")
@click.option('-∞', '-t', '--loop-forever', is_flag=True, help='Run in test mode.')
def main(
    # Gain,
    audio_input_name,
    # BirdVoxThreshold,
    # BirdVoxDuration,
    sunrise_sunset_filename,
    sunset_offset,
    sunrise_offset,
    test,
    # PauseForInput,
    output_directory,
    cloud_storage_directory,
    sox_filepath,
    filename_template,
    loop_forever,
):
    script_start_time = now()

    print("Audio Input Name:", audio_input_name)
    print("Sunrise Sunset Filename:", sunrise_sunset_filename)
    print("Sunset Offset:", sunset_offset)
    print("Sunrise Offset:", sunrise_offset)
    print("Test:", test)
    print("Output Directory:", output_directory)
    print("Cloud Storage Directory:", cloud_storage_directory)
    print("Sox Filepath:", sox_filepath)
    print()

    file_type = 'wav'
    test_duration = '00:00:02'

    while True:
        today = None
        today_string = now().strftime("%#m/%#d/")
        # read a csv file with sunrise and sunset times for the year as formatted above.
        with open(sunrise_sunset_filename, "r") as f:
            csvfile = csv.DictReader(f, delimiter=",")

            for row in csvfile:
                dt = row['Date']
                if dt.startswith(today_string):
                    today = row
                    break

        if today:
            sunset_time = datetime.strptime(today["Sunset"], "%H:%M:%S")
            sunrise_time = datetime.strptime(today["Sunrise"], "%H:%M:%S")  # + timedelta(days=1)
            sunset = script_start_time.replace(
                hour=sunset_time.hour, minute=sunset_time.minute, second=sunset_time.second, microsecond=0
            )
            sunrise = script_start_time.replace(
                hour=sunrise_time.hour, minute=sunrise_time.minute, second=sunrise_time.second, microsecond=0
            ) + timedelta(days=1)
            start_record = sunset + timedelta(hours=sunset_offset)
            stop_record = sunrise + timedelta(hours=sunrise_offset)
        else:
            # If no CSV File detected, set to default start/end recording times.
            raise FileNotFoundError()
            print("No SunriseSunset.csv file detected, reverting to default times:")
            start_record = datetime(script_start_time.year, script_start_time.month, script_start_time.day, 21, 0, 0)
            stop_record = start_record + timedelta(days=1, hours=-16)

        # start_record = make_local_timestamp_aware(start_record)
        # stop_record = make_local_timestamp_aware(stop_record)

        print("Start Time:", start_record)
        print("End Time:", stop_record)

        if test:
            print("Running Test Recordings.")
        elif (stop_record - now()).total_seconds() >= 0:
            # If The StartRecord time has not already passed
            print("Will start recording at", start_record.strftime("%H:%M:%S"))
            while (start_record - now()).total_seconds() >= 0:
                time.sleep(1)
            print("\nStarting recording.")
        else:
            print("This script started after the recommended start time. Starting recording immediately.")

        # PM Recording
        start_pm_at = now()
        start_am_at = (start_pm_at + timedelta(days=1)).replace(hour=0, minute=0, second=2, microsecond=0)

        full_output_directory = os.path.join(
            output_directory, start_pm_at.strftime("%Y"), start_pm_at.strftime("%Y-%m-%d")
        )
        os.makedirs(full_output_directory, exist_ok=True)
        print("Outputting to", full_output_directory)
        recorded_files = []
        pm_filename = os.path.join(full_output_directory, format_filename(start_pm_at, filename_template))

        pm_record_time = test_duration if test else format_hhmmss(start_am_at - start_pm_at)

        print(
            "Starting PM Recording:",
            start_pm_at.strftime("%Y-%m-%d %H:%M:%S"),
            "Record Time:",
            pm_record_time,
            pm_filename,
            "Filename:",
            f"{pm_filename}.{file_type}",
        )

        sox_cmd = [
            sox_filepath,
            '-t',
            'waveaudio',
            '-c',
            '1',
            '-r',
            '22050',
            audio_input_name,
            f"{pm_filename}.{file_type}",
            'trim',
            '0',
            pm_record_time,
        ]
        execute(sox_cmd)
        recorded_files.append(f"{pm_filename}.{file_type}")

        # AM Recording
        actual_am_start_time = now()
        am_record_duration = stop_record - actual_am_start_time
        am_filename = None
        if am_record_duration.total_seconds() > 0:
            am_record_time = test_duration if test else format_hhmmss(am_record_duration)
            am_filename = os.path.join(full_output_directory, format_filename(start_am_at, filename_template))
            print(
                "Starting AM Recording:",
                actual_am_start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "Record Time:",
                am_record_time,
                am_filename,
            )

            sox_cmd = [
                sox_filepath,
                '-t',
                'waveaudio',
                '-c',
                '1',
                '-r',
                '22050',
                audio_input_name,
                f"{am_filename}.{file_type}",
                'trim',
                '0',
                am_record_time,
            ]
            execute(sox_cmd)

            recorded_files.append(f"{am_filename}.{file_type}")

        print("Recording Complete:", now().strftime("%Y-%m-%d %H:%M:%S"))

        execute(['nighthawk', '--audacity-output', *recorded_files], failure_mode="IGNORE")

        if file_type == 'wav':
            print("Converting to FLAC...")
            is_ok_to_delete_wavs = True
            sox_cmd = [sox_filepath, f"{pm_filename}.{file_type}", f"{pm_filename}.flac"]
            p = execute(sox_cmd, failure_mode="RETURN_ERRORLEVEL")
            if p != 0:
                print(f"Could not find flac, {p}")
                is_ok_to_delete_wavs = False

            if am_filename:
                sox_cmd = [sox_filepath, f"{am_filename}.{file_type}", f"{am_filename}.flac"]
                p = execute(sox_cmd, failure_mode="RETURN_ERRORLEVEL")
                if p != 0:
                    print(f"Could not find flac, {p}")
                    is_ok_to_delete_wavs = False

            if is_ok_to_delete_wavs:
                print("Deleting wav files...")
                for file in recorded_files:
                    if os.path.exists(file):
                        os.remove(file)
            else:
                print("Did not find converted flac files... Leaving original recordings.")

        # Upload to Cloud Storage
        if cloud_storage_directory:
            print("Copying", full_output_directory, "to", cloud_storage_directory)
            if not os.path.exists(cloud_storage_directory):
                os.makedirs(cloud_storage_directory)

            # copy everything in path to cloud_storage_directory
            for root, dirs, files in os.walk(full_output_directory):
                for file in files:
                    print("Copying", file)
                    shutil.copy(os.path.join(root, file), cloud_storage_directory)

        for file in recorded_files:
            execute(['py', '../nfc-processing/getsnips.py', 'clip', '-i', file])
        execute(
            ['py', '../nfc-processing/getsnips.py', 'spec', f"{full_output_directory}\\clips\\*.wav"],
            failure_mode="IGNORE",
        )

        if not loop_forever:
            break
        print(f'All done for last night!  Waiting {10000/60/60:.1f}h before going around again...')
        time.sleep(10000)


if __name__ == '__main__':
    main()
