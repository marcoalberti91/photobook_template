#!/bin/bash
# Complete automation: compile LaTeX and convert to CMYK FOGRA39 in one step
# Usage: bash compile_and_convert.sh filename (without .tex extension)

if [ $# -eq 0 ]; then
    echo "Usage: bash compile_and_convert.sh filename"
    echo "Example: bash compile_and_convert.sh main"
    echo ""
    echo "This script will:"
    echo "  1. Compile filename.tex to filename.pdf"
    echo "  2. Convert to RGB: intermediate_rgb.pdf"
    echo "  3. Convert to CMYK: output_fogra39.pdf"
    exit 1
fi

FILENAME="$1"
TEX_FILE="$FILENAME.tex"
PDF_FILE="$FILENAME.pdf"

# Check if .tex file exists
if [ ! -f "$TEX_FILE" ]; then
    echo "Error: File '$TEX_FILE' not found"
    exit 1
fi

# Check if pdflatex is installed
if ! command -v pdflatex &> /dev/null; then
    echo "Error: pdflatex is not installed"
    echo "Please install LaTeX (e.g., MacTeX or TeX Live)"
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

echo "========================================="
echo "Step 1: Compiling LaTeX..."
echo "========================================="
pdflatex "$TEX_FILE"

if [ ! -f "$PDF_FILE" ]; then
    echo "✗ LaTeX compilation failed"
    exit 1
fi

echo "✓ LaTeX compilation successful: $PDF_FILE"
echo ""

echo "========================================="
echo "Step 2: Converting to Adobe RGB..."
echo "========================================="
bash scripts/convert_to_rgb.sh "$PDF_FILE"

if [ ! -f "intermediate_rgb.pdf" ]; then
    echo "✗ RGB conversion failed"
    exit 1
fi

echo ""
echo "========================================="
echo "Step 3: Converting to CMYK FOGRA39..."
echo "========================================="
bash scripts/convert_to_cmyk.sh "intermediate_rgb.pdf"

echo ""
echo "========================================="
echo "✓ All conversions complete!"
echo "========================================="
echo ""
echo "Output files:"
echo "  • Original: $PDF_FILE"
echo "  • RGB: intermediate_rgb.pdf"
echo "  • CMYK (print-ready): output_fogra39.pdf"
echo ""
echo "The 'output_fogra39.pdf' file is ready for professional printing!"
