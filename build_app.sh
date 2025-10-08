#!/bin/bash

echo "=================================================="
echo "Building macOS Application Bundle"
echo "=================================================="
echo ""

# Check if py2app is installed
if ! python3 -c "import py2app" 2>/dev/null; then
    echo "Installing py2app..."
    pip3 install py2app
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Build the app
echo "Building application..."
python3 setup.py py2app

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo "✓ Build successful!"
    echo "=================================================="
    echo ""
    echo "Application created at: dist/Disk Monitor.app"
    echo ""
    echo "To install:"
    echo "  cp -r 'dist/Disk Monitor.app' /Applications/"
    echo ""
else
    echo ""
    echo "❌ Build failed"
    exit 1
fi
