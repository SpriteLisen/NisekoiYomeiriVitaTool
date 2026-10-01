set "RELEASE_DIR=Anagram Editor Release"
pyinstaller --onefile --icon=resources/icon.png --name="Anagram Editor" --distpath="%RELEASE_DIR%" --clean --noconsole anagram_editor.py

xcopy "resources" "%RELEASE_DIR%\resources\" /E /I /Y >nul
xcopy "lang" "%RELEASE_DIR%\lang\" /E /I /Y >nul
xcopy "export" "%RELEASE_DIR%\export\" /E /I /Y >nul

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"