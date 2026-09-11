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
4. **Video Generation Dispatch (Google Flow Wire Standards):**
   - **Tạo video với ảnh (1-3 Images):** Strictly use **R2V / Image-to-Video** via RPC **`MZZa6b`** (model: `veo_3_1_r2v_lite_low_priority`, duration: 8s fixed). Pass `reference_media_ids` or `start_image_media_id`. **Never use Frame-to-Frame (`nprQif`) or single-frame structures for 1 image.**
   - **Tạo video từ Frame to Frame (Bắt buộc đủ 2 Images):** Use **F2F** interpolation via RPC **`nprQif`** (model: `veo_3_1_i2v_s_lite_6s_fl_low_priority` for 6s, or `veo_3_1_interpolation_lite_low_priority` for 8s). Both `start_image_media_id` AND `end_image_media_id` are required.

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

1. **Default Mode (Lossless Reverse Alpha Blending + Adaptive Grain, 6ms):**
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output/sample.jpeg"
```

2. **AI Inpainting Mode (LaMa Deep Learning on GPU/CPU):**
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output/sample.jpeg" -e lama
```

3. **Clean single image with custom output:**
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output/sample.jpeg" -o "agent-veo3/output/sample_clean.jpeg"
```

4. **Batch clean all images in folder:**
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output"
```

---

## LaMa AI Model Setup (Optional for `-e lama`)

The default **Reverse Alpha** engine requires no model downloads and is 100% operational immediately.

To enable the deep learning LaMa inpainting engine (`-e lama`):
1. **Download Model File (~198MB):**
   - **HuggingFace:** [lama_fp32.onnx (208 MB)](https://huggingface.co/Carve/LaMa-ONNX/resolve/main/lama_fp32.onnx?download=true)
   - **GitHub Releases:** [big-lama.onnx (208 MB)](https://github.com/xulihang/ImageTrans_plugins/releases/download/plugins/big-lama.onnx)
2. **Place in assets directory:**
   ```
   agent-veo3/assets/models/lama_fp32.onnx
   ```
   *(Accepts either `lama_fp32.onnx` or `big-lama.onnx`)*.
3. **Hardware Acceleration:** Auto-selects NVIDIA CUDA GPU, DirectX 12 GPU (DirectML), or CPU.
