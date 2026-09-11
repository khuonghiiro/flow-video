# Hướng Dẫn Tải Model LaMa Inpainting (AI Engine)

Thư mục này dùng để lưu trữ file mô hình **LaMa (Large Mask Inpainting) ONNX** phục vụ cho chế độ AI deep inpainting của công cụ khử logo watermark (`remove_gemini_watermark.py`).

---

## 1. File Model Cần Thiết

Hệ thống hỗ trợ tự động một trong hai tên file sau (đặt trực tiếp vào thư mục này):
- `lama_fp32.onnx` (Khuyên dùng)
- hoặc `big-lama.onnx`

> **Dung lượng:** ~198 MB đến 208 MB.

---

## 2. Link Tải Trực Tiếp

Nếu môi trường mạng của bạn chặn tải tự động từ terminal, hãy mở trình duyệt và tải từ 1 trong 2 nguồn sau:

1. **HuggingFace (Khuyên dùng):**
   [https://huggingface.co/Carve/LaMa-ONNX/resolve/main/lama_fp32.onnx?download=true](https://huggingface.co/Carve/LaMa-ONNX/resolve/main/lama_fp32.onnx?download=true)

2. **GitHub Releases (Dự phòng):**
   [https://github.com/xulihang/ImageTrans_plugins/releases/download/plugins/big-lama.onnx](https://github.com/xulihang/ImageTrans_plugins/releases/download/plugins/big-lama.onnx)

Sau khi tải xong, hãy copy file vào đúng đường dẫn:
```
agent-veo3/assets/models/lama_fp32.onnx
```

---

## 3. Khả Năng Tương Thích Phần Cứng (Hardware Acceleration)

Mô hình LaMa ONNX tự động nhận diện và tận dụng phần cứng có sẵn theo thứ tự ưu tiên:
1. **NVIDIA GPU (CUDA):** Tự động kích hoạt `CUDAExecutionProvider` nếu có GPU NVIDIA (tốc độ ~15ms - 30ms).
2. **DirectX 12 GPU (DirectML):** Tự động nhận diện GPU Intel / AMD Radeon / NVIDIA qua `DmlExecutionProvider` trên Windows.
3. **CPU thuần:** Tự động fallback về `CPUExecutionProvider` (tốc độ ~150ms - 250ms trên CPU thông thường).

---

## 4. Cách Sử Dụng Trong Terminal

- **Kích hoạt chế độ AI LaMa:**
  ```bash
  python agent-veo3/scripts/remove_gemini_watermark.py "duong_dan_anh.jpeg" -e lama
  ```
- **Chế độ Mặc định (Reverse Alpha Blending - Không cần model AI):**
  ```bash
  python agent-veo3/scripts/remove_gemini_watermark.py "duong_dan_anh.jpeg"
  ```
