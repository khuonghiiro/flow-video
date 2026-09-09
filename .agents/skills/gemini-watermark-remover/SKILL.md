---
name: gemini-watermark-remover
description: Mathematically removes visible Gemini/Imagen sparkle watermarks (48px/96px) from AI-generated images using Reverse Alpha Blending while preserving 100% pixel sharpness, micro-textures, and high-frequency details.
---

# Gemini / Imagen Watermark Remover

Use this skill when you need to remove the visible watermark (semi-transparent 4-pointed sparkle icon) placed by Google Gemini, Google Imagen, or Google Flow on generated images without losing any background pixel sharpness.

## 1. Code Architecture & Test Separation

- **Production Logic:** `agent-veo3/scripts/remove_gemini_watermark.py` (Committed to Git, used in production pipelines).
- **Test Scripts:** `agent-veo3/scripts/tests/` (Added to `agent-veo3/.gitignore`, NEVER pushed to Git. Contains automated test pipelines like `test_e2e_generate_and_unwatermark.py`).

```
agent-veo3/
├── assets/watermarks/                  # Reference masks (bg_48.png, bg_96.png)
├── scripts/
│   ├── remove_gemini_watermark.py      # [PRODUCTION] Main processing logic (Committed to Git)
│   └── tests/                          # [TESTING] Ignored by git (.gitignore)
│       └── test_e2e_generate_and_unwatermark.py
└── skills_vi/
    └── fk-unwatermark.md               # Vietnamese skill guide
```

## 2. Core Mathematical Principle

Unlike AI inpainting or blur filters that erase underlying pixels and guess smooth approximations, Gemini applies its watermark via standard alpha blending:

$$I = (1 - \alpha) \cdot B + \alpha \cdot W$$

Where:
- $I$: The watermarked image pixel.
- $B$: The original background pixel to recover.
- $W$: The watermark color ($255$ pure white).
- $\alpha$: The pre-calibrated continuous alpha transparency map ($\approx 0.28$).

The original background is restored with **zero loss of sharpness, micro-ripples, or grain**:

$$B = \text{clip}\left(\frac{I - \alpha \cdot 255}{1 - \alpha}, 0, 255\right)$$

## 3. Watermark Assets & Geometry

Reference alpha masks are stored in:
`agent-veo3/assets/watermarks/`
- `bg_48.png`: For standard resolutions (< 2048px, e.g. 1376x768, 1024x1024).
- `bg_96.png`: For high resolutions ($\ge$ 2048px, 2K/4K).

The detection engine automatically scans the bottom-right $250 \times 250$ region using template cross-correlation, allowing sub-pixel precision across any aspect ratio (landscape, portrait, square).

## 4. CLI Usage

The primary script is located at:
`agent-veo3/scripts/remove_gemini_watermark.py`

Run from the repository root:

### Process a Single Image:
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output/image.jpeg"
```

### Process with Custom Output Path:
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output/image.jpeg" -o "agent-veo3/output/clean.jpeg"
```

### Batch Process an Entire Directory:
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output"
```

### Run Test Verification:
```bash
python agent-veo3/scripts/tests/test_e2e_generate_and_unwatermark.py
```

## 5. Python API Integration

To call the engine directly inside Python pipelines:

```python
import sys
from pathlib import Path
import cv2

# Add scripts directory to sys.path relative to workspace root
sys.path.append(str(Path("agent-veo3/scripts").resolve()))
from remove_gemini_watermark import remove_watermark

# Load image
img = cv2.imread("agent-veo3/output/input_with_logo.jpeg")

# Remove watermark (returns uint8 numpy array)
cleaned = remove_watermark(img, alpha_peak=0.28)

# Save cleaned image
cv2.imwrite("agent-veo3/output/output_cleaned.jpeg", cleaned, [int(cv2.IMWRITE_JPEG_QUALITY), 98])
```

## 6. Performance Metrics

- **Algorithm execution (in-memory):** $\approx 6.6\text{ ms}$ per image ($> 150\text{ FPS}$).
- **End-to-end with disk I/O:** $\approx 35\text{ ms}$ per image ($\approx 30\text{ images/second}$).
- **Hardware requirement:** Runs directly on CPU with NumPy/OpenCV; zero GPU or heavy deep-learning dependencies required.
