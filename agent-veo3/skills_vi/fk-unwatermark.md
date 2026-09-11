# /fk-unwatermark — Khử Logo Watermark Gemini / Imagen (Giữ 100% Độ Nét Pixel)

Kỹ năng tự động phát hiện và khử sạch logo watermark hình ngôi sao 4 cánh ở góc phải bên dưới do Google Gemini / Imagen / Google Flow tạo ra, sử dụng thuật toán toán học **Reverse Alpha Blending** mà vẫn giữ nguyên 100% độ sắc nét pixel, vân chi tiết và chất lượng gốc.

Usage: `/fk-unwatermark <đường_dẫn_ảnh_hoặc_thư_mục> [--output <đường_dẫn_xuất>] [--alpha 0.28] [--lama]`

- `<đường_dẫn_ảnh_hoặc_thư_mục>` — File ảnh đơn lẻ hoặc thư mục chứa nhiều ảnh cần làm sạch
- `--output` / `-o` — Tùy chọn đường dẫn file hoặc thư mục đích
- `--alpha` / `-a` — Độ mờ của watermark (mặc định: `0.28`, chuẩn cho Gemini / Imagen 3)
- `--lama` / `-m lama` — Sử dụng mô hình AI LaMa Inpainting (xóa sạch 100% cả trên nền tối và bầu trời)

---

## 🎯 Khi Nào Cần Sử Dụng

1. **Sau khi sinh ảnh nhân vật / bối cảnh:** Vừa tạo ảnh tham chiếu nhân vật (character refs) hoặc ảnh scene từ Google Flow xong và muốn khử ngay logo trước khi render.
2. **Trước khi đưa vào pipeline video:** Tránh tình trạng watermark từ ảnh tĩnh bị AI khuếch đại thành dị tật chuyển động nhấp nháy trong video Veo2 / Veo3 (`fk-gen-videos`, `fk-gen-loop-4s`, `fk-gen-chain-videos`).
3. **Làm ảnh thumbnail YouTube / Banner:** Đảm bảo ảnh bìa và thumbnail sắc nét nguyên bản, không bị đóng dấu watermark nền tảng.

---

## 🏗️ Cấu Trúc Mã Nguồn & Quy Chuẩn Thư Mục I/O

Tuân thủ nguyên tắc phân tách rõ ràng giữa mã nguồn chính thức, kịch bản thử nghiệm và luồng thư mục xử lý ảnh:

```
agent-veo3/
├── assets/watermarks/                  # Template mask chuẩn (bg_48.png, bg_96.png)
├── output/
│   ├── watermarks/                     # [I/O] Thư mục lưu ảnh tải về còn chứa watermark từ Google Flow
│   └── cleaned/                        # [I/O] Thư mục lưu ảnh sau khi đã khử sạch 100% logo
├── scripts/
│   ├── remove_gemini_watermark.py      # [PRODUCTION] Logic xử lý chính (Được commit Git)
│   └── tests/                          # [TESTING] Thư mục chứa script kiểm thử (ĐÃ ĐƯA VÀO .gitignore, KHÔNG PUSH GIT)
│       └── test_full_pipeline_clean_flow.py
└── skills_vi/
    └── fk-unwatermark.md               # Tài liệu hướng dẫn Tiếng Việt
```

### 📂 Quy Chuẩn Luồng Xử Lý & Upload Ảnh Lên Flow
1. **Tải ảnh thô về:** Tất cả ảnh do Flow sinh ra có logo watermark PHẢI được lưu vào `agent-veo3/output/watermarks/`.
2. **Khử logo:** Thuật toán xử lý và xuất ảnh sạch sang thư mục riêng biệt `agent-veo3/output/cleaned/`.
3. **Upload ảnh sạch lên Flow:**
   - AI quét đúng các file trong `agent-veo3/output/cleaned/`.
   - Kiểm tra hash/tên file đã upload trong metadata để **tuyệt đối không upload trùng lặp 2 lần cùng một ảnh**.
   - Lưu lại `media_id` (UUID 36 ký tự) sạch trả về từ Google Flow.
4. **Tạo video từ ảnh đã upload (Chuẩn Google Flow Wire Protocol):**
   - **Tạo video với ảnh (1 đến 3 ảnh):** Bắt buộc dùng chế độ **Tạo video với ảnh (R2V / Image-to-Video)** qua RPC **`MZZa6b`** (Model: `veo_3_1_r2v_lite_low_priority`, thời lượng: cố định **8s**, 0 credit). **Tuyệt đối KHÔNG dùng cơ chế frame hay F2F cho 1 ảnh đơn lẻ**.
   - **Tạo video Frame to Frame (Bắt buộc đủ 2 ảnh Start & End):** Sử dụng logic **F2F** qua RPC **`nprQif`** (Model: `veo_3_1_i2v_s_lite_6s_fl_low_priority` cho 6s, hoặc `veo_3_1_interpolation_lite_low_priority` cho 8s). Cần đủ cả `start_image_media_id` VÀ `end_image_media_id`.
   - **Tạo video Text-to-Video (0 ảnh):** Sử dụng RPC **`YhhmEf`** (Model: `veo_3_1_t2v_lite_low_priority`, 4s/6s/8s).

