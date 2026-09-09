# /fk-gen-loop-4s — Tạo Animation Loop 4s (Start & End Frame Trùng Nhau)

Kỹ năng tạo video hoạt ảnh lặp vô tận (seamless loop 4 giây) cho nhân vật 2D / Sprite / VFX từ **Tab 4: Trợ Lý Prompt AI**.

Usage: `/fk-gen-loop-4s <project_id> <video_id> [scene_id]`

---

## 🎯 Nguyên Lý Hoạt Động (Start-End Frame Loop)
- Để tạo chuyển động khép kín hoàn hảo (seamless loop) cho Sprite 2D (ví dụ: Idle thở, vung kiếm, tóc bay, bay bổng):
  1. Tạo hoặc chọn ảnh tĩnh gốc làm chuẩn (`start_frame`).
  2. **Gán chính ảnh đó làm `end_frame`** (`end_scene_media_id = image_media_id`).
  3. API Veo3/Flow sẽ gọi `start_end_frame_2_video` (i2v_fl) với thời lượng 4s, ép frame đầu (0s) và frame cuối (4s) phải trùng khớp 100%, tạo ra chu kỳ chuyển động lặp vô tận.

---

## 📋 Các Bước Thực Hiện Chi Tiết

### Bước 0: Xác định Orientation & Lấy thông tin Project
```bash
PROJ_OUT=$(curl -s http://127.0.0.1:8100/api/projects/<PID>/output-dir)
OUTDIR=$(echo "$PROJ_OUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['path'])")
ORI=$(cat ${OUTDIR}/meta.json | python3 -c "import sys,json; print(json.load(sys.stdin).get('orientation','HORIZONTAL'))")
ori=$(echo "$ORI" | tr '[:upper:]' '[:lower:]')
```

### Bước 1: Kiểm tra ảnh của Scene
Lấy danh sách scene của video:
```bash
curl -s "http://127.0.0.1:8100/api/scenes?video_id=<VID>"
```
- Nếu scene chưa có ảnh (`${ori}_image_status != "COMPLETED"`): Chạy `/fk-gen-images <PID> <VID>` trước.
- Đảm bảo `${ori}_image_media_id` là UUID hợp lệ.

### Bước 2: Thiết lập Start Frame = End Frame cho Scene
Với mỗi scene cần làm animation loop, gán `${ori}_end_scene_media_id` bằng chính `${ori}_image_media_id`:
```bash
# Lấy IMG_ID hiện tại của scene
IMG_ID=$(curl -s "http://127.0.0.1:8100/api/scenes/<SID>" | python3 -c "import sys,json; print(json.load(sys.stdin)['${ori}_image_media_id'])")

# PATCH gán end_scene_media_id = IMG_ID (tạo vòng lặp khép kín)
curl -X PATCH http://127.0.0.1:8100/api/scenes/<SID> \
  -H "Content-Type: application/json" \
  -d "{\"${ori}_end_scene_media_id\": \"${IMG_ID}\"}"
```

### Bước 3: Cập nhật Transition Prompt chuẩn 4s Loop
Cập nhật prompt chuyển động (chú ý giữ vững phông xanh `#00FF00` và chuyển động quay về điểm xuất phát):
```bash
curl -X PATCH http://127.0.0.1:8100/api/scenes/<SID> \
  -H "Content-Type: application/json" \
  -d '{
    "transition_prompt": "4-second seamless looping animation, starting and ending at the exact same pose. Smooth natural idle breathing, gentle hair and fabric flutter, fluid subtle movement that loops back seamlessly to frame 0. Fixed centered camera, no background shift, pure chroma green background #00FF00 preserved with zero artifacts."
  }'
```

### Bước 4: Gửi Batch Request tạo Video
```bash
curl -X POST http://127.0.0.1:8100/api/requests/batch \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {"type": "GENERATE_VIDEO", "scene_id": "<SID>", "project_id": "<PID>", "video_id": "<VID>", "orientation": "${ORI}"}
    ]
  }'
```

Server sẽ tự động kích hoạt `start_end_frame_2_video` vì đã có `end_scene_media_id`.

### Bước 5: Chờ hoàn tất & Đưa vào Studio 2D
Poll trạng thái:
```bash
curl -s "http://127.0.0.1:8100/api/requests/batch-status?video_id=<VID>&type=GENERATE_VIDEO"
```
Khi `done: true`, video loop 4s sẵn sàng. Người dùng có thể:
1. Chuyển sang **Tab 1.3: Video Animation Slicer & AI Matting** trong Studio 2D để tự động cắt thành các frame PNG trong suốt.
2. Nạp vào **Tab 1.2: Animation Sequencer** để tạo hoạt ảnh sprite sheet trong game/ứng dụng.
