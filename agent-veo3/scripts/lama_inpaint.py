"""
LaMa (Large Mask Inpainting) Engine via ONNX Runtime
Hỗ trợ tăng tốc phần cứng tự động: NVIDIA CUDA GPU -> DirectX 12 GPU (DirectML) -> CPU.
"""

import sys
from pathlib import Path
import cv2
import numpy as np

# Cache session to avoid reloading model on every image in batch processing
_SESSION_CACHE = {}


def get_default_model_path() -> Path | None:
    """Tìm file model lama ONNX trong thư mục assets."""
    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir.parent / "assets" / "models" / "lama_fp32.onnx",
        script_dir.parent / "assets" / "models" / "big-lama.onnx",
        script_dir.parent / "assets" / "models" / "lama.onnx",
    ]
    for c in candidates:
        if c.exists() and c.stat().st_size > 10 * 1024 * 1024:
            return c
    return None


def get_lama_session(model_path: Path | str | None = None):
    """
    Khởi tạo ONNX Runtime session với cơ chế ưu tiên phần cứng:
    1. CUDAExecutionProvider (NVIDIA GPU - CUDA)
    2. DmlExecutionProvider (Mọi GPU DirectX 12: Intel Iris/HD, AMD Radeon, NVIDIA)
    3. CPUExecutionProvider (CPU thuần - fallback)
    """
    import onnxruntime as ort

    if model_path is None:
        model_path = get_default_model_path()
    if model_path is None:
        raise FileNotFoundError(
            "Không tìm thấy file model LaMa ONNX (lama_fp32.onnx / big-lama.onnx).\n"
            "Vui lòng tải model và đặt vào thư mục: agent-veo3/assets/models/"
        )

    model_path = Path(model_path).resolve()
    model_key = str(model_path)
    if model_key in _SESSION_CACHE:
        return _SESSION_CACHE[model_key]

    available_providers = ort.get_available_providers()
    priority = ["CUDAExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider"]
    providers = [p for p in priority if p in available_providers]

    opts = ort.SessionOptions()
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    opts.intra_op_num_threads = 4

    session = ort.InferenceSession(str(model_path), sess_options=opts, providers=providers)
    active_provider = session.get_providers()[0] if session.get_providers() else "Unknown"
    print(f"[AI-ENGINE] LaMa Model loaded from {model_path.name} | Hardware: {active_provider}")

    _SESSION_CACHE[model_key] = (session, active_provider)
    return _SESSION_CACHE[model_key]


def inpaint_patch(
    roi_bgr: np.ndarray,
    roi_mask: np.ndarray,
    session,
    target_size: int = 512
) -> np.ndarray:
    """
    Chạy LaMa inpainting trên một vùng ảnh ROI (BGR [H, W, 3], Mask [H, W] uint8 0/255).
    Resize chuẩn về target_size (512x512) và resize ngược lại kích thước ban đầu.
    """
    orig_h, orig_w = roi_bgr.shape[:2]

    # Convert BGR -> RGB và chuẩn hóa về [0.0, 1.0]
    rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
    img_resized = cv2.resize(rgb, (target_size, target_size), interpolation=cv2.INTER_AREA)
    mask_resized = cv2.resize(roi_mask, (target_size, target_size), interpolation=cv2.INTER_NEAREST)

    img_tensor = (img_resized.astype(np.float32) / 255.0).transpose(2, 0, 1)[np.newaxis, ...]
    mask_tensor = (mask_resized.astype(np.float32) > 127).astype(np.float32)[np.newaxis, np.newaxis, ...]

    input_names = [inp.name for inp in session.get_inputs()]
    inputs = {
        input_names[0]: img_tensor,
        input_names[1]: mask_tensor,
    }

    outputs = session.run(None, inputs)
    out_tensor = outputs[0][0] # shape [3, H, W]

    # Handle output range (could be [0, 1] or [0, 255])
    if out_tensor.max() <= 2.0:
        out_tensor = out_tensor * 255.0
    out_img = np.clip(out_tensor.transpose(1, 2, 0), 0, 255).astype(np.uint8)

    # Convert RGB -> BGR
    out_bgr = cv2.cvtColor(out_img, cv2.COLOR_RGB2BGR)
    # Resize về kích thước ban đầu của ROI
    res_bgr = cv2.resize(out_bgr, (orig_w, orig_h), interpolation=cv2.INTER_CUBIC)
    return res_bgr


def remove_watermark_lama(
    img: np.ndarray,
    mask: np.ndarray,
    model_path: Path | str | None = None,
    roi_padding: int = 40,
) -> np.ndarray:
    """
    Khử logo thông minh bằng LaMa AI inpainting với cơ chế Crop ROI cục bộ:
    Chỉ cắt đúng vùng quanh logo + roi_padding đưa vào mạng AI,
    sau đó hòa trộn viền mềm (feather blend) trở lại ảnh gốc.
    """
    h, w = img.shape[:2]
    session, provider = get_lama_session(model_path)

    # Tìm bounding box của mask
    y_indices, x_indices = np.where(mask > 0)
    if len(y_indices) == 0:
        return img.copy()

    y_min, y_max = y_indices.min(), y_indices.max()
    x_min, x_max = x_indices.min(), x_indices.max()

    # Mở rộng ROI thành hình vuông có đệm để LaMa nhận đủ ngữ cảnh xung quanh
    box_w = x_max - x_min + 1
    box_h = y_max - y_min + 1
    side = max(box_w, box_h) + roi_padding * 2
    # Đảm bảo kích thước là bội số của 8
    side = int(np.ceil(side / 8) * 8)

    cx = (x_min + x_max) // 2
    cy = (y_min + y_max) // 2

    rx1 = max(0, cx - side // 2)
    ry1 = max(0, cy - side // 2)
    rx2 = min(w, rx1 + side)
    ry2 = min(h, ry1 + side)

    # Điều chỉnh lại nếu sát mép ảnh
    if rx2 - rx1 < side and rx1 > 0:
        rx1 = max(0, rx2 - side)
    if ry2 - ry1 < side and ry1 > 0:
        ry1 = max(0, ry2 - side)

    roi_img = img[ry1:ry2, rx1:rx2]
    roi_mask = mask[ry1:ry2, rx1:rx2]

    # Chạy LaMa trên ROI
    inpainted_roi = inpaint_patch(roi_img, roi_mask, session, target_size=512)

    # Hòa trộn mềm (soft blend) dựa trên mask đã được làm mờ nhẹ viền (feathering)
    dilated_mask = cv2.dilate(roi_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    feather = cv2.GaussianBlur(dilated_mask.astype(np.float32) / 255.0, (9, 9), 0)[:, :, np.newaxis]

    blended_roi = np.round(roi_img.astype(np.float32) * (1.0 - feather) + inpainted_roi.astype(np.float32) * feather).astype(np.uint8)

    result = img.copy()
    result[ry1:ry2, rx1:rx2] = blended_roi
    return result
