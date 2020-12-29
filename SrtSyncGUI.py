# img_viewer.py
"""Perform linear time correction on a subtitle."""

from __future__ import division

import PySimpleGUI as sg
import os.path

import srt
import datetime
import srt_tools.utils
import logging

import sys

log = logging.getLogger(__name__)

# Subtitle Functions

def timedelta_to_milliseconds(delta):
    return delta.days * 86400000 + delta.seconds * 1000 + delta.microseconds / 1000


def parse_args():
    def srt_timestamp_to_milliseconds(parser, arg):
        try:
            delta = srt.srt_timestamp_to_timedelta(arg)
        except ValueError:
            parser.error("not a valid SRT timestamp: %s" % arg)
        else:
            return timedelta_to_milliseconds(delta)

    examples = {
        "Stretch out a subtitle so that second 1 is 2, 2 is 4, etc": "srt linear-timeshift --f1 00:00:01,000 --t1 00:00:01,000 --f2 00:00:02,000 --t2 00:00:03,000"
    }

    parser = srt_tools.utils.basic_parser(description=__doc__, examples=examples)
    parser.add_argument(
        "--from-start",
        "--f1",
        type=lambda arg: srt_timestamp_to_milliseconds(parser, arg),
        required=True,
        help="the first desynchronised timestamp",
    )
    parser.add_argument(
        "--to-start",
        "--t1",
        type=lambda arg: srt_timestamp_to_milliseconds(parser, arg),
        required=True,
        help="the first synchronised timestamp",
    )
    parser.add_argument(
        "--from-end",
        "--f2",
        type=lambda arg: srt_timestamp_to_milliseconds(parser, arg),
        required=True,
        help="the second desynchronised timestamp",
    )
    parser.add_argument(
        "--to-end",
        "--t2",
        type=lambda arg: srt_timestamp_to_milliseconds(parser, arg),
        required=True,
        help="the second synchronised timestamp",
    )
    return parser.parse_args()


def calc_correction(to_start, to_end, from_start, from_end):
    angular = (to_end - to_start) / (from_end - from_start)
    linear = to_end - angular * from_end
    return angular, linear


def correct_time(current_msecs, angular, linear):
    return round(current_msecs * angular + linear)


def correct_timedelta(bad_delta, angular, linear):
    bad_msecs = timedelta_to_milliseconds(bad_delta)
    good_msecs = correct_time(bad_msecs, angular, linear)
    good_delta = datetime.timedelta(milliseconds=good_msecs)
    return good_delta


def linear_correct_subs(subtitles, angular, linear):
    for subtitle in subtitles:
        subtitle.start = correct_timedelta(subtitle.start, angular, linear)
        subtitle.end = correct_timedelta(subtitle.end, angular, linear)
        yield subtitle

# First the window layout in 2 columns

file_list_column = [
    [
        sg.Text("Subtitle Folder"),
        sg.In(size=(25, 1), enable_events=True, key="-FOLDER-"),
        sg.FolderBrowse(initial_folder="D:/Video/"),
    ],
    [
        sg.Listbox(
            values=[], enable_events=True, size=(40, 20), key="-FILE LIST-"
        )
    ],
]

if os.path.exists("savedtimes.txt"):
    fr = open("savedtimes.txt", "r")
    times_list = fr.read().split('\n')
    print(times_list)
else:
    times_list = ['00:00:00,000', '00:00:00,000', '00:00:00,000', '00:00:00,000']

# For now will only show the name of the file that was chosen
srt_column = [
    [sg.Text("Choose an SRT from list on left:")],
    [sg.Text(size=(80, 1), key="-TOUT-")],
    [sg.Text(text="First SRT time: "), sg.InputText(key='-F1-', default_text=times_list[0])],
    [sg.Text(text="First Video time: "), sg.InputText(key='-T1-', default_text=times_list[1])],
    [sg.Text(text="Second SRT time: "), sg.InputText(key='-F2-', default_text=times_list[2])],
    [sg.Text(text="Second Video time: "), sg.InputText(key='-T2-', default_text=times_list[3])],
    [sg.Text(text="Encoding: "), sg.DropDown(['utf-8', 'latin-1'], default_value='utf-8', key='-encoding-')],
    [sg.Button("OK", key='-SYNC-')],
    [sg.Text(size=(80, 3), key="-TOUT2-")]
]

# ----- Full layout -----
layout = [
    [
        sg.Column(file_list_column),
        sg.VSeperator(),
        sg.Column(srt_column),
    ]
]

window = sg.Window("Srt Sync", layout)

while True:
    event, values = window.read()
    if event == "Exit" or event == sg.WIN_CLOSED:
        break
    # Folder name was filled in, make a list of files in the folder
    if event == "-FOLDER-":
        folder = values["-FOLDER-"]
        try:
            # Get list of files in folder
            file_list = os.listdir(folder)
        except:
            file_list = []

        fnames = [
            f
            for f in file_list
            if os.path.isfile(os.path.join(folder, f))
            and f.lower().endswith((".srt"))
        ]
        window["-FILE LIST-"].update(fnames)
    elif event == "-FILE LIST-":  # A file was chosen from the listbox
        try:
            filename = os.path.join(
                values["-FOLDER-"], values["-FILE LIST-"][0]
            )
            window["-TOUT-"].update(filename)
        except:
            pass
    elif event == "-SYNC-":
        # window["-TOUT2-"].update(values["-F1-"])
        sys.argv = ["SrtSyncGUI.py", "--input", filename, "--f1", values["-F1-"], "--f2", values["-F2-"], "--t1", values["-T1-"],
                    "--t2",  values["-T2-"], "--output", filename.replace('.srt', '_c.srt'), "--encoding", values["-encoding-"]]
        
        print(sys.argv)
        args = parse_args()

        f = open("savedtimes.txt", "w")
        f.write(values["-F1-"] + '\n' + values["-T1-"] + '\n' + values["-F2-"] + '\n' + values["-T2-"])
        f.close()

        logging.basicConfig(level=args.log_level)
        angular, linear = calc_correction(
            args.to_start, args.to_end, args.from_start, args.from_end
        )
        srt_tools.utils.set_basic_args(args)
        try:
            corrected_subs = linear_correct_subs(args.input, angular, linear)
            output = srt_tools.utils.compose_suggest_on_fail(corrected_subs, strict=args.strict)
            try:
                args.output.write(output)
                args.output.close()
            except (UnicodeEncodeError, TypeError):  # Python 2 fallback
                args.output.write(output.encode(args.encoding))
            window["-TOUT2-"].update("Success!")
        except Exception as e:
            window["-TOUT2-"].update("Try a different encoding\n" + str(e))

        
            
        '''angular, linear = calc_correction(
            values["-T1-"], values["-T2-"], values["-F1-"], values["-F2-"]
        )'''

window.close()



