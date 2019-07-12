# qtube

**qtube** is a frontend for youtube that uses [pyqt](https://www.riverbankcomputing.com/software/pyqt/download5), [youtube-dl](https://github.com/ytdl-org/youtube-dl) and [mpv](https://mpv.io/) (via [python-mpv](https://github.com/jaseg/python-mpv)). 

<p align="middle">
    <img src="assets/image.png" width="90%" /> 
</p>

## Requirements

- Python 3
- youtube-dl
- mpv
- libmpv

## Setup

```
git clone git@github.com:hdbhdb/qtube.git
cd qtube
pip install requirements.txt
```

Then to run qtube:

```
python qtube.py
```

## Features & Usage

- watch and browse YouTube without browser and without ads
- play videos natively within application
- download videos
- queue search results as a playlist
- almost anything you can do with mpv

qtube aims to be highly modifiable. Configuration settings are not currently possible within the application, but you can start [here](https://github.com/hdbhdb/qtube/blob/2753b575e8bc1742f25c979893b33a73b3225417/qtube.py#L19-L31) for modifying basic settings with code. 

Click videos to play natively in player. Right-click for further options (i.e., to download videos). Downloaded videos can be played natively as well. 

Most mpv keybindings will work when the mpv player is selected. See the [mpv manual](https://mpv.io/manual/stable/#keyboard-control) for details on mpv keybindings.  




    