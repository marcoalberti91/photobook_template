# Color Profiles & PDF Conversion Guide

## Color Profile Resources

- **FOGRA39 Profile** (CMYK, print standard): https://www.color.org/registry/Coated_Fogra39L_VIGC_300.xalter
- **Adobe RGB Profile**: https://www.color.org/profiles/srgb_appearance.xalter
- **Quick Online Converter**: https://www.presspdf.com/index-en

---

## Overview

This guide helps you convert LaTeX-generated PDFs from RGB to CMYK format using **Ghostscript**, which is essential for professional printing with services like PixartPrinting.

### Quick Conversion Steps

1. **Convert RGB to Adobe RGB**:
   ```bash
   bash scripts/convert_to_rgb.sh main.pdf
   ```
   Output: `intermediate_rgb.pdf`

2. **Convert to CMYK FOGRA39** (for printing):
   ```bash
   bash scripts/convert_to_cmyk.sh intermediate_rgb.pdf
   ```
   Output: `output_fogra39.pdf`

---

## What is Ghostscript?

Ghostscript is a powerful interpreter for PostScript and PDF files. It allows you to:

- Convert PDF color models (RGB ↔ CMYK)
- Compress PDFs
- Merge or split documents
- Apply ICC color profiles for professional color management

## Installation

### macOS (Homebrew)
```bash
brew install ghostscript
```

### Linux (Ubuntu/Debian)
```bash
sudo apt install ghostscript
```

### Windows
Download the installer from: https://ghostscript.com/releases

---

## Typical LaTeX Workflow

1. **Compile LaTeX normally** (generates RGB PDF):
   ```bash
   pdflatex main.tex
   ```
   Output: `main.pdf` (in RGB)

2. **Convert to RGB with color profile**:
   ```bash
   bash scripts/convert_to_rgb.sh main.pdf
   ```
   Output: `intermediate_rgb.pdf`

3. **Convert to CMYK FOGRA39** (for professional printing):
   ```bash
   bash scripts/convert_to_cmyk.sh intermediate_rgb.pdf
   ```
   Output: `output_fogra39.pdf`

---

## Verify the Conversion

### Using Adobe Acrobat Pro
- Use the Preflight function to verify color space and ICC profile

### Using MuPDF (Command Line)
```bash
mutool info output_fogra39.pdf
```

---

## Ghostscript Parameters Explained

- `sDEVICE=pdfwrite` → Outputs a PDF file
- `sColorConversionStrategy=CMYK` → Forces CMYK conversion
- `sProcessColorModel=DeviceCMYK` → Sets color model to CMYK
- `dOverrideICC` → Ignores embedded ICC profiles
- `sOutputICCProfile=<profile>` → Applies ICC color profile
- `o <output>` → Output filename

---

## Available Scripts

Three automation scripts are provided in the `scripts/` directory:

### 1. convert_to_rgb.sh
Converts a PDF to Adobe RGB color space with color profile embedding.

**Usage:**
```bash
bash scripts/convert_to_rgb.sh input.pdf
```

**Example:**
```bash
bash scripts/convert_to_rgb.sh main.pdf
```

### 2. convert_to_cmyk.sh
Converts a PDF to CMYK FOGRA39 color space (required for professional printing).

**Usage:**
```bash
bash scripts/convert_to_cmyk.sh input.pdf
```

**Example:**
```bash
bash scripts/convert_to_cmyk.sh intermediate_rgb.pdf
```

### 3. compile_and_convert.sh
Complete automation: compile LaTeX and convert to CMYK in one step.

**Usage:**
```bash
bash scripts/compile_and_convert.sh filename
```

**Example:**
```bash
bash scripts/compile_and_convert.sh main
```

This script will automatically:
1. Compile `main.tex` to `main.pdf`
2. Convert to RGB: `intermediate_rgb.pdf`
3. Convert to CMYK: `output_fogra39.pdf`

**Note:** This is the fastest way to go from your LaTeX source to a print-ready PDF!

---

## Troubleshooting

**Ghostscript not found?**
- Ensure it's installed: `gs --version`
- Add to PATH if needed

**Colors look different after conversion?**
- Verify the ICC profile is being applied correctly
- Try using Adobe Acrobat's color settings

**File size too large?**
- Add `-dPDFSETTINGS=/ebook` to reduce file size (may affect quality)
