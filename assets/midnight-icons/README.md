# Midnight neon icons

These 21 RGBA PNGs are extracted from the approved, unmodified
`design-reference/icons-midnight.png` (1536 × 1024 RGB).

`manifest.json` records exact weather keys, source crop rectangles, PNG sizes
and six transparent padding pixels. Order and names match `WeatherCore.catalog`.
Meteor Shower and Aurora retain three distinct variants each.

Extraction: crop the original pixels, estimate the dark catalog background from
the blank side margins, unmatte it into alpha, remove disconnected frame residue,
then add transparent padding. No new icon design, redraw, sharpening or upscaling
is used. The originals' internal neon colors and glow are the visual reference.
RGB unmatting is an estimate because the sheet is flattened, not a layered asset.

Native artwork regions are 140–186 pixels wide and 96–121 pixels high (before
padding). These are dashboard-sized exports; they are not high-resolution masters.
For substantially larger use, request the original individual transparent files.

Reproduce from the repository root:

```text
python tests/extract_midnight_icons.py
node tests/midnight-icons.test.cjs
python tests/test_midnight_assets.py
```

The extraction script also saves a native-size QA contact sheet to the OS temp
directory. The website uses the individual PNGs, never the contact sheet.
