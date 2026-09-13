# ai-artifacts-cleaner (aac)

A small Python console app that strips metadata and AI traces from images —
including the markers that ChatGPT/DALL·E, Midjourney, or Adobe Firefly
embed in generated/edited images (EXIF, XMP, ICC profile, and **C2PA/JUMBF**
provenance manifests).

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

Check what a file contains (no modification):

```bash
aac scan photo.jpg
aac scan ./photos -r
```

Clean a single file (creates `photo_clean.jpg` by default):

```bash
aac clean photo.jpg
```

Clean a whole directory recursively into a separate folder:

```bash
aac clean ./photos -r -o ./photos_clean
```

Overwrite originals (careful — no backup):

```bash
aac clean photo.jpg --in-place
```

Preview without writing files:

```bash
aac clean ./photos -r -o ./out --dry-run
```

### `clean` options

| Flag | Description |
|---|---|
| `-r`, `--recursive` | recurse into subdirectories |
| `-o`, `--output` | output directory (preserves subfolder structure) |
| `--in-place` | overwrite the original file |
| `--quality` | JPEG save quality (default 95) |
| `--keep-color-profile` | keep the ICC color profile (removed by default) |
| `--dry-run` | show what would happen without writing anything |

## Supported formats

JPEG, PNG, WEBP, TIFF, BMP.

## Limitations

- Animated/multi-frame files are skipped by default when cleaning — only
  static images are supported.
- `scan` detects C2PA/XMP by searching for characteristic byte signatures
  in the file rather than fully parsing the manifest structure — enough to
  detect them and to confirm they're gone after `clean`.
