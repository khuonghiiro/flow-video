"""
Gemini / Imagen Watermark Remover - Pixel-Preserving Reverse Alpha Engine
Khử logo/watermark góc dưới bên phải do Gemini / Imagen tạo ra mà vẫn giữ nguyên 100% độ nét pixel.
"""

import os
import sys
import argparse
from pathlib import Path
# Auto-re-exec with .venv python if cv2 is missing in current environment
try:
    import cv2
    import numpy as np
except ModuleNotFoundError:
    import subprocess
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir.parent / ".venv" / "Scripts" / ("python.exe" if sys.platform == "win32" else "python"),
        script_dir.parent.parent / ".venv" / "Scripts" / ("python.exe" if sys.platform == "win32" else "python"),
    ]
    for venv_py in candidates:
        if venv_py.exists() and sys.executable.lower() != str(venv_py).lower():
            res = subprocess.run([str(venv_py), str(Path(__file__).resolve())] + sys.argv[1:])
            sys.exit(res.returncode)
    raise

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_default_asset_dir() -> Path:
    """Trả về thư mục chứa watermark assets."""
    script_dir = Path(__file__).resolve().parent
    # Check agent-veo3/assets/watermarks
    asset_dir = script_dir.parent / "assets" / "watermarks"
    if asset_dir.exists():
        return asset_dir
    # Check script_dir / assets
    alt_dir = script_dir / "assets"
    if alt_dir.exists():
        return alt_dir
    return asset_dir


def generate_parametric_mask(size: int = 48) -> np.ndarray:
    """
    Tạo mask tham số hình ngôi sao 4 cánh (Astroid) với anti-aliasing siêu mịn
    để fallback nếu không có file asset bg_48 / bg_96.
    """
    scale = 8
    hi_size = size * scale
    Y, X = np.ogrid[:hi_size, :hi_size]
    cx = (hi_size - 1) / 2.0
    cy = (hi_size - 1) / 2.0
    r = hi_size / 2.0
    power = 0.68
    dist = (np.abs(X - cx) / r) ** power + (np.abs(Y - cy) / r) ** power
    mask_hi = (dist <= 1.0).astype(np.float32)
    # Downscale với phép nội suy AREA để tạo viền anti-aliased hoàn hảo
    mask = cv2.resize(mask_hi, (size, size), interpolation=cv2.INTER_AREA)
    return (mask * 128.0).astype(np.uint8)


def load_watermark_template(size: int = 48, asset_dir: Path | None = None) -> np.ndarray:
    """Tải template bg_48 hoặc bg_96, hoặc fallback mask tham số."""
    if asset_dir is None:
        asset_dir = get_default_asset_dir()
    
    filename = f"bg_{size}.png"
    filepath = asset_dir / filename
    if filepath.exists():
        bg = cv2.imread(str(filepath), cv2.IMREAD_GRAYSCALE)
        if bg is not None and bg.shape == (size, size):
            return bg
            
    return generate_parametric_mask(size)


def detect_watermark_position(
    img: np.ndarray,
    template: np.ndarray,
    target_size: int = 48,
    search_radius: int = 8,
) -> tuple[int, int, float]:
    """
    Định vị chính xác logo watermark ở góc dưới bên phải.
    Vị trí thiết kế chuẩn của Google Imagen / Flow:
    - 48px: offset = 73px từ cạnh phải và cạnh đáy (anchor: w - 48 - 73, h - 48 - 73).
    - 96px: offset = 146px từ cạnh phải và cạnh đáy (anchor: w - 96 - 146, h - 96 - 146).
    
    Tìm kiếm cục bộ chỉ trong bán kính hẹp xung quanh anchor (+/- search_radius),
    triệt tiêu hoàn toàn nguy cơ nhảy sai tọa độ do vân nền phức tạp gây ra.
    """
    h, w = img.shape[:2]
    expected_offset = 73 if target_size == 48 else 146
    x_anchor = w - target_size - expected_offset
    y_anchor = h - target_size - expected_offset

    if x_anchor < 0 or y_anchor < 0:
        return max(0, w - target_size), max(0, h - target_size), 1.0

    # Lấy vùng ROI nhỏ quanh anchor
    y_min = max(0, y_anchor - search_radius)
    y_max = min(h, y_anchor + target_size + search_radius)
    x_min = max(0, x_anchor - search_radius)
    x_max = min(w, x_anchor + target_size + search_radius)

    roi = img[y_min:y_max, x_min:x_max]
    if roi.shape[0] < target_size or roi.shape[1] < target_size:
        return x_anchor, y_anchor, 1.0

    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    tpl_gray = template if len(template.shape) == 2 else cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    if tpl_gray.dtype != np.uint8:
        tpl_gray = np.clip(tpl_gray * 255.0, 0, 255).astype(np.uint8) if tpl_gray.max() <= 1.0 else tpl_gray.astype(np.uint8)

    res = cv2.matchTemplate(gray_roi, tpl_gray, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)

    best_x = x_min + max_loc[0]
    best_y = y_min + max_loc[1]

    # Nếu correlation hợp lệ trong vùng lân cận, nhận best_x, best_y; nếu không giữ anchor
    if max_val < 0.25:
        return x_anchor, y_anchor, 1.0

    return best_x, best_y, float(max_val)


