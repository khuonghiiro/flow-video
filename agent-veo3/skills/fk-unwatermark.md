# /fk-unwatermark — Remove Visible Gemini/Imagen Watermarks

Remove the semi-transparent 4-pointed sparkle watermark from Gemini/Imagen generated images using the lossless Reverse Alpha Blending mathematical engine.

Usage: `/fk-unwatermark <image_or_dir_path> [--output <output_path>] [--alpha 0.28] [--lama]`

- `image_or_dir_path` — path to single image or directory containing images
- `--output` / `-o` — optional target output file or directory
- `--alpha` / `-a` — watermark opacity (default: `0.28`, tuned for Gemini / Imagen 3)
- `--lama` / `-m lama` — use LaMa AI inpainting engine (flawless reconstruction on challenging backgrounds)

---

## Code Architecture & Test Separation

```
agent-veo3/
├── assets/watermarks/                  # Calibrated alpha masks (bg_48.png, bg_96.png)
├── output/
│   ├── watermarks/                     # [I/O] Raw downloaded images with watermarks from Google Flow
│   └── cleaned/                        # [I/O] Restored clean images with 100% pixel fidelity
├── scripts/
│   ├── remove_gemini_watermark.py      # [PRODUCTION] Core processing logic (Committed to Git)
│   └── tests/                          # [TESTING] Test scripts (IGNORED by .gitignore, NEVER pushed to Git)
│       └── test_full_pipeline_clean_flow.py
└── skills/
    └── fk-unwatermark.md               # English skill reference
```

### Folder Conventions & Flow Upload Rules
1. **Raw Downloads:** Always save downloaded images containing watermarks into `agent-veo3/output/watermarks/`.
2. **Cleaned Output:** Always output unwatermarked images to `agent-veo3/output/cleaned/`.
3. **Flow Upload:** AI scans `agent-veo3/output/cleaned/` and tracks uploaded UUIDs to **never upload duplicate images**.
4. **Video Generation Dispatch:**
   - **Single Frame (1 Image):** Strictly use **I2V (Image-to-Video)** via RPC `eb1hJf` (only pass `start_image_media_id`). **Never use Frame-to-Frame (`nprQif`) for single-frame generation.**
   - **Start & End Frame (2 Images):** Use **F2F** interpolation via RPC `nprQif`.
   - **Reference Images (1-3 Images):** Use **R2V** via RPC `MZZa6b`.

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
