# Jlink-rtt-logger_for_TEKO
Cross-platform Python tool to automatically capture, timestamp, and save J-Link RTT logs with intelligent text filtering.
# 📟 RTT Auto Logger

**Automated J-Link RTT Log Capture with Timestamps and Text Filtering**

A lightweight, cross-platform Python utility designed to seamlessly capture, timestamp, and save logs from J-Link RTT (Real-Time Transfer) interfaces. It automatically generates log files with date/time stamps and filters out annoying control characters, making your embedded debugging experience much cleaner.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- 🕒 **Automatic Timestamps:** Injects precise system timestamps (down to milliseconds) into every log line.
- 📂 **Smart File Naming:** Automatically creates log files named with the exact date and time of launch (e.g., `RTT_log_2026-08-31_14-30-00.txt`).
- 🧹 **Text Filtering:** Automatically strips out invisible control characters, null bytes, and ANSI escape sequences that often corrupt RTT logs.
- 🔄 **Auto-Reconnect:** Keeps listening and automatically reconnects if the J-Link connection drops.
-  **Cross-Platform:** Works flawlessly on both Windows and Linux.
- 🚀 **One-Click Launch:** Includes ready-to-use Batch (Windows) and Bash (Linux) scripts to start the J-Link server and the logger simultaneously.

## 🛠️ Prerequisites

- Python 3.8 or higher.
- SEGGER J-Link Software and Documentation Pack (specifically `JLinkGDBServerCL`).
- A target microcontroller with RTT enabled in your firmware.

## 🚀 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/rtt-auto-logger.git
   cd rtt-auto-logger



No external Python packages are required! The script uses only the Python Standard Library.
⚙️ Usage
Basic Run
Simply run the script. It will connect to the local J-Link server, start capturing logs, and save them to the current directory.
bash

1
Command Line Arguments
Argument
Short
Description
--directory
-d
Specify a custom directory to save log files.
--host
-H
J-Link server host (default: localhost).
--port
-p
RTT Telnet port (default: 19021).
--reconnect
Enable automatic reconnection if the connection drops.
--no-filter
Disable control character filtering (show raw data).
Examples:
bash

12345
🎯 One-Click Auto-Start (Recommended)
To avoid launching the J-Link server and the Python logger separately, use the provided wrapper scripts. They start the J-Link GDB Server in the background, wait for it to initialize, and then launch the logger.
For Windows:
Run start_rtt_logger.bat. (Make sure to update the J-Link path and device name inside the script if necessary).
For Linux:
bash

12
📊 Example Output
Console & File Output:
text

123
Generated File Name:
text

1
📜 License
This project is licensed under the MIT License - see the LICENSE file for details.
Happy debugging! 🐛🔍
