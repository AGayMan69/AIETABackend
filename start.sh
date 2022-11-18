#!/bin/bash
# Start script for AIETA bluetooth service
cd /home/pi/blue/
/usr/bin/git pull
/usr/bin/python3 rfcomm-server.py