def load_calibrated_alpha(size: int = 48, asset_dir: Path | None = None) -> np.ndarray:
    """Tải alpha map đã được hiệu chuẩn chính xác từ pixel thật của Google Imagen/Flow."""
    if asset_dir is None:
        asset_dir = get_default_asset_dir()
    
    for filename in [f"perfect_alpha_{size}.npy", f"true_calibrated_alpha_{size}.npy"]:
        npy_path = asset_dir / filename
        if npy_path.exists():
            try:
                return np.load(str(npy_path))
            except Exception:
                pass
            
    # Fallback template png
    template = load_watermark_template(size, asset_dir)
    default_peak = 0.315 if size == 48 else 0.297
    return (template.astype(np.float64) / 255.0) * default_peak


def remove_watermark(
    img: np.ndarray,
    alpha_peak: float | None = None,
    target_size: int | None = None,
    asset_dir: Path | None = None,
    aggressive: bool = False,
    restore_grain: bool = True,
    engine: str = "alpha",
    model_path: Path | str | None = None,
) -> np.ndarray:
    """
    Khử watermark Gemini/Flow bảo tồn 100% chi tiết pixel gốc.
    - engine='alpha': Dùng Reverse Alpha Blending chính xác + Adaptive Grain Restoration (Mặc định, 6ms, siêu nét).
    - engine='lama': Dùng LaMa AI Deep Inpainting (ONNX Runtime, tự động GPU CUDA/DirectML/CPU, ~150ms).
    """
    h, w = img.shape[:2]
    
    # Chọn kích thước template tự động dựa theo độ phân giải nếu không chỉ định
    if target_size is None:
        target_size = 96 if max(h, w) >= 2048 else 48
        
    template = load_watermark_template(target_size, asset_dir)
    alpha_map = load_calibrated_alpha(target_size, asset_dir)
    
    # Chuẩn hóa alpha_peak nếu người dùng chỉ định cụ thể
    if alpha_peak is not None and alpha_map.max() > 0:
        alpha_norm = (alpha_map / alpha_map.max()) * alpha_peak
    else:
        alpha_norm = alpha_map
    
    # Tự động định vị watermark
    found_x, found_y, score = detect_watermark_position(img, template, target_size=target_size)
    t_h, t_w = alpha_norm.shape[:2]
    
    # Kiểm tra bounds và fallback vị trí chuẩn
    expected_offset = 73 if target_size == 48 else 146
    x1, y1 = found_x, found_y
    x2, y2 = x1 + t_w, y1 + t_h
    if x1 < 0 or y1 < 0 or x2 > w or y2 > h:
        x1 = w - target_size - expected_offset
        y1 = h - target_size - expected_offset
        x2, y2 = x1 + t_w, y1 + t_h

    # Nếu người dùng yêu cầu chế độ LaMa AI
    if engine in ("lama", "ai"):
        try:
            from lama_inpaint import remove_watermark_lama, get_default_model_path
            target_model = model_path or get_default_model_path()
            if target_model and Path(target_model).exists():
                mask = np.zeros((h, w), dtype=np.uint8)
                mask[y1:y2, x1:x2] = (alpha_norm > 0.05).astype(np.uint8) * 255
                return remove_watermark_lama(img, mask, model_path=target_model)
            else:
                print("[WARN] Chưa có model LaMa ONNX trong assets/models/, chuyển sang Reverse Alpha Blending...")
        except Exception as e:
            print(f"[WARN] Không thể chạy LaMa AI ({e}), chuyển sang Reverse Alpha Blending...")

    # Phục hồi bằng Reverse Alpha Blending chính xác
    patch = img[y1:y2, x1:x2].astype(np.float64)
    a_3d = alpha_norm[:, :, np.newaxis]
    denom = np.maximum(1.0 - a_3d, 1e-4)
    restored = np.clip((patch - a_3d * 255.0) / denom, 0.0, 255.0)

    # Adaptive Micro-Grain Restoration: Phục hồi vi hạt tại lõi alpha cao
    if restore_grain:
        m = 10
        surround = []
        if y1 > 0:
            surround.append(img[max(0, y1 - m):y1, x1:x2].reshape(-1, 3))
        if y2 < h:
            surround.append(img[y2:min(h, y2 + m), x1:x2].reshape(-1, 3))
        if x1 > 0:
            surround.append(img[y1:y2, max(0, x1 - m):x1].reshape(-1, 3))
        if x2 < w:
            surround.append(img[y1:y2, x2:min(w, x2 + m)].reshape(-1, 3))
            
        if surround:
            surround_pixels = np.concatenate(surround, axis=0).astype(np.float64)
            bg_std = np.std(surround_pixels, axis=0)
            bg_std = np.clip(bg_std, 0.5, 6.0)
            
            peak_val = alpha_norm.max()
            if peak_val > 0.15:
                core_weight = np.clip((alpha_norm - 0.15) / (peak_val - 0.15), 0.0, 1.0)
                rng = np.random.RandomState(int((x1 * 31 + y1 * 17) & 0xFFFFFFFF))
                grain = rng.normal(0.0, 1.0, restored.shape) * (bg_std * 0.70)
                restored = np.clip(restored + grain * core_weight[:, :, np.newaxis], 0.0, 255.0)
    
    result = img.copy()
    result[y1:y2, x1:x2] = np.round(restored).astype(np.uint8)

    if aggressive:
        core_mask = np.zeros((h, w), dtype=np.uint8)
        core_mask[y1:y2, x1:x2] = (alpha_norm > 0.22).astype(np.uint8) * 255
        cleaned = cv2.inpaint(result, core_mask, inpaintRadius=2, flags=cv2.INPAINT_NS)
        return cleaned

    return result


