#!/bin/bash
# Convert PDF from RGB to CMYK FOGRA39 color space (required for professional printing)
# Usage: bash convert_to_cmyk.sh input.pdf

if [ $# -eq 0 ]; then
    echo "Usage: bash convert_to_cmyk.sh input.pdf"
    echo "Example: bash convert_to_cmyk.sh intermediate_rgb.pdf"
    echo "Output: output_fogra39.pdf"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="output_fogra39.pdf"

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

echo "Converting '$INPUT_FILE' to CMYK FOGRA39..."
echo "Output: $OUTPUT_FILE"

gs -dSAFER -dBATCH -dNOPAUSE \
   -sDEVICE=pdfwrite \
   -o "$OUTPUT_FILE" \
   -sProcessColorModel=DeviceCMYK \
   -sColorConversionStrategy=CMYK \
   -sColorConversionStrategyForImages=CMYK \
   -dOverrideICC \
   -sOutputICCProfile=profiloFOGRA39.icc \
   -sSourceObjectICCProfile=profiloFOGRA39.icc \
   -sSourceRenderingIntent=RelativeColorimetric \
   "$INPUT_FILE"

if [ $? -eq 0 ]; then
    echo "✓ Conversion successful: $OUTPUT_FILE"
    echo "File is now ready for professional printing!"
else
    echo "✗ Conversion failed"
    exit 1
fi
