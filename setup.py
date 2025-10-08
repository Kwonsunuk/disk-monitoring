"""
Setup script for creating macOS application bundle
Usage: python3 setup.py py2app
"""

from setuptools import setup

APP = ['disk_monitor_gui.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'iconfile': None,
    'plist': {
        'CFBundleName': 'Disk Monitor',
        'CFBundleDisplayName': 'External Disk Monitor',
        'CFBundleGetInfoString': "Monitor external disk temperature and I/O speeds",
        'CFBundleIdentifier': "com.diskmonitor.app",
        'CFBundleVersion': "1.0.0",
        'CFBundleShortVersionString': "1.0.0",
        'NSHumanReadableCopyright': "Copyright © 2025",
    },
    'packages': ['PyQt5', 'psutil'],
}

setup(
    name='Disk Monitor',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
