# PySappy2
## What is this?
This is a cross-platform port of [Some Shrug's SapPy](https://github.com/hfmkwi/SapPy).

This program seeks to emulate the functionality of the GBA's sound engine - 
formally known as the M4A engine or colloquially as Sappy - as close as
possible.

This project is still heavily in development. However, playback with a high 
degree of accuracy can be achieved with this emulator in its current state.

## Prerequisites
```sh
pip install pyfmodex
# for Windows users:
pip install windows-curses
```

## How do I use this?
To use SapPy2, simply call it from the command line:
```sh
python3 .\sap.py .\fe6.gba -st 0x3994d8 15
```

Full command line usage is as follows:
```
usage: sap.py [-h] [-st SONG_TABLE] path song_num

positional arguments:
  path                  path to the ROM to play
  song_num

options:
  -h, --help            show this help message and exit
  -st SONG_TABLE, --song_table SONG_TABLE
                        address of song table in rom
```

## TSG

### Issue: pyfmodex failed to find fmod

Install [FMOD](https://fmod.com/download#fmodengine) and fix `fmod_path` in [sappy/fmod.py](sappy/fmod.py) following [this guide](https://pyfmodex.readthedocs.io/en/latest/usage/installation.html).

### Issue: `_curses.error: curses function returned NULL`

The terminal is too small, try to run it in full screen mode.
