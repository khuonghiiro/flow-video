# /fk-rename-asset — Tự Động Đổi Tên Ảnh & Video Chuẩn Hóa Trên Google Flow (mYWVGd)

Kỹ năng tự động hoặc thủ công đổi tên hiển thị (display name) cho ảnh tĩnh và video clip trên Google Flow Web UI thông qua batch RPC `mYWVGd`.

Usage: 
- Đổi tên trực tiếp: `/fk-rename-asset <asset_id_hoặc_media_id> "<tên_mới>" [project_id]`
- Gọi REST: `POST http://127.0.0.1:8100/api/flow/video/rename` hoặc `POST http://127.0.0.1:8100/api/flow/image/rename`

---

## 🎯 1. Quy Chuẩn Đặt Tên & Điều Kiện Áp Dụng (Naming Rules)

### Điều kiện áp dụng:
1. **Khi thực hiện tạo nhân vật & video theo Master Plan (`plans/plan_character_pipeline.md`)**:
   - **BẮT BUỘC** áp dụng chuẩn đặt tên: `[{động tác gì - góc bao nhiêu độ}] {tên nhân vật - số thứ tự tạo}`.
2. **Khi User có yêu cầu đặt tên cụ thể**:
   - **Luôn lắng nghe và tuân thủ 100%** theo cách đặt tên mà User mong muốn.
3. **Khi User KHÔNG yêu cầu đặt tên và KHÔNG theo quy trình `plan_character_pipeline.md`**:
   - **KHÔNG tự ý sửa tên**, giữ nguyên tên mặc định do hệ thống Flow sinh ra.

### Cấu trúc chuẩn khi chạy Master Plan:
```
[{động tác gì - góc bao nhiêu độ}] {tên nhân vật - số thứ tự tạo}
```

- Trong đó:
  - `{động tác gì}`: Hành động cụ thể (ví dụ: `đi bộ`, `đứng thở`, `vung kiếm`, `chạy`, `chuẩn bị`, `đứng yên`).
  - `{góc bao nhiêu độ}`: Góc quay camera (ví dụ: `0`, `45`, `90`, `135`, `180`, `225`, `270`, `315`).
  - `{tên nhân vật}`: Tên nhân vật hoặc chủ thể (ví dụ: `Liễu như viên`, `Hàn Lập`, `Tiêu Viêm`).
  - `{số thứ tự tạo}`: Đánh số 2 chữ số (`01`, `02`, `03`...) là số asset thứ mấy được tạo ra cho động tác và góc quay đó.

### 🎬 Ví dụ Cho Video:
- `[đi bộ - 45] Liễu như viên - 01` *(video đi bộ góc 45 độ lần 1)*
- `[đi bộ - 45] Liễu như viên - 02` *(video đi bộ góc 45 độ lần 2 nếu tạo lại)*
- `[đứng thở - 0] Liễu như viên - 01` *(video idle loop 4s góc chính diện)*
- `[vung kiếm - 90] Liễu như viên - 01` *(video chém kiếm góc nhìn ngang)*

### 📸 Ví dụ Cho Ảnh Tĩnh:
- `[đứng yên - 0] Liễu như viên - 01`
- `[chuẩn bị - 45] Liễu như viên - 01`

---

## ⚡ 2. Hai Cách Thực Hiện Đổi Tên

### Cách 1: Tự Động Đổi Tên Ngay Khi Gọi Sinh (Khuyên Dùng)
Khi gọi API `/api/flow/generate-image` hoặc `/api/flow/generate-video`, truyền trực tiếp trường `"title"` (hoặc `"display_name"`). Backend `agent-veo3` sẽ tự động kích hoạt RPC `mYWVGd` để đổi tên ngay sau khi tác vụ được gửi lên Google Cloud:

```bash
# Tạo video kèm tự động đặt tên:
curl -X POST http://127.0.0.1:8100/api/flow/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "start_image_media_id": "<IMAGE_MEDIA_ID>",
    "end_image_media_id": "<IMAGE_MEDIA_ID>",
    "prompt": "seamless idle loop, martial arts combat stance, green background #00FF00",
    "duration": 4.0,
    "duration_s": 4,
    "project_id": "<PID>",
    "title": "[đi bộ - 45] Liễu như viên - 01"
  }'
```

### Cách 2: Đổi Tên Sau Khi Đã Tạo (Bằng Endpoint Rename)
Sau khi tạo ảnh hoặc video từ bất kỳ nguồn nào (kể cả tạo qua batch `/api/requests/batch` hoặc script khác):

1. **Đổi tên Video**:
```bash
curl -X POST http://127.0.0.1:8100/api/flow/video/rename \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "<VIDEO_OPERATION_ID_HOẶC_MEDIA_ID>",
    "title": "[đi bộ - 45] Liễu như viên - 01",
    "project_id": "<PID>"
  }'
```

2. **Đổi tên Ảnh**:
```bash
curl -X POST http://127.0.0.1:8100/api/flow/image/rename \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "<IMAGE_ASSET_ID_HOẶC_MEDIA_ID>",
    "title": "[đứng yên - 0] Liễu như viên - 01",
    "project_id": "<PID>"
  }'
```

> **Ghi chú thông minh**: Backend đã có cơ chế tự động phân giải (`resolve_asset_id`): Bạn có thể truyền thẳng `media_id` (UUID ảnh hoặc UUID video) mà không cần phải tìm thủ công Node ID, hệ thống sẽ tự động tra cứu project graph và đổi tên chính xác 100%.

---

## 🔄 3. Tích Hợp Vào Quy Trình Khi Người Dùng Yêu Cầu Tạo Video Khác

Bất cứ khi nào người dùng yêu cầu:
- *"Tạo cho tôi video nhân vật X đang làm hành động Y"*
- *"Tạo video loop 4s từ ảnh này"*
- *"Tạo một loạt hoạt ảnh combat"*

**AI phải thực hiện tuần tự:**
1. Sinh ảnh (hoặc lấy ảnh có sẵn) -> Đổi tên thành `[{tư thế - góc độ}] {Tên nhân vật} - {STT}` (ví dụ: `[đứng yên - 0] Liễu như viên - 01`).
2. Tạo video với prompt hành động và góc quay tương ứng.
3. **Ngay sau khi có kết quả video** (hoặc ngay lúc submit): Gọi API đổi tên video thành `[{động tác - góc độ}] {Tên nhân vật} - {STT}` (ví dụ: `[đi bộ - 45] Liễu như viên - 01`).
4. Báo cáo lại cho người dùng ID và Tên hiển thị rõ ràng trên Google Flow.
