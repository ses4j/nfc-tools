import os
import re
from datetime import timedelta
from typing import Union
import click
from matplotlib.pyplot import figure
import numpy as np
import soundfile as sf
from scipy import signal
import matplotlib.pyplot as plt
import librosa
import librosa.display

import matplotlib.ticker as ticker


def _add_spec_to_axes(
    clip,
    duration,
    ax,
    n_fft,
    hop_length=None,
    win_length=None,
    window=signal.windows.blackman,
):
    #             ax.set_title(f"{window} {min(n_fft, win_length)}", fontsize=4)
    # ax.xaxis.set_visible(False)
    # ax.yaxis.set_visible(False)
    # ax.yaxis.set_ticklabels([])

    # plt.gca().set_axis_off()
    S = np.abs(
        librosa.stft(
            clip,
            hop_length=hop_length,
            win_length=min(n_fft, win_length) if win_length else None,
            window=window,
            n_fft=n_fft,  # fft must be equal to or greater than win_length
        )
    )
    librosa.display.specshow(
        librosa.amplitude_to_db(S, ref=np.max),
        cmap="gray_r",
        y_axis="hz",
        x_axis="ms",
        hop_length=hop_length,
        # window=window,
        ax=ax,
    )
    # ax.xaxis.set_major_formatter(PrecisionDateFormatter("%H:%M:%S.{ms}"))
    ax.label_outer()

    # draw vertical line from (70,100) to (70, 250)
    y2 = y1 = 7000
    yellow_line_duration = 0.05
    x1 = duration / 2.0 - yellow_line_duration / 2.0
    x2 = x1 + yellow_line_duration
    ax.plot([x1, x2], [y1, y2], "y-", lw=0.5)


def create_spectrogram(
    fn_audio,
    fn_gram,
    offset=None,
    duration=None,
    n_fft=256,
    hop_length=16,
    window=signal.windows.blackman,
    min_frequency=None,
    max_frequency=None,
    auto_center=False,
):

    # duration = 3.0 - offset * 2.0
    # # offset = 0
    # duration = 1.0
    entire_clip, sample_rate = librosa.load(
        fn_audio, sr=None  # , offset=offset, duration=duration
    )
    total_infile_duration = librosa.get_duration(entire_clip, sr=sample_rate)

    if auto_center:
        S, phase = librosa.magphase(librosa.stft(entire_clip))
        rms_data = librosa.feature.rms(S=S)
        loudest_time = (
            rms_data.argmax() / len(rms_data[0]) * len(entire_clip) / sample_rate
        )

        print(f"loudest time is {loudest_time}")

        duration = 0.3 if duration is None else duration
        offset = loudest_time - duration / 2.0

    if offset is None and duration is not None:
        offset = (total_infile_duration - duration) / 2.0
    elif offset is not None and duration is None:
        duration = 0.3

    clip, sample_rate = librosa.load(
        fn_audio,
        sr=None,
        offset=offset,
        duration=duration
        # offset=loudest_time,
        # duration=duration,
    )
    duration = librosa.get_duration(clip, sr=sample_rate)

    win_length = None  # n_fft
    fig = plt.figure(figsize=(8.00, 6.00), dpi=100)
    axes = fig.subplots()
    _add_spec_to_axes(
        clip,
        ax=axes,
        duration=duration,
        n_fft=n_fft,
        hop_length=hop_length,
        win_length=win_length,
        window=window,
    )

    axes.set(ylim=[min_frequency, max_frequency])

    # fig.tight_layout()
    # plt.show()
    fig.savefig(
        fn_gram,
        dpi=100,
        bbox_inches="tight",
        pad_inches=0,
    )
    click.echo(f'Wrote spectrogram to "{fn_gram}".')
    plt.close(fig)


# create_spectrogram(
#     "clips\\NFC-2021-09-10 0000 000913-deep desc zeep 6.25k-8.5k 58ms.wav",
#     "my_plot.png",
#     zoom=500,
# )


def construct_safe_filename(s):
    s = re.sub(r"[/\\]", "_", s)
    s = re.sub(r"\?", " maybe", s)
    return s


def get_frame(timestamp: Union[float, timedelta], samplerate: int):
    timestamp_secs = (
        timestamp.total_seconds() if hasattr(timestamp, "total_seconds") else timestamp
    )
    return int(round(timestamp_secs * samplerate))


