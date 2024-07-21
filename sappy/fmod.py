# -*- coding: utf-8 -*-
"""Set path to FMOD dynamic link library."""
import os
import platform

systems = {
    'Windows': 'Windows',
    'Darwin': 'Mac',
    'Linux': 'Linux',
}

machines = {
    'x86': 'x86',
    'i386': 'x86',
    'i686': 'x86',
    'x64': 'x64',
    'x86_64': 'x64',
    'AMD64': 'x64',
    'arm': 'arm',
    'armv6l': 'arm',
    'armv7l': 'arm',
    'arm64': 'arm64',
    'aarch64': 'arm64',
    'aarch64_be': 'arm64',
    'armv8b': 'arm64',
    'armv8l': 'arm64',
}

fmod_filenames = {
    'Windows': 'fmod.dll',
    'Mac': 'libfmod.dylib',
    'Linux': 'libfmod.so',
}

def set_fmod_path():
    system = systems[platform.system()]
    machine = machines[platform.machine()]
    fmod_filename = fmod_filenames[system]
    fmod_path = os.path.join(os.path.dirname(__file__), '../lib/', system, machine, fmod_filename)
    os.environ['PYFMODEX_DLL_PATH'] = fmod_path
