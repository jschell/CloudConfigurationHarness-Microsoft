# PDF Form Filling Guide

## Overview

Two workflows depending on whether the PDF has fillable form fields.

## Fillable Fields Workflow

For PDFs with interactive form fields:

### Step 1: Verify Fillable Fields
```bash
python scripts/check_fillable_fields.py document.pdf
```

### Step 2: Extract Field Info
```bash
python scripts/extract_form_field_info.py document.pdf > fields.json
```

Generates JSON mapping of all form fields with properties (type, page, bounding boxes).

### Step 3: Convert to Images
```bash
python scripts/convert_pdf_to_images.py document.pdf output_dir/
```

### Step 4: Create Field Values
Create `field_values.json` specifying values for each field:
```json
{
  "field_name": "value",
  "checkbox_field": true
}
```

### Step 5: Fill Fields
```bash
python scripts/fill_fillable_fields.py document.pdf field_values.json output.pdf
```

## Non-Fillable Fields Workflow

For image-based or non-interactive PDFs.

### Option A: Structure Extraction (Preferred)

```bash
python scripts/extract_form_structure.py document.pdf > structure.json
```

Identifies text labels, lines, checkboxes with coordinates.

Generate `fields.json` with calculated entry positions, then:
```bash
python scripts/fill_pdf_form_with_annotations.py document.pdf fields.json output.pdf
```

### Option B: Visual Estimation (Fallback)

1. Convert to images
2. Visually identify field locations
3. Use ImageMagick cropping for precise coordinates:
   ```bash
   convert page.png -crop 200x50+100+200 field_region.png
   ```
4. Populate `fields.json` with coordinates
5. Run fill script

### Hybrid Method

Combine structure extraction with visual estimation when needed.

## Validation

Always validate before finalizing:
```bash
python scripts/check_bounding_boxes.py document.pdf fields.json
python scripts/create_validation_image.py document.pdf fields.json validation.png
```

## Quick Reference

| PDF Type | Approach | Key Scripts |
|----------|----------|-------------|
| Fillable forms | Extract + fill | check_fillable_fields, fill_fillable_fields |
| Scanned/image | Structure + annotate | extract_form_structure, fill_pdf_form_with_annotations |
| Mixed | Hybrid | Combine approaches |
