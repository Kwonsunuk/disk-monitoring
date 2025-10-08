#!/bin/bash

echo "=================================================="
echo "External Disk Monitor - Installation Script"
echo "=================================================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✓ Python $PYTHON_VERSION detected"
echo ""

# Install pip dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

echo "✓ Python dependencies installed"
echo ""

# Check for smartmontools (optional)
if command -v smartctl &> /dev/null; then
    echo "✓ smartmontools detected (temperature monitoring enabled)"
else
    echo "⚠️  smartmontools not found (temperature monitoring disabled)"
    echo "   To enable temperature monitoring, install smartmontools:"
    echo "   brew install smartmontools"
fi
echo ""

# Make script executable
chmod +x disk_monitor_gui.py

echo "=================================================="
echo "✓ Installation complete!"
echo "=================================================="
echo ""
echo "To run the application:"
echo "  python3 disk_monitor_gui.py"
echo ""
echo "Optional: Install smartmontools for temperature monitoring:"
echo "  brew install smartmontools"
echo ""
