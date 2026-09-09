# fk-unwatermark — Remove Visible Gemini/Imagen Watermarks

Remove the semi-transparent 4-pointed sparkle watermark from Gemini/Imagen generated images using the lossless Reverse Alpha Blending mathematical engine.

Usage: `/fk-unwatermark <image_or_dir_path> [--output <output_path>] [--alpha 0.28]`

- `image_or_dir_path` — path to single image or directory containing images
- `--output` / `-o` — optional target output file or directory
- `--alpha` / `-a` — watermark opacity (default: `0.28`, tuned for Gemini / Imagen 3)

## When to Use

- After generating character reference images or scene images from Google Flow / Imagen.
- Before passing images to Veo2 / Veo3 video generation pipelines (`fk-gen-videos`, `fk-gen-chain-videos`).
- Preparing pristine assets for YouTube thumbnails (`fk-thumbnail`).

## Execution Command

Run through Agent Veo3 virtual environment:

```bash
& "d:\_DuAn\App_Desktop\workflows\flow-video\agent-veo3\.venv\Scripts\python.exe" "d:\_DuAn\App_Desktop\workflows\flow-video\agent-veo3\scripts\remove_gemini_watermark.py" "<PATH>"
```

### Examples

1. **Clean single image:**
```bash
& "d:\_DuAn\App_Desktop\workflows\flow-video\agent-veo3\.venv\Scripts\python.exe" "d:\_DuAn\App_Desktop\workflows\flow-video\agent-veo3\scripts\remove_gemini_watermark.py" "d:\_DuAn\App_Desktop\workflows\flow-video\agent-veo3\output\sample.jpeg"
```

2. **Batch clean all images in folder:**
```bash
& "d:\_DuAn\App_Desktop\workflows\flow-video\agent-veo3\.venv\Scripts\python.exe" "d:\_DuAn\App_Desktop\workflows\flow-video\agent-veo3\scripts\remove_gemini_watermark.py" "d:\_DuAn\App_Desktop\workflows\flow-video\agent-veo3\output"
```

## How It Works

1. **Auto-Detection:** Automatically scans the bottom-right region using template cross-correlation with calibrated `bg_48.png` / `bg_96.png` assets.
2. **Reverse Alpha Blending:** Reconstructs the exact background pixel value $B = \frac{I - \alpha \cdot 255}{1 - \alpha}$.
3. **100% Detail Preservation:** Zero blur or AI approximation. Every underlying pixel, micro-grain, and sharp edge remains intact.
4. **Speed:** ~6.6ms algorithm time per image (> 150 FPS).
