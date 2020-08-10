# SrtSyncGUI
A Python program with a GUI to sync subtitles with the wrong framerate.
If your SRT subtitles keep getting out of sync with audio/video (a single shift doesn't work for long), this is the tool for you.

All you need to do is look at the time for a spoken line early in the video, and a line later in the video, then check the time for the same 2 lines in the SRT file.
Input the SRT file and the times, and this program will create a synced file in the same folder as the previous SRT (with _c added to the name).

Times should be in the format: 00:00:00,000

Uses PySimpleGUI for the interface, and the srt library for parsing subtitle times.

To download the dependencies with the project, use git clone --recurse-submodules.
