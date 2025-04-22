@echo off
rem Install required packages
pip install pyinstaller pillow intelhex

rem Build exe with all resources bundled
pyinstaller --noconfirm ^
            --onefile ^
            --noconsole ^
            --name "FlashTool" ^
            --add-data "qr_a_trung.jpg;." ^
            --add-data "NuLink_8051OT.exe;." ^
            --clean ^
            app.py

rem Clean up build files
rmdir /S /Q build
del FlashTool.spec

echo Build completed! Check dist folder for FlashTool.exe
pause
