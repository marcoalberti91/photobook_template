#!/bin/bash
# Convert PDF to Adobe RGB color space with color profile embedding
# Usage: bash convert_to_rgb.sh input.pdf

if [ $# -eq 0 ]; then
    echo "Usage: bash convert_to_rgb.sh input.pdf"
    echo "Example: bash convert_to_rgb.sh main.pdf"
    echo "Output: intermediate_rgb.pdf"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="intermediate_rgb.pdf"

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: File '$INPUT_FILE' not found"
    exit 1
fi

# Check if Ghostscript is installed
if ! command -v gs &> /dev/null; then
    echo "Error: Ghostscript is not installed"
    echo "Please install it:"
    echo "  macOS: brew install ghostscript"
    echo "  Linux: sudo apt install ghostscript"
    exit 1
fi

echo "Converting '$INPUT_FILE' to Adobe RGB..."
echo "Output: $OUTPUT_FILE"

gs -dNOPAUSE -dBATCH -sDEVICE=pdfwrite \
   -sOutputICCProfile=profiloAdobeRGB.icc \
   -o "$OUTPUT_FILE" \
   "$INPUT_FILE"

if [ $? -eq 0 ]; then
    echo "✓ Conversion successful: $OUTPUT_FILE"
else
    echo "✗ Conversion failed"
    exit 1
fi
