@echo off
echo Packing full.
nuitka --standalone config_ui.py --enable-plugin=upx --onefile --enable-plugin=tk-inter --include-data-files=ffmpeg.exe=ffmpeg.exe --include-data-files=ffprobe.exe=ffprobe.exe
rename config.exe full.exe
echo Packing single.
nuitka --standalone main.py --enable-plugin=upx --onefile
echo Packing config.
nuitka --standalone config.py --enable-plugin=upx --onefile --enable-plugin=tk-inter