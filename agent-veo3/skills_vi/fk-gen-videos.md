# Hướng dẫn Kỹ năng: Tạo Video Toàn Bộ Phân Cảnh (fk-gen-videos)

Tạo video cho tất cả phân cảnh (scenes) sử dụng Google Flow Veo 3.1 Batch API với đầy đủ các chế độ:
1. **Tạo video với ảnh (Image-to-Video / R2V)**: RPC `MZZa6b` (1 đến 3 ảnh tham chiếu, 8s).
2. **Tạo video Frame-to-Frame (F2F)**: RPC `nprQif` (Bắt buộc đủ 2 frame: Start Frame + End Frame, 4s/6s/8s).
3. **Text-to-Video (T2V)**: RPC `YhhmEf` (Chỉ prompt, 4s/6s/8s).

Cú pháp: `/fk-gen-videos <project_id> <video_id>`

---

## 🧭 Quy tắc cốt lõi về cơ chế tạo Video của Google Flow

1. **Tạo video với ảnh (Image-to-Video / R2V):**
   - **RPC:** `MZZa6b`
   - **Model:** `veo_3_1_r2v_lite_low_priority` (0 token)
   - **Độ dài (Duration):** Cố định **8s** (không dùng được 4s hay 6s).
   - **Tham chiếu:** Tối đa 3 ảnh tham chiếu (`[[null, id1], [null, id2], [null, id3]]`).
   - **Không dùng Frame start:** Google Flow tuyệt đối không dùng cấu trúc frame cho chế độ tạo video với ảnh.
   - **Số lượng (Count):** 1 đến 4 video song song cùng 1 prompt.

2. **Tạo video từ Frame to Frame (Interpolation / F2F):**
   - **RPC:** `nprQif`
   - **Model:** `veo_3_1_interpolation_lite_low_priority` (0 token)
   - **Độ dài (Duration):** 4s, 6s, 8s (khuyên dùng 8s).
   - **Yêu cầu bắt buộc:** Phải có đủ **2 Frame**: Start Frame VÀ End Frame. Tuyệt đối không dùng F2F khi chỉ có 1 frame. Nếu chỉ có 1 frame, hệ thống tự động chuyển sang `MZZa6b` (Tạo video với ảnh).
   - **Số lượng (Count):** 1 đến 4 video song song.

---

## Bước 0: Xác định tỷ lệ khung hình (Orientation)

```bash
PROJ_OUT=$(curl -s http://127.0.0.1:8100/api/projects/<PID>/output-dir)
OUTDIR=$(echo "$PROJ_OUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['path'])")
ORI=$(cat ${OUTDIR}/meta.json | python3 -c "import sys,json; print(json.load(sys.stdin).get('orientation','HORIZONTAL'))")
ori=$(echo "$ORI" | tr '[:upper:]' '[:lower:]')
```
- Không bao giờ hardcode `VERTICAL` hoặc `HORIZONTAL`. Dùng biến `${ORI}`.

---

## Bước 1: Kiểm tra điều kiện tiên quyết (Ảnh phân cảnh)

```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```
Tất cả phân cảnh phải có `${ori}_image_media_id` hợp lệ và `${ori}_image_status` là `"COMPLETED"`.

---

## Bước 2: Gửi lệnh Batch qua Server

Hệ thống backend tự động điều phối hàng đợi (tối đa 5 request đồng thời, nghỉ 10s cooldown):

```bash
curl -X POST http://127.0.0.1:8100/api/requests/batch \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {"type": "GENERATE_VIDEO", "scene_id": "<SID1>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "${ORI}"},
      {"type": "GENERATE_VIDEO", "scene_id": "<SID2>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "${ORI}"}
    ]
  }'
```

Kiểm tra tiến độ:
```bash
curl -s "http://127.0.0.1:8100/api/requests/batch-status?video_id=<VID>&type=GENERATE_VIDEO"
```

---

## 🛠️ Gọi trực tiếp qua Veo 3.1 API (Manual / Direct)

### 1. Tạo video với ảnh (Image-to-Video / R2V)
```bash
curl -X POST http://127.0.0.1:8100/api/flow/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "start_image_media_id": "<MEDIA_UUID_ĐÃ_XOÁ_LOGO>",
    "prompt": "Chuyển cảnh vũ trụ huyền ảo, camera trôi chậm về phía trước",
    "project_id": "<PID>",
    "aspect_ratio": "VIDEO_ASPECT_RATIO_PORTRAIT",
    "duration_s": 8,
    "count": 2
  }'
```
- Tự động kích hoạt RPC `MZZa6b`, độ dài 8s, sinh 2 video đồng thời.

### 2. Tạo video Frame to Frame (F2F)
```bash
curl -X POST http://127.0.0.1:8100/api/flow/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "start_image_media_id": "<START_FRAME_UUID>",
    "end_image_media_id": "<END_FRAME_UUID>",
    "prompt": "Chuyển tiếp mượt mà giữa hai khung cảnh, ánh sáng lan tỏa",
    "project_id": "<PID>",
    "aspect_ratio": "VIDEO_ASPECT_RATIO_PORTRAIT",
    "duration_s": 8,
    "count": 2
  }'
```
- Tự động kích hoạt RPC `nprQif`, độ dài 8s với đủ Start và End frame.
