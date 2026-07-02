# PDF Processing Advanced Reference

## pypdfium2 Library

Python binding for PDFium (Chromium's PDF library). Excellent for fast rendering.

### Render PDF to Images
```python
import pypdfium2 as pdfium

pdf = pdfium.PdfDocument("document.pdf")
page = pdf[0]
bitmap = page.render(scale=2.0)
img = bitmap.to_pil()
img.save("page_1.png", "PNG")
```

### Extract Text
```python
import pypdfium2 as pdfium

pdf = pdfium.PdfDocument("document.pdf")
for i, page in enumerate(pdf):
    text = page.get_text()
    print(f"Page {i+1}: {len(text)} chars")
```

## JavaScript Libraries

### pdf-lib (MIT License)

#### Load and Modify PDF
```javascript
import { PDFDocument } from 'pdf-lib';
import fs from 'fs';

async function manipulatePDF() {
    const existingPdfBytes = fs.readFileSync('input.pdf');
    const pdfDoc = await PDFDocument.load(existingPdfBytes);

    const newPage = pdfDoc.addPage([600, 400]);
    newPage.drawText('Added by pdf-lib', { x: 100, y: 300, size: 16 });

    const pdfBytes = await pdfDoc.save();
    fs.writeFileSync('modified.pdf', pdfBytes);
}
```

#### Merge PDFs
```javascript
import { PDFDocument } from 'pdf-lib';

async function mergePDFs() {
    const mergedPdf = await PDFDocument.create();

    const pdf1 = await PDFDocument.load(fs.readFileSync('doc1.pdf'));
    const pdf2 = await PDFDocument.load(fs.readFileSync('doc2.pdf'));

    const pdf1Pages = await mergedPdf.copyPages(pdf1, pdf1.getPageIndices());
    pdf1Pages.forEach(page => mergedPdf.addPage(page));

    const pdf2Pages = await mergedPdf.copyPages(pdf2, [0, 2, 4]);
    pdf2Pages.forEach(page => mergedPdf.addPage(page));

    fs.writeFileSync('merged.pdf', await mergedPdf.save());
}
```

### pdfjs-dist (Mozilla)

#### Extract Text with Coordinates
```javascript
import * as pdfjsLib from 'pdfjs-dist';

async function extractText() {
    const pdf = await pdfjsLib.getDocument('document.pdf').promise;

    for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const textContent = await page.getTextContent();

        const textWithCoords = textContent.items.map(item => ({
            text: item.str,
            x: item.transform[4],
            y: item.transform[5]
        }));
    }
}
```

## Advanced Command-Line

### poppler-utils

```bash
# Text with bounding boxes
pdftotext -bbox-layout document.pdf output.xml

# High-res conversion
pdftoppm -png -r 300 document.pdf output_prefix
pdftoppm -jpeg -jpegopt quality=85 -r 200 document.pdf jpeg_output

# Extract images
pdfimages -j -p document.pdf page_images
pdfimages -list document.pdf  # List without extracting
```

### qpdf Advanced

```bash
# Split into groups
qpdf --split-pages=3 input.pdf output_%02d.pdf

# Complex page extraction
qpdf input.pdf --pages input.pdf 1,3-5,8,10-end -- extracted.pdf

# Optimize for web
qpdf --linearize input.pdf optimized.pdf

# Repair corrupted
qpdf --check input.pdf
qpdf --fix-qdf damaged.pdf repaired.pdf

# Encryption with permissions
qpdf --encrypt user_pass owner_pass 256 --print=none --modify=none -- input.pdf encrypted.pdf
```

## Advanced Python

### pdfplumber - Precise Extraction

```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    page = pdf.pages[0]

    # Text with coordinates
    for char in page.chars[:10]:
        print(f"'{char['text']}' at ({char['x0']:.1f}, {char['y0']:.1f})")

    # Text by bounding box
    bbox_text = page.within_bbox((100, 100, 400, 200)).extract_text()

    # Custom table settings
    tables = page.extract_tables({
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3
    })
```

### reportlab - Professional Tables

```python
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

data = [['Product', 'Q1', 'Q2'], ['Widgets', '120', '135']]

table = Table(data)
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('GRID', (0, 0), (-1, -1), 1, colors.black)
]))
```

## Performance Tips

1. **Large PDFs:** Use streaming, process pages individually
2. **Text extraction:** pdftotext fastest for plain text
3. **Image extraction:** pdfimages faster than rendering
4. **Memory:** Process in chunks for large documents

## Troubleshooting

### Encrypted PDFs
```python
from pypdf import PdfReader
reader = PdfReader("encrypted.pdf")
if reader.is_encrypted:
    reader.decrypt("password")
```

### Corrupted PDFs
```bash
qpdf --check corrupted.pdf
qpdf --replace-input corrupted.pdf
```

### Scanned PDFs (no text)
Use OCR - see main SKILL.md for pytesseract example.

## License Summary

| Library | License |
|---------|---------|
| pypdf | BSD |
| pdfplumber | MIT |
| pypdfium2 | Apache/BSD |
| reportlab | BSD |
| poppler-utils | GPL-2 |
| qpdf | Apache |
| pdf-lib | MIT |
| pdfjs-dist | Apache |
