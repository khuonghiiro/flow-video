"""
LaMa (Large Mask Inpainting) ONNX Engine.
Khử watermark / logo Gemini / Imagen bằng mạng nơ-ron Fourier Convolutions (LaMa).
Chạy cục bộ qua ONNX Runtime trên patch ROI 512x512, bảo tồn 100% độ phân giải ảnh gốc.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple
import cv2
import numpy as np

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_default_model_path() -> Path:
    """Trả về đường dẫn tới model LaMa ONNX mặc định."""
    script_dir = Path(__file__).resolve().parent
    models_dir = script_dir.parent / "models" / "lama"
    
    # Ưu tiên model full fp32 (chất lượng cao nhất)
    fp32_model = models_dir / "lama_fp32.onnx"
    if fp32_model.exists():
        return fp32_model
        
    # Fallback model quantized 2025jan
    quant_model = models_dir / "inpainting_lama_2025jan.onnx"
    if quant_model.exists():
        return quant_model
        
    return fp32_model


class LamaInpainter:
    """Quản lý phiên suy luận ONNX Runtime cho model LaMa."""

    def __init__(self, model_path: Optional[str | Path] = None):
        self.model_path = Path(model_path) if model_path else get_default_model_path()
        self._session = None

    @property
    def session(self):
        """Khởi tạo phiên ONNX Runtime một lần (Lazy Loading)."""
        if self._session is None:
            import onnxruntime as ort
            if not self.model_path.exists():
                raise FileNotFoundError(f"Không tìm thấy model LaMa tại: {self.model_path}")
            
            providers = ['CPUExecutionProvider']
            if 'DmlExecutionProvider' in ort.get_available_providers():
                providers.insert(0, 'DmlExecutionProvider')
                
            self._session = ort.InferenceSession(str(self.model_path), providers=providers)
        return self._session

    def create_watermark_mask(
        self,
        size: int,
        wx_roi: int,
        wy_roi: int,
        tpl: Optional[np.ndarray] = None,
        dilation_px: int = 8
    ) -> np.ndarray:
        """Tạo mask che vùng logo trong khuôn 512x512."""
        mask = np.zeros((512, 512), dtype=np.uint8)
        
        if tpl is not None and tpl.shape[0] == size and tpl.shape[1] == size:
            base_mask = (tpl > 30).astype(np.uint8) * 255
            k_size = max(3, dilation_px * 2 + 1)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_size, k_size))
            dilated = cv2.dilate(base_mask, kernel)
        else:
            # Fallback hình tròn che phủ tâm logo
            dilated = np.zeros((size, size), dtype=np.uint8)
            radius = int(size * 0.6) + dilation_px
            center = (size // 2, size // 2)
            cv2.circle(dilated, center, radius, 255, -1)
            
        y2 = min(512, wy_roi + size)
        x2 = min(512, wx_roi + size)
        h_part = y2 - wy_roi
        w_part = x2 - wx_roi
        
        if h_part > 0 and w_part > 0:
            mask[wy_roi:y2, wx_roi:x2] = dilated[:h_part, :w_part]
            
        return mask

    def inpaint_roi(
        self,
        crop: np.ndarray,
        mask: np.ndarray,
        feather_size: int = 7
    ) -> np.ndarray:
        """Thực thi suy luận LaMa trên crop 512x512 và hòa trộn mượt."""
        img_tensor = (crop.astype(np.float32) / 255.0).transpose(2, 0, 1)[np.newaxis, ...]
        mask_tensor = (mask > 0).astype(np.float32)[np.newaxis, np.newaxis, ...]
        
        out = self.session.run(None, {'image': img_tensor, 'mask': mask_tensor})
        inpaint_patch = np.clip(out[0][0].transpose(1, 2, 0), 0, 255).astype(np.uint8)
        
        # Tạo mask feather làm mờ viền để ghép liền mạch tuyệt đối
        feather_mask = cv2.GaussianBlur(
            mask.astype(np.float32) / 255.0,
            (feather_size, feather_size),
            0
        )[:, :, np.newaxis]
        
        blended = (crop * (1.0 - feather_mask) + inpaint_patch * feather_mask).astype(np.uint8)
        return blended

    def remove_watermark(
        self,
        img: np.ndarray,
        wx: int,
        wy: int,
        size: int = 48,
        tpl: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Khử watermark trên ảnh gốc:
        - Cắt vùng 512x512 chứa watermark ở góc dưới phải.
        - Chạy LaMa AI tái tạo chi tiết.
        - Ghép mượt trở lại ảnh gốc (vùng ngoài ROI giữ nguyên 100% pixel).
        """
        h, w = img.shape[:2]
        
        # Xác định bounding box ROI 512x512
        y1_roi = max(0, h - 512)
        x1_roi = max(0, w - 512)
        crop = img[y1_roi:h, x1_roi:w].copy()
        
        # Nếu ảnh nhỏ hơn 512x512 thì resize padding
        c_h, c_w = crop.shape[:2]
        if c_h != 512 or c_w != 512:
            pad_h = 512 - c_h
            pad_w = 512 - c_w
            crop = cv2.copyMakeBorder(crop, 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT)
            
        wx_roi = wx - x1_roi
        wy_roi = wy - y1_roi
        
        mask = self.create_watermark_mask(size, wx_roi, wy_roi, tpl=tpl)
        blended_roi = self.inpaint_roi(crop, mask)
        
        result = img.copy()
        result[y1_roi:h, x1_roi:w] = blended_roi[:c_h, :c_w]
        return result


# Singleton instance để tái sử dụng session
_DEFAULT_INPAINTER: Optional[LamaInpainter] = None

def get_lama_inpainter() -> LamaInpainter:
    """Lấy hoặc khởi tạo instance LamaInpainter dùng chung."""
    global _DEFAULT_INPAINTER
    if _DEFAULT_INPAINTER is None:
        _DEFAULT_INPAINTER = LamaInpainter()
    return _DEFAULT_INPAINTER
