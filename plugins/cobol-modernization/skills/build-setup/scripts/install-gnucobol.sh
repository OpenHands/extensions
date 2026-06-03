#!/bin/bash
# Install GnuCOBOL compiler for COBOL-to-Java migration projects

set -euo pipefail

echo "Installing GnuCOBOL..."

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y gnucobol
    elif command -v yum &> /dev/null; then
        sudo yum install -y gnucobol
    else
        echo "Error: Unsupported Linux package manager"
        exit 1
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    if command -v brew &> /dev/null; then
        brew install gnucobol
    else
        echo "Error: Homebrew not found. Install from https://brew.sh"
        exit 1
    fi
else
    echo "Error: Unsupported OS: $OSTYPE"
    exit 1
fi

echo "Verifying installation..."
cobc --version
echo "GnuCOBOL installed successfully!"