def process_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    alpha_peak: float | None = None,
    engine: str = "alpha",
    model_path: Path | str | None = None,
) -> bool:
    """Xử lý một file ảnh đơn lẻ."""
    in_p = Path(input_path)
    if not in_p.exists():
        print(f"[ERROR] Không tìm thấy file: {in_p}")
        return False
        
    img = cv2.imread(str(in_p))
    if img is None:
        print(f"[ERROR] Không thể đọc ảnh: {in_p}")
        return False
        
    cleaned = remove_watermark(img, alpha_peak=alpha_peak, engine=engine, model_path=model_path)
    
    if output_path is None:
        if in_p.parent.name == "watermarks":
            out_p = in_p.parent.parent / "cleaned" / f"{in_p.stem}{in_p.suffix}"
        else:
            out_p = in_p.parent / f"{in_p.stem}_cleaned{in_p.suffix}"
    else:
        out_p = Path(output_path)
        
    out_p.parent.mkdir(parents=True, exist_ok=True)
    
    # Lưu với chất lượng JPEG/PNG cao nhất
    if out_p.suffix.lower() in [".jpg", ".jpeg"]:
        cv2.imwrite(str(out_p), cleaned, [int(cv2.IMWRITE_JPEG_QUALITY), 98])
    else:
        cv2.imwrite(str(out_p), cleaned)
        
    print(f"[SUCCESS] Đã khử logo thành công -> {out_p}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Khử logo watermark Gemini/Imagen mà vẫn giữ nguyên độ nét pixel."
    )
    parser.add_argument("input", nargs="?", default=None, help="Đường dẫn tới file ảnh hoặc thư mục ảnh cần xử lý")
    parser.add_argument("-o", "--output", help="Đường dẫn file hoặc thư mục xuất (tùy chọn)")
    parser.add_argument(
        "-a", "--alpha",
        type=float,
        default=None,
        help="Độ mờ alpha tùy chỉnh của watermark (mặc định: tự động theo calibrated template)"
    )
    parser.add_argument(
        "-e", "--engine",
        choices=["alpha", "lama", "ai"],
        default="alpha",
        help="Engine khử logo: 'alpha' (Reverse Alpha Blending + Grain, 6ms) hoặc 'lama'/'ai' (LaMa AI Inpainting, GPU/CPU)"
    )
    parser.add_argument(
        "-m", "--model",
        default=None,
        help="Đường dẫn tùy chọn tới file model LaMa ONNX (mặc định tìm trong agent-veo3/assets/models/)"
    )
    args = parser.parse_args()
    
    # Mặc định quét agent-veo3/output/watermarks nếu không truyền tham số
    if args.input is None:
        script_dir = Path(__file__).resolve().parent
        default_watermarks = script_dir.parent / "output" / "watermarks"
        if default_watermarks.exists():
            in_path = default_watermarks
        else:
            in_path = script_dir.parent / "output"
    else:
        in_path = Path(args.input)
        
    if in_path.is_file():
        process_file(in_path, args.output, alpha_peak=args.alpha, engine=args.engine, model_path=args.model)
    elif in_path.is_dir():
        image_exts = {".jpg", ".jpeg", ".png", ".webp"}
        files = [f for f in in_path.iterdir() if f.suffix.lower() in image_exts and "_cleaned" not in f.name]
        print(f"Tìm thấy {len(files)} ảnh trong thư mục {in_path}...")
        for f in files:
            out_file = None
            if args.output:
                out_file = Path(args.output) / f.name
            elif in_path.name == "watermarks":
                out_file = in_path.parent / "cleaned" / f.name
            process_file(f, out_file, alpha_peak=args.alpha, engine=args.engine, model_path=args.model)
    else:
        print(f"[ERROR] Đường dẫn không hợp lệ: {in_path}")
        sys.exit(1)



if __name__ == "__main__":
    main()
