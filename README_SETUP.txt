# ADB Forensic Monitor - Setup Guide

If you have moved this folder to another system, please follow these steps to ensure it works correctly:

## 1. Prerequisites
Ensure the following are installed on your system:
- **Python 3.10 or higher**: [Download here](https://www.python.org/downloads/)
- **Node.js**: [Download here](https://nodejs.org/)
- **ADB (Android Debug Bridge)**: 
  - You can download the "SDK Platform-Tools" from Google.
  - For convenience, you can place `adb.exe` directly inside the `backend` folder of this project, OR add it to your Windows System PATH.

## 2. How to Run
Simply double-click the `START_APP.bat` file in this folder.

The script will automatically:
- Create a Python virtual environment and install backend dependencies.
- Install frontend Node.js packages if they are missing.
- Start both the server and the dashboard.
- Open your browser to the dashboard automatically.

## 3. Important Note on Zipping
When zipping this project to share:
- You **can exclude** the `backend/venv` and `frontend/node_modules` folders to make the zip file much smaller. 
- The `START_APP.bat` script is designed to recreate these folders automatically on the new system as long as Python and Node.js are installed.

## 4. Troubleshooting
- **Backend fails to start**: Check if another application is using port 5000.
- **Frontend fails to start**: Check if another application is using port 5173.
- **No devices detected**: Ensure "USB Debugging" is enabled on your Android phone and you have trusted the computer's connection on the phone screen.
