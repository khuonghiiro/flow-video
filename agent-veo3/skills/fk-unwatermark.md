# /fk-unwatermark — Remove Visible Gemini/Imagen Watermarks

Remove the semi-transparent 4-pointed sparkle watermark from Gemini/Imagen generated images using the lossless Reverse Alpha Blending mathematical engine.

Usage: `/fk-unwatermark <image_or_dir_path> [--output <output_path>] [--alpha 0.28]`

- `image_or_dir_path` — path to single image or directory containing images
- `--output` / `-o` — optional target output file or directory
- `--alpha` / `-a` — watermark opacity (default: `0.28`, tuned for Gemini / Imagen 3)

---

## Code Architecture & Test Separation

```
agent-veo3/
├── assets/watermarks/                  # Calibrated alpha masks (bg_48.png, bg_96.png)
├── scripts/
│   ├── remove_gemini_watermark.py      # [PRODUCTION] Core processing logic (Committed to Git)
│   └── tests/                          # [TESTING] Test scripts (IGNORED by .gitignore, NEVER pushed to Git)
│       └── test_e2e_generate_and_unwatermark.py
└── skills/
    └── fk-unwatermark.md               # English skill reference
```

- **Production Logic (`agent-veo3/scripts/`):** Contains `remove_gemini_watermark.py` used in production pipelines and tracked by Git.
- **Testing Scripts (`agent-veo3/scripts/tests/`):** Contains test, verification, and benchmark scripts. This folder is added to `agent-veo3/.gitignore` and is **never pushed to Git**.

---

## When to Use

- After generating character reference images or scene images from Google Flow / Imagen.
- Before passing images to Veo2 / Veo3 video generation pipelines (`fk-gen-videos`, `fk-gen-chain-videos`).
- Preparing pristine assets for YouTube thumbnails (`fk-thumbnail`).

---

## Execution Command

Run from the workspace root directory:

```bash
# Windows PowerShell
& "agent-veo3/.venv/Scripts/python.exe" agent-veo3/scripts/remove_gemini_watermark.py "<PATH>"

# Linux / macOS / Standard Python
python agent-veo3/scripts/remove_gemini_watermark.py "<PATH>"
```

### Examples

1. **Clean single image:**
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output/sample.jpeg"
```

2. **Clean single image with custom output:**
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output/sample.jpeg" -o "agent-veo3/output/sample_clean.jpeg"
```

3. **Batch clean all images in folder:**
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output"
```

4. **Run test verification script:**
```bash
python agent-veo3/scripts/tests/test_e2e_generate_and_unwatermark.py
```

---

## How It Works

1. **Auto-Detection:** Automatically scans the bottom-right region using template cross-correlation with calibrated `bg_48.png` / `bg_96.png` assets located in `agent-veo3/assets/watermarks/`.
2. **Reverse Alpha Blending:** Reconstructs the exact background pixel value $B = \frac{I - \alpha \cdot 255}{1 - \alpha}$.
3. **100% Detail Preservation:** Zero blur or AI approximation. Every underlying pixel, micro-grain, and sharp edge remains intact.
4. **Ultra-Fast Speed:** ~6.6ms algorithm time per image (> 150 FPS), ~35ms including disk I/O.