---

## 🧠 Nguyên Lý Hoạt Động (Reverse Alpha Blending + Adaptive Grain)

Khác với các công cụ inpainting (xóa vật thể AI) thường làm nhòe mờ chi tiết nền vì phải "đoán" pixel thay thế, thuật toán này giải toán trực tiếp:

$$I = (1 - \alpha) \cdot B + \alpha \cdot W$$

* $I$: Pixel ảnh hiện tại (đang chứa logo).
* $W$: Màu của logo watermark ($255$ - màu trắng).
* $\alpha$: Bản đồ độ trong suốt chuẩn xác (`perfect_alpha_48.npy` / `perfect_alpha_96.npy` với đỉnh $\approx 0.315 / 0.297$).
* $B$: Pixel gốc ban đầu cần khôi phục.

Phép đảo ngược khôi phục chính xác:

$$B = \frac{I - \alpha \cdot 255}{1 - \alpha}$$

### 🔬 Bổ sung Phục Hồi Vi Hạt Tự Nhiên (Adaptive Micro-Grain Restoration)
Ở vùng tâm lõi watermark ($\alpha > 0.15$), quá trình lượng tử hóa số nguyên 8-bit và nén JPEG DCT của Gemini làm suy giảm các vi hạt nhiễu tần số cao của nền. Thuật toán tự động đo độ lệch chuẩn phương sai vi mô ($\sigma_{bg}$) ở viền xung quanh và tái tạo bù lượng vi hạt đối xứng hoàn hảo, đảm bảo khi zoom sâu 6x - 10x cũng **tuyệt đối không còn bất kỳ vệt phẳng, vệt tối hay đường viền nào**.

---

## 🚀 Hướng Dẫn Sử Dụng Chi Tiết

Mọi lệnh đều chạy từ thư mục gốc của dự án (`flow-video`):

### 1. Khử logo bằng Toán Học Reverse Alpha Blending (Mặc định - 6ms):
Giữ 100% pixel gốc, tự bù vi hạt thích ứng, không cần model AI:
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output/A_breathtaking_golden_sunset.jpeg"
```

### 2. Khử logo bằng Deep AI LaMa Inpainting (Tùy chọn nâng cao):
Sử dụng mô hình AI LaMa ONNX (tự động tăng tốc GPU NVIDIA / GPU DirectX 12 / CPU):
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output/input.jpeg" -e lama
```

### 3. Khử logo và lưu sang file đích tùy chọn:
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output/input.jpeg" -o "agent-veo3/output/output_clean.jpeg"
```

### 4. Xử lý hàng loạt (Batch Processing) cho cả thư mục:
Tự động quét tất cả ảnh `.jpg`, `.jpeg`, `.png`, `.webp` trong thư mục và làm sạch đồng loạt:
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output"
```

---

## 📦 Hướng Dẫn Tải Model AI LaMa (`lama_fp32.onnx`)

Khi bạn hoặc user khác pull repo về máy mới, chế độ mặc định **Reverse Alpha** luôn hoạt động sẵn sàng 100% mà không cần tải thêm bất cứ file nào.

Nếu muốn sử dụng thêm chế độ AI LaMa Inpainting (`-e lama`):
1. **Tải file model (khoảng ~198MB):**
   - **Link HuggingFace:** [lama_fp32.onnx (208 MB)](https://huggingface.co/Carve/LaMa-ONNX/resolve/main/lama_fp32.onnx?download=true)
   - **Link GitHub Releases:** [big-lama.onnx (208 MB)](https://github.com/xulihang/ImageTrans_plugins/releases/download/plugins/big-lama.onnx)
2. **Copy file vào thư mục:**
   ```
   agent-veo3/assets/models/lama_fp32.onnx
   ```
   *(Hệ thống hỗ trợ tự động cả 2 tên file `lama_fp32.onnx` hoặc `big-lama.onnx`)*.
3. **Hỗ trợ phần cứng:** Tự động dùng card GPU NVIDIA (CUDA), GPU Windows DirectX 12 (Intel/AMD/NVIDIA), hoặc CPU thuần mà không cần thiết lập gì thêm.

---

## ⚡ Hiệu Năng Xử Lý

* **Engine Reverse Alpha (Toán học):** ~6.6 ms / ảnh (> 150 FPS), 0 MB model, bảo tồn nguyên vẹn 100% pixel gốc.
* **Engine LaMa AI (Deep Learning):** ~15 ms / ảnh (NVIDIA GPU) hoặc ~150 - 250 ms / ảnh (CPU thuần qua ONNX Runtime), tự động nối vân nền phức tạp.