def write_clip(infile, outputdir, timestamp, description, length_secs: float = 3.0):
    fileinfo = sf.info(infile)
    basefilename = os.path.splitext(os.path.split(infile)[1])[0]

    sec = round(timestamp.total_seconds())
    hours = sec // 3600
    minutes = (sec // 60) - (hours * 60)
    seconds = int(sec - hours * 3600 - minutes * 60)

    description = construct_safe_filename(description)
    desc = f"{hours:02d}{minutes:02d}{seconds:02d}-{description}"
    outfile = os.path.join(outputdir, f"{basefilename} {desc}.wav")
    samplerate = fileinfo.samplerate
    start_ts = timestamp - timedelta(seconds=length_secs / 2.0)
    start_frame = get_frame(start_ts, samplerate)
    clip_wav_data, _ = sf.read(
        infile, frames=get_frame(length_secs, samplerate), start=start_frame
    )
    with sf.SoundFile(
        outfile,
        "w",
        fileinfo.samplerate,
        channels=fileinfo.channels,
        subtype=fileinfo.subtype,
    ) as f:
        f.write(clip_wav_data)

    print(f"Wrote {timestamp} into {outfile}")


# # print(data)
# clip(infile, timestamp=timedelta(minutes=1, seconds=7), description="singleup")
@click.group()
@click.option("--debug/--no-debug", default=False)
def cli(debug):
    click.echo(f"Debug mode is {'on' if debug else 'off'}")


@cli.command()
@click.option(
    "-i", "--infile", required=True, type=str, help="wav/flac file to clip from"
)
@click.option(
    "-n",
    "--notesfile",
    required=False,
    type=str,
    help="if given, file to source clip timestamps from. otherwise, expects it to be <infile_base>.notes or <infile_base>._detections.csv",
)
def clip(infile, notesfile):
    # infile = "NFC-2021-09-10 0000.flac"
    assert os.path.exists(infile)
    basename, ext = os.path.splitext(infile)
    assert ext.lower() in [".flac", ".wav"]

    if not notesfile:
        notesfile = basename + ".txt"
    if not os.path.exists(notesfile):
        notesfile = basename + "_detections.csv"

    assert os.path.exists(notesfile), notesfile

    outputdir = os.path.join(os.path.dirname(infile), "clips")
    os.makedirs(outputdir, exist_ok=True)
    """
start_sec,end_sec,filename,path,order,prob_order,family,prob_family,group,prob_group,species,prob_species,predicted_category,prob
30.200000000000003,32.0,vinalhaven-nfc-2021-08-14-2230.wav,Q:\birdrecordings\vinalhaven-nfc-2021-08\vinalhaven-nfc-2021-08-14-2230.wav,Passeriformes,0.97104126,Parulidae,0.951334,SBUF,0.9273938,,,SBUF,0.9273937940597534
132.4,134.20000000000002,vinalhaven-nfc-2021-08-14-2230.wav,Q:\birdrecordings\vinalhaven-nfc-2021-08\vinalhaven-nfc-2021-08-14-2230.wav,Passeriformes,0.9721271,Parulidae,0.9554213,ZEEP,0.9575265,norwat,0.9999989,norwat,0.999998927116394
227.4,228.8,vinalhaven-nfc-2021-08-14-2230.wav,Q:\birdrecordings\vinalhaven-nfc-2021-08\vinalhaven-nfc-2021-08-14-2230.wav,Passeriformes,0.96027213,Parulidae,0.9154916,ZEEP,0.88409126,,,ZEEP,0.8840912580490112
232.4,234.0,vinalhaven-nfc-2021-08-14-2230.wav,Q:\birdrecordings\vinalhaven-nfc-2021-08\vinalhaven-nfc-2021-08-14-2230.wav,Passeriformes,0.97222793,Parulidae,0.9563978,,,bawwar,0.99999833,bawwar,0.9999983310699463
"""

    notes_format = 'scottold'
    with open(notesfile) as f:
        for line in f:
            line = line.strip()
            if line == 'start_sec,end_sec,filename,path,order,prob_order,family,prob_family,group,prob_group,species,prob_species,predicted_category,prob':
                notes_format = 'nighthawk'
                continue
            if notes_format == 'nighthawk':
                start_sec,end_sec,filename,path,order,prob_order,family,prob_family,group,prob_group,species,prob_species,predicted_category,prob = line.split(',')
                if float(prob) < .99:
                    continue
                midpoint_sec = (float(start_sec) + float(end_sec)) / 2.0
                diff = float(end_sec) - float(start_sec)
                timestamp = timedelta(seconds=midpoint_sec)
                description = predicted_category or 'unknown'
                length_secs = max(3.0, diff + 2.0)
            else:
                if line.startswith("#"):
                    continue
                m = re.match(r"(\d\d)(\d\d)(\d\d[\.\d]*)[ ]+(.*)", line)
                if m is None:
                    print(f"skipping {line}, cannot parse.")
                    continue
                hours = int(m.group(1))
                minutes = int(m.group(2))
                seconds = float(m.group(3))
                timestamp = timedelta(hours=hours, minutes=minutes, seconds=seconds)
                description = re.sub("[:]", "-", m.group(4))
                length_secs=3

            write_clip(infile, outputdir, timestamp=timestamp, description=description, length_secs=length_secs)


@cli.command()
@click.option("-i", "--infile", required=True, type=str, help="")
@click.option("-m", "--min", required=False, type=int, help="")
@click.option("-M", "--max", required=False, type=int, help="")
@click.option(
    "-o",
    "--offset",
    required=False,
    type=float,
    help="Time (in seconds) of start of spectrogram.",
)
@click.option(
    "-d",
    "--duration",
    required=False,
    type=float,
    help="Duration (in seconds) of clip to spectrogram.",
)
def spec(infile, min, max, offset, duration):
    assert os.path.exists(infile)
    basename, ext = os.path.splitext(infile)
    outfile = f"{basename}-spec.png"
    create_spectrogram(
        infile,
        outfile,
        min_frequency=min,
        max_frequency=max,
        duration=duration,
        offset=offset,
    )
    # os.system(f'start "{outfile}"')
    import subprocess

    os.startfile(outfile)
    # subprocess.run(["start", outfile], check=True)


if __name__ == "__main__":
    cli()
