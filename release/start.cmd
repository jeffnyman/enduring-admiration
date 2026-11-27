@echo off
rem Windows: start the Bible reader. Needs Node.js 22.13 or newer (https://nodejs.org).
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is not installed. Download the LTS version from https://nodejs.org and run this again.
  pause
  exit /b 1
)
node start.mjs %*
if errorlevel 1 pause
