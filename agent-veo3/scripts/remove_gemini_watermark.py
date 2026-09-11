"""
Gemini / Imagen Watermark Remover - Pixel-Preserving Reverse Alpha Engine
Khử logo/watermark góc dưới bên phải do Gemini / Imagen tạo ra mà vẫn giữ nguyên 100% độ nét pixel.
"""

import os
import sys
import argparse
from pathlib import Path
import cv2
import numpy as np

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
    search_margin: int = 250
) -> tuple[int, int, float]:
    """
    Tự động dò tìm tọa độ (x, y) của logo ở góc dưới bên phải bằng cross-correlation chuẩn hóa.
    Trả về: (best_x, best_y, confidence)
    """
    h, w = img.shape[:2]
    t_h, t_w = template.shape[:2]
    
    y0 = max(0, h - search_margin)
    x0 = max(0, w - search_margin)
    search_roi = img[y0:h, x0:w]
    
    gray_roi = cv2.cvtColor(search_roi, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(gray_roi, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    
    found_x = x0 + max_loc[0]
    found_y = y0 + max_loc[1]
    
    return found_x, found_y, float(max_val)


def load_calibrated_alpha(size: int = 48, asset_dir: Path | None = None) -> np.ndarray:
    """Tải alpha map đã được hiệu chuẩn chính xác từ pixel thật của Google Imagen/Flow."""
    if asset_dir is None:
        asset_dir = get_default_asset_dir()
    
    npy_path = asset_dir / f"perfect_alpha_{size}.npy"
    if npy_path.exists():
        try:
            return np.load(str(npy_path))
        except Exception:
            pass
            
    # Fallback template png
    template = load_watermark_template(size, asset_dir)
    return (template.astype(np.float64) / 255.0) * 0.314


def remove_watermark(
    img: np.ndarray,
    alpha_peak: float = 0.295,
    target_size: int | None = None,
    asset_dir: Path | None = None,
    aggressive: bool = False,
    method: str = "rab",
) -> np.ndarray:
    """
    Khử watermark Gemini/Flow bảo tồn 100% chi tiết pixel gốc.
    - method="rab": Thuật toán Reverse Alpha Blending chuẩn xác:
      B = clip((I - alpha * 255) / (1 - alpha), 0, 255)
    - method="lama": Mạng nơ-ron LaMa Fourier Inpainting khử sạch 100% không để lại viền mờ.
    - aggressive=True: Khử nhiễu lượng tử hóa Navier-Stokes nhẹ tại tâm lõi.
    """
    h, w = img.shape[:2]
    
    # Chọn kích thước template tự động dựa theo độ phân giải nếu không chỉ định
    if target_size is None:
        target_size = 96 if max(h, w) >= 2048 else 48
        
    template = load_watermark_template(target_size, asset_dir)
    
    # Tự động định vị watermark
    found_x, found_y, score = detect_watermark_position(img, template)
    
    # Kiểm tra bounds và fallback vị trí chuẩn (~73px từ góc phải dưới)
    x1, y1 = found_x, found_y
    if x1 < 0 or y1 < 0 or x1 + target_size > w or y1 + target_size > h or score < 0.35:
        x1 = w - target_size - 73
        y1 = h - target_size - 73

    # Chế độ AI LaMa Inpainting
    if method.lower() == "lama":
        try:
            from lama_inpaint import get_lama_inpainter
            inpainter = get_lama_inpainter()
            return inpainter.remove_watermark(img, x1, y1, size=target_size, tpl=template)
        except Exception as e:
            print(f"[WARN] LaMa inpainting thất bại ({e}), fallback về Reverse Alpha Blending.")

    # Chế độ Reverse Alpha Blending toán học
    alpha_map = load_calibrated_alpha(target_size, asset_dir)
    if alpha_map.max() > 0:
        alpha_norm = (alpha_map / alpha_map.max()) * alpha_peak
    else:
        alpha_norm = alpha_map
    
    t_h, t_w = alpha_norm.shape[:2]
    x2, y2 = x1 + t_w, y1 + t_h

    patch = img[y1:y2, x1:x2].astype(np.float64)
    a_3d = alpha_norm[:, :, np.newaxis]
    denom = np.maximum(1.0 - a_3d, 1e-4)
    restored = np.clip(np.round((patch - a_3d * 255.0) / denom), 0.0, 255.0).astype(np.uint8)
    
    result = img.copy()
    result[y1:y2, x1:x2] = restored

    if aggressive:
        core_mask = np.zeros((h, w), dtype=np.uint8)
        core_mask[y1:y2, x1:x2] = (alpha_norm > 0.22).astype(np.uint8) * 255
        cleaned = cv2.inpaint(result, core_mask, inpaintRadius=2, flags=cv2.INPAINT_NS)
        return cleaned

    return result


def process_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    alpha_peak: float = 0.28,
    method: str = "rab"
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
        
    cleaned = remove_watermark(img, alpha_peak=alpha_peak, method=method)
    
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
        
    print(f"[SUCCESS] Đã khử logo thành công ({method.upper()}) -> {out_p}")
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
        default=0.28,
        help="Độ mờ alpha của watermark (mặc định: 0.28)"
    )
    parser.add_argument(
        "-m", "--method",
        choices=["rab", "lama"],
        default="rab",
        help="Phương pháp khử watermark: 'rab' (Reverse Alpha Blending, siêu tốc) hoặc 'lama' (AI Inpainting, chất lượng hoàn hảo)"
    )
    parser.add_argument(
        "--lama",
        action="store_true",
        help="Sử dụng model AI LaMa để khử logo (viết tắt cho --method lama)"
    )
    args = parser.parse_args()
    
    chosen_method = "lama" if args.lama else args.method
    
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
        process_file(in_path, args.output, alpha_peak=args.alpha, method=chosen_method)
    elif in_path.is_dir():
        image_exts = {".jpg", ".jpeg", ".png", ".webp"}
        files = [f for f in in_path.iterdir() if f.suffix.lower() in image_exts and "_cleaned" not in f.name]
        print(f"Tìm thấy {len(files)} ảnh trong thư mục {in_path} (Phương pháp: {chosen_method.upper()})...")
        for f in files:
            out_file = None
            if args.output:
                out_file = Path(args.output) / f.name
            elif in_path.name == "watermarks":
                out_file = in_path.parent / "cleaned" / f.name
            process_file(f, out_file, alpha_peak=args.alpha, method=chosen_method)
    else:
        print(f"[ERROR] Đường dẫn không hợp lệ: {in_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
