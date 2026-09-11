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
4. **Tạo video từ ảnh đã upload:**
   - **1 ảnh (Single Frame):** Bắt buộc dùng logic **I2V (Image-to-Video)** qua RPC `eb1hJf` (chỉ truyền duy nhất `start_image_media_id`), **tuyệt đối KHÔNG dùng logic F2F (Frame-to-Frame / Interpolation - `nprQif`)**.
   - **2 ảnh (Start & End Frame):** Sử dụng logic **F2F** qua RPC `nprQif`.
   - **1-3 ảnh tham chiếu phong cách/nhân vật:** Sử dụng logic **R2V** qua RPC `MZZa6b`.

---

## 🧠 Nguyên Lý Hoạt Động (Reverse Alpha Blending)

Khác với các công cụ inpainting (xóa vật thể AI) thường làm nhòe mờ chi tiết nền vì phải "đoán" pixel thay thế, thuật toán này giải toán trực tiếp:

$$I = (1 - \alpha) \cdot B + \alpha \cdot W$$

* $I$: Pixel ảnh hiện tại (đang chứa logo).
* $W$: Màu của logo watermark ($255$ - màu trắng).
* $\alpha$: Bản đồ độ trong suốt đã được hiệu chuẩn ($\approx 0.28$).
* $B$: Pixel gốc ban đầu cần khôi phục.

Phép đảo ngược khôi phục chính xác:

$$B = \frac{I - \alpha \cdot 255}{1 - \alpha}$$

👉 **Kết quả:** Vân sóng nước, sợi vải, lá cây, hạt noise tự nhiên và chi tiết vi mô dưới lớp watermark được phục hồi nguyên vẹn 100%, không để lại vệt mờ hay đường viền.

---

## 🚀 Hướng Dẫn Sử Dụng Chi Tiết

Mọi lệnh đều chạy từ thư mục gốc của dự án (`flow-video`):

### 1. Khử logo cho một bức ảnh đơn lẻ:
Tự động tạo ra file `<tên_ảnh>_cleaned.<ext>` cùng thư mục:
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output/A_breathtaking_golden_sunset.jpeg"
```

### 2. Khử logo và lưu sang file đích tùy chọn:
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output/input.jpeg" -o "agent-veo3/output/output_clean.jpeg"
```

### 3. Xử lý hàng loạt (Batch Processing) cho cả thư mục:
Tự động quét tất cả ảnh `.jpg`, `.jpeg`, `.png`, `.webp` trong thư mục và làm sạch đồng loạt:
```bash
python agent-veo3/scripts/remove_gemini_watermark.py "agent-veo3/output"
```

### 4. Chạy kịch bản kiểm thử (Test Script):
Script kiểm thử nằm trong thư mục `tests/` riêng biệt (không ảnh hưởng Git):
```bash
python agent-veo3/scripts/tests/test_e2e_generate_and_unwatermark.py
```

---

## ⚡ Hiệu Năng Xử Lý

* **Thời gian thuật toán:** ~6.6 ms / ảnh (> 150 FPS, đủ tốc độ xử lý video real-time).
* **Thời gian tổng thể (kèm đọc/ghi ổ đĩa):** ~35 ms / ảnh (~30 ảnh / giây).
* **Phần cứng yêu cầu:** Chạy trực tiếp trên CPU qua NumPy và OpenCV, không tốn VRAM GPU, không cần tải model AI nặng.
