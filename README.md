# ZWaveUtils
General Utilities for the Z-Wave 700 & 800 series

# Overview

This repository contains a number of general purpose utilites specifically
for the Silicon Labs Gecko EFR32 series Z-Wave wireless microcontrollers.

There are a variety of different utilities for various functions.
Generally most functions are in individual files which have plenty of comments describing the function provided.

NOTE! THIS IS NOT AN OFFICIAL Silicon Labs project. NO SUPPORT IS AVAILABLE.
This is a personal project for my own enjoyment.

No rights reserved. Please feel free to copy and enhance.

# Utilites

1. ProdTestGen.py - Python program that commands RailTest to function like the 500 series ProdTestGen
    - Production testing utility that will send 10 NOPs when a DUT sends a NIF
    - The number of ACKs is returned and can be used for a quick Pass/Fail test of the RF
2. ZWaveNVM500.py - Python program that pulls the NVM data from a 500 series SerialAPI
    - NVM data contains the Z-Wave Network HomeID/NodeIDs and routing tables
    - First step in upgrading a controller from a 500 series to 700 series without having to rebuild the network
3. ZWaveRSSI.py - Python program that reads the background RSSI values via the SerialAPI
4. zlf\_combiner.sh - bash script that concatenates all \*.zlf trace files in the folder the script is run from into one file, `combined_trace.zlf`.
5. ZWaveFlashSize.py - Python program that reads in the .MAP file and prints out the percentage of FLASH and RAM used for various categories.

# Future Utilities (no schedule so don't hold me to them!)

2. ScopeToggle - Toggle 8-bit value on a GPIO. A fast real-time UART on a oscilliscope for debug.
3. LfrcoCalib - LFRCO calibration to the HFXO which achieves ??? ppm
4. UARTDrv - UART Driver - Initialization of the USART into a simple UART
5. SPIDrv - SPI Driver - Initialization of the USART into a simple SPI interface
9. What other tools do you need???

# Contacts 

Eric Ryherd - drzwave@silabs.com - author and developer

---

# Git Basics

- Extract from github.com - this is a public GIT repository - please be kind!
    - git clone "https://github.com/drzwave/ZWaveUtils.git" <directory_name> - will create a local repository
    - git status -uno - Prints out which files in your local directory have changed or need to be checked in
    - git pull - updates local directory/repository with the main branch
    - git add - adds a file to the repository
    - git commit -a -m "comment goes here" - commits changed files TO YOUR LOCAL REPOSITORY - not to BitBucket!
    - git push - pushes your commits up to the repo - always do a GIT PULL before committing
    - See the many GIT tutorials for more details
