# PySappy2
## What is this?
This is a cross-platform port of [Some Shrug's SapPy](https://github.com/hfmkwi/SapPy).

This program seeks to emulate the functionality of the GBA's sound engine - 
formally known as the M4A engine or colloquially as Sappy - as close as
possible.

This project is still heavily in development. However, playback with a high 
degree of accuracy can be achieved with this emulator in its current state.

## How do I use this?
To use SapPy2, install [FMOD](https://fmod.com/download#fmodengine) following [this guide](https://pyfmodex.readthedocs.io/en/latest/usage/installation.html) and call it from the command line:
```
python3 .\sap.py .\fe6.gba -st 0x3994d8 97
```

Full command line usage is as follows:
```
usage: sap.py [-h] [-st SONG_TABLE] path song_num

positional arguments:
  path                  path to the ROM to play
  song_num

optional arguments:
  -h, --help            show this help message and exit
  -st SONG_TABLE, --song_table SONG_TABLE
                        address of song table in rom
```
