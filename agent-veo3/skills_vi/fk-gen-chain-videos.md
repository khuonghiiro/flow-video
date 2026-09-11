# Hướng dẫn Kỹ năng: Tạo Chuỗi Video Nối Tiếp Liền Mạch (fk-gen-chain-videos)

Tự động kết nối các phân cảnh liên tiếp nhau bằng kỹ thuật Frame-to-Frame (`nprQif`) để khi ghép nối các video lại thành 1 video dài thì phân cảnh chuyển đổi hoàn toàn mượt mà, không bị giật hay cắt ngang.

Cú pháp: `/fk-gen-chain-videos <project_id> <video_id>`

---

## 🔗 Nguyên lý hoạt động của Chuỗi Video Liền Mạch

1. **Phân cảnh N (đầu chuỗi hoặc giữa chuỗi):**
   - `start_image`: Ảnh phân cảnh N.
   - `end_image`: Ảnh phân cảnh N+1.
   - **Cơ chế:** Google Flow render video chuyển động xuất phát từ ảnh N và kết thúc chính xác tại ảnh N+1 qua RPC `nprQif` (Model: `veo_3_1_interpolation_lite_low_priority`, 8s).

2. **Phân cảnh cuối cùng trong chuỗi (không có cảnh con nối tiếp):**
   - Chỉ có `start_image` (ảnh của chính phân cảnh đó), không có `end_image`.
   - **Cơ chế:** Tự động dùng RPC `MZZa6b` (Tạo video với ảnh - R2V).

3. **Bảo toàn bất biến ghép nối:**
   - Frame cuối của video N == Ảnh mở đầu của phân cảnh N+1 == Frame đầu của video N+1.
   - Khi chạy ghép nối (concat), 2 video chuyển tiếp mượt mà như 1 cú máy liên tục!

---

## 🛠️ Gọi Trực Tiếp API Frame-to-Frame

```bash
curl -X POST http://127.0.0.1:8100/api/flow/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "start_image_media_id": "<START_MEDIA_ID>",
    "end_image_media_id": "<END_MEDIA_ID>",
    "prompt": "Chuyển tiếp mượt mà từ cảnh ngồi sang đứng dậy",
    "project_id": "<PID>",
    "aspect_ratio": "VIDEO_ASPECT_RATIO_PORTRAIT",
    "duration_s": 8,
    "model_family": "veo",
    "count": 2
  }'
```
- Sử dụng RPC `nprQif`, tự động kích hoạt 2 video song song.
