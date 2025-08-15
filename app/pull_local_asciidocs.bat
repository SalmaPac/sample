@echo off
setlocal

:: Configuration
set REPO_URL=https://github.com/green-code-initiative/creedengo-rules-specifications.git
set REPO_DIR=temp_repo
set OUTPUT_DIR=pattern-library

:: Clean up any previous clone
if exist %REPO_DIR% (
    rmdir /s /q %REPO_DIR%
)

:: Clone fresh
git clone %REPO_URL% %REPO_DIR%
if errorlevel 1 (
    echo Failed to clone repo.
    exit /b 1
)

:: Create output directory
if not exist %OUTPUT_DIR% (
    mkdir %OUTPUT_DIR%
)

:: Copy .asciidoc files
for /R %REPO_DIR%\src\main\rules %%F in (*.asciidoc) do (
    python cleaner.py "%%F"
    echo Copying %%F
    copy /Y "%%F" "%OUTPUT_DIR%\"
)

:: Optional cleanup
rmdir /s /q %REPO_DIR%

echo Done.
endlocal
