# Photobook Template

A professional LaTeX template for creating custom photobooks with optimized layouts for print. This template provides a modular structure for organizing photos across multiple days/sections with customizable image arrangements.

## Project Overview

This is a LaTeX-based photobook template designed for creating high-quality photo albums ready for professional printing. It includes:

- **Modular Section Structure**: Organize photos by day or theme using separate TeX files
- **Custom Macros**: Pre-built commands for 1, 2, 3, 4, 6, and 8-image layouts
- **Print-Ready Specifications**: 
  - Page size: 216mm × 303mm (8.5" × 11.93")
  - Margins: 25mm on all sides
  - Center-aligned page numbers
- **ICC Profiles**: Included color profiles (Adobe RGB and FOGRA39) for accurate color reproduction
- **Bibliography Support**: Built-in citation management with BibTeX

## Project Structure

```
photobook_template/
├── main.tex                    # Main LaTeX document (compile this)
├── README.md                   # This file
├── references.bib              # Bibliography file for citations
├── profiloAdobeRGB.icc         # Adobe RGB color profile
├── profiloFOGRA39.icc          # FOGRA39 color profile
├── macros/                     # Custom LaTeX commands
│   ├── commands_1img.tex       # Layout for 1 image per page
│   ├── commands_2img.tex       # Layout for 2 images per page
│   ├── commands_3img.tex       # Layout for 3 images per page
│   ├── commands_4img.tex       # Layout for 4 images per page
│   ├── commands_6img.tex       # Layout for 6 images per page
│   └── commands_8img.tex       # Layout for 8 images per page
├── sections/                   # Content sections
│   ├── giorno1.tex             # First section/day
│   └── giorno2.tex             # Second section/day
└── images/                     # Image assets
    ├── flags/                  # Flag images or icons
    ├── giorno1/                # Images for section 1
    └── giorno2/                # Images for section 2
```

## Dependencies

### Required Software

To build `main.pdf` from `main.tex`, you need to install a complete LaTeX distribution:

#### macOS
Install **MacTeX**, which includes all necessary LaTeX packages:
```bash
brew install mactex
```

Or download from: https://www.tug.org/mactex/

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install texlive-full
```

Or for a minimal installation:
```bash
sudo apt-get install texlive texlive-latex-extra texlive-fonts-recommended
```

#### Linux (Fedora/RHEL)
```bash
sudo dnf install texlive-scheme-full
```

#### Windows
Download and install **MiKTeX** or **TeX Live**:
- **MiKTeX**: https://miktex.org/download
- **TeX Live**: https://www.tug.org/texlive/

### LaTeX Packages Used

The following packages are automatically included and should be part of your LaTeX distribution:
- **scrbook** - KOMA-Script book class
- **geometry** - Page layout control
- **graphicx** - Image insertion
- **placeins** - Image placement
- **fancyhdr** - Header and footer customization
- **adjustbox** - Image adjustments and trimming
- **natbib** - Bibliography management

## Installation & Setup

### 1. Install LaTeX Distribution

Follow the instructions above for your operating system.

### 2. Verify Installation

Test that LaTeX is properly installed:
```bash
pdflatex --version
```

### 3. Clone or Download the Template

```bash
git clone <repository-url> photobook_template
cd photobook_template
```

## Building the PDF

### Basic Compilation

Compile the main document:
```bash
pdflatex main.tex
```

### Full Compilation (with bibliography)

If using citations from `references.bib`:
```bash
pdflatex main.tex
bibtex main.aux
pdflatex main.tex
pdflatex main.tex
```

### Using a LaTeX IDE

If you prefer a GUI, use one of these free editors:
- **TeXstudio**: http://texstudio.sourceforge.net/
- **Overleaf** (online): https://www.overleaf.com/
- **Visual Studio Code** with LaTeX Workshop extension

## PDF Color Conversion for Printing

After compiling your LaTeX to PDF, you may need to convert it to CMYK format for professional printing services. 

### Quick Conversion Scripts

Two automated scripts are provided in the `scripts/` directory to convert your PDF for professional printing:

**Step 1: Convert to Adobe RGB**
```bash
bash scripts/convert_to_rgb.sh main.pdf
```
Output: `intermediate_rgb.pdf`

**Step 2: Convert to CMYK FOGRA39** (for professional printing)
```bash
bash scripts/convert_to_cmyk.sh intermediate_rgb.pdf
```
Output: `output_fogra39.pdf`

**Or use the one-step automation:**
```bash
bash scripts/compile_and_convert.sh main
```
This compiles LaTeX and performs both color conversions automatically.

### Prerequisites

Ghostscript is required for color conversion. Install it:
- **macOS**: `brew install ghostscript`
- **Linux**: `sudo apt install ghostscript`
- **Windows**: Download from https://ghostscript.com/releases

For detailed information about color profiles, ICC settings, and troubleshooting, see [COLORS.md](COLORS.md).

## Creating Your Photobook

### 1. Add Images
Place your photos in the `images/giorno1/` and `images/giorno2/` directories (or create new subdirectories as needed).

### 2. Edit Sections
Edit the files in the `sections/` directory to add your content. For example, in `giorno1.tex`:
```latex
\section{Day 1: Morning}

\TwoImages{images/giorno1/photo1.jpg}{images/giorno1/photo2.jpg}

\ThreeImages{images/giorno1/photo3.jpg}{images/giorno1/photo4.jpg}{images/giorno1/photo5.jpg}
```

### 3. Use Layout Macros
Available commands for different image layouts:
- `\OneImage{path}` - Single image layout
- `\TwoImages{path1}{path2}` - Two images side-by-side
- `\ThreeImages{path1}{path2}{path3}` - Three images
- `\FourImages{path1}{path2}{path3}{path4}` - Four images
- `\SixImages{...}` - Six images grid
- `\EightImages{...}` - Eight images grid

### 4. Compile
Run `pdflatex main.tex` to generate `main.pdf`.

## Print Specifications

- **Page Size**: 216mm × 303mm (8.5" × 11.93")
- **Margins**: 25mm (≈1")
- **Color Profiles**: 
  - Use `profiloAdobeRGB.icc` for digital output
  - Use `profiloFOGRA39.icc` for professional printing
- **Page Numbering**: Centered in footer

## Troubleshooting

### Missing packages
If you get "undefined control sequence" errors, ensure all required packages are installed:
```bash
# macOS
sudo tlmgr install missing-package-name

# Linux
sudo apt-get install texlive-<package-collection>
```

### Image not found errors
Ensure image paths are relative to the main directory and use forward slashes `/` in paths.

### PDF appears blank
Check that:
1. All `\include{}` statements in `main.tex` point to existing files
2. Image files exist and paths are correct
3. No syntax errors in your TeX files (check console output)

## License

This template is provided as-is. Modify freely for your personal use.

## Author

Marco Alberti - December 2025

