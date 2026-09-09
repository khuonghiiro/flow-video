# Cẩm Nang Tạo Dự Án Video Mới Trên Google Flow (Dành Cho Người Dùng)
> **Thư mục tiếng Việt**: `agent-veo3/skills_vi/`  
> **Phiên bản Tiếng Anh cho AI Agent**: [`../skills/fk-create-project.md`](../skills/fk-create-project.md)

---

## 📖 1. Giới Thiệu & Điểm Đột Phá Của Agent Veo3

Trước đây trong FlowKit gốc, kỹ năng tạo dự án (`flowkit/skills/fk-create-project.md`) có một hạn chế rất lớn: **FlowKit không thể tự tạo dự án trên Google Flow** và bắt buộc người dùng phải mở trình duyệt web `flow.google.com`, tự bấm tạo dự án, rồi copy mã UUID từ thanh địa chỉ dán vào terminal.

Trong hệ thống **`agent-veo3`**, toàn bộ quy trình này đã được **tự động hóa 100%**:
- **Tự động tạo dự án trên Google Flow qua Batch RPC `jHPbke`**: Khi bạn tạo dự án qua API, backend tự động gửi lệnh lên Google Cloud để tạo dự án thật và lấy mã dự án về.
- **Tự động đồng bộ tên dự án qua Batch RPC `o8DA4`**: Tên dự án bạn đặt sẽ được cập nhật ngay trên giao diện web của Google Flow.
- **Tự động nhận diện Tab Flow đang mở**: Nếu bạn đang mở sẵn trang Google Flow trên Chrome, Chrome Extension sẽ tự động lấy `project_id` mà không cần nhập tay.

---

## 🎯 2. Các Thông Tin Cần Chuẩn Bị Trước Khi Tạo Dự Án

| Thông tin | Mô tả | Ví dụ |
| :--- | :--- | :--- |
| **Tên dự án (`name`)** | Tên đại diện cho toàn bộ video / chuỗi video | `"Hành Trình Luna Đến Hành Tinh Kẹo"` |
| **Cốt truyện (`story`)** | Tóm tắt nội dung chính và thông điệp | `"Chú mèo Luna hạ cánh xuống hành tinh kẹo ngọt và khám phá kho báu..."` |
| **Chất liệu ảnh (`material`)** | Phong cách mỹ thuật thống nhất cho mọi cảnh | `3d_pixar`, `realistic`, `anime`, `stop_motion`, `minecraft`, `oil_painting` *(gọi `GET /api/materials` để xem)* |
| **Nhân vật (`characters`)** | Tên + mô tả ngoại hình mặc định (**1 bộ trang phục**) | `"Mèo trắng mặc đồ phi hành gia, đội mũ kính phi thuyền"` |
| **Bối cảnh (`locations`)** | Địa điểm diễn ra câu chuyện | `"Núi Kẹo Bông", "Rừng Kẹo Dẻo", "Bãi Đáp Tàu"` |
| **Đạo cụ (`visual_asset`)** | Vật phẩm, phương tiện, vũ khí quan trọng | `"Tàu Thám Hiểm Cổ Điển", "La Bàn Kẹo Ngọt"` |
| **Khung hình (`orientation`)** | Tỷ lệ hiển thị | `HORIZONTAL` (16:9 - YouTube ngang) hoặc `VERTICAL` (9:16 - TikTok/Shorts/Reels) |

---

## 🛡️ 3. Bí Quyết Vượt Bộ Lọc An Toàn Cho Nhân Vật Người Thật (Bypass Safety Filter)

Khi làm phim tài liệu, tin tức hoặc nhân vật dựa trên **người nổi tiếng có thật** (chính trị gia, danh nhân), AI của Google rất dễ kích hoạt lỗi `PUBLIC_ERROR_UNSAFE_GENERATION`.

### Nguyên nhân:
Google quét cả ảnh chân dung gửi lên, từ khóa trong câu lệnh (prompt), và ảnh đầu ra. Nếu nhận diện ra mặt người nổi tiếng, hệ thống sẽ chặn ngay.

### 5 Quy tắc vàng để không bị chặn:
1. **Dùng Bí Danh Tiếng Anh (Role-based Alias)**: Tuyệt đối không dùng tên thật. Dùng chức danh tiếng Anh:
   - ✅ Dùng: `"The Commander"`, `"Iron Premier"`, `"The Senior Diplomat"`.
   - ❌ Tránh: Tên thật của các nguyên thủ hoặc người nổi tiếng.
2. **Mô tả ngoại hình, không mô tả danh tính**:
   - Tả màu tóc, vóc dáng, dáng đứng, bộ vest đặc trưng, không đề cập họ là ai.
3. **Ảnh tham chiếu chụp sau lưng (Back View) hoặc góc nghiêng (Profile)**:
   - Trong `image_prompt`, ghi rõ: `"seen from behind"` hoặc `"left side profile"`.
   - Người xem vẫn nhận ra nhân vật qua bóng lưng và dáng vóc, nhưng AI không thấy mặt nên không kích hoạt bộ lọc!
4. **Góc máy trong phân cảnh phải khớp với ảnh**:
   - Nếu ảnh ref chụp sau lưng, prompt của cảnh cũng phải là: `"View from behind The Commander..."`.
5. **Thang nâng bậc 4 cấp khi bị chặn**:
   - **Cấp 1**: Đổi câu lệnh sang góc máy phía sau/bên hông. Thử lại 2-3 lần.
   - **Cấp 2**: Bỏ từ bí danh, thay bằng mô tả chung (`"An older distinguished leader"`).
   - **Cấp 3**: Bỏ ảnh tham chiếu cho cảnh đó (`character_names: []`), chỉ dùng prompt mô tả.
   - **Cấp 4**: Lược bỏ toàn bộ chi tiết nhạy cảm (màu tóc, vest quen thuộc), chỉ tả một người bình thường.

---

## 🚀 4. Quy Trình Thực Hiện 6 Bước Chuẩn Thực Chiến

### Bước 0: Tạo Dự Án Trên Google Flow (Tự Động)
Bạn **không cần** mở Google Flow để tạo tay.
- Khi gọi API `POST /api/projects` (ở Bước 1), hệ thống sẽ **tự động gọi RPC `jHPbke`** tạo dự án trên Flow.
- Nếu muốn tạo độc lập:
  ```bash
  curl -X POST http://127.0.0.1:8100/api/flow/project/create \
    -H "Content-Type: application/json" \
    -d '{"title": "Dự Án Video Veo3"}'
  ```

---

### Bước 1: Khởi Tạo Dự Án & Danh Sách Nhân Vật/Bối Cảnh
Gửi yêu cầu khởi tạo toàn diện:
```bash
curl -X POST http://127.0.0.1:8100/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Chuyến Phiêu Lưu Của Luna",
    "description": "Khám phá hành tinh kẹo ngọt",
    "story": "Luna, chú mèo phi hành gia, hạ cánh xuống Hành Tinh Kẹo Ngọt...",
    "material": "3d_pixar",
    "characters": [
      {
        "name": "Luna",
        "entity_type": "character",
        "description": "Cute white cat wearing a retro astronaut suit with glass helmet and orange badges.",
        "voice_description": "Playful, youthful, expressive female voice"
      },
      {
        "name": "Candy Mountain",
        "entity_type": "location",
        "description": "Majestic pastel-colored mountains made of swirling candy canes under a cotton candy sky."
      }
    ]
  }'
```
*Lưu lại mã `id` trả về (đây là `<PID>`).*

---

### Bước 2: Tạo Video Container
Một dự án có thể chứa nhiều tập video. Tạo container cho tập 1:
```bash
curl -X POST http://127.0.0.1:8100/api/videos \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "<PID>",
    "title": "Tập 1: Đặt Chân Lên Hành Tinh Kẹo",
    "display_order": 0
  }'
```
*Lưu lại `id` trả về (đây là `<VID>`).*

---

### Bước 3: Tạo Phân Cảnh (Scenes) & Viết Prompt Veo3 Chuẩn
Veo 3 hỗ trợ âm thanh tự nhiên (tiếng động môi trường, giọng nói). Cấu trúc prompt 5 thành phần:
`[Góc máy] + [Chủ thể] + [Hành động chia theo giây] + [Ánh sáng] + [Âm thanh & SFX]`

```bash
curl -X POST http://127.0.0.1:8100/api/scenes \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "<VID>",
    "display_order": 0,
    "prompt": "Luna stepping out of Star Cruiser airlock onto sugary surface of Candy Mountain. Wide shot, low angle.",
    "video_prompt": "Wide shot of Star Cruiser ramp lowering. 0-3s: Luna emerges in her white space suit, stepping onto the crystalline sugar soil. The camera tracks slowly alongside. 3-6s: She looks around at the swirling pastel mountains. 6-8s: Luna says: \"What a magical place!\" (no subtitles)\n\nAudio: soft cosmic hum, gentle sugary wind.\nSFX: metallic ramp clinking, boots stepping on sugar crystals.\nNegative: subtitles, watermark, text overlay, distorted face.",
    "character_names": ["Luna", "Candy Mountain"],
    "chain_type": "ROOT"
  }'
```

> **Ba Chế Độ Sinh Video Veo3 Tự Động:**
> 1. **2 Frames** (Start & End Frame): Nối chuyển động mượt giữa 2 ảnh (RPC `nprQif`).
> 2. **1 Frame** (Start Frame): Sinh video từ ảnh tĩnh đầu vào (RPC `eb1hJf`).
> 3. **0 Frame / Refs**: Sinh video trực tiếp từ prompt và ảnh tham chiếu (RPC `MZZa6b`).

---

### Bước 4: Kiểm Tra & Chỉnh Sửa Phân Cảnh (PATCH)
Nếu muốn đổi câu lệnh trước khi sinh ảnh/video:
```bash
curl -X PATCH http://127.0.0.1:8100/api/scenes/<SID> \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Nội dung prompt ảnh mới...",
    "video_prompt": "Nội dung video prompt mới..."
  }'
```

---

### Bước 5: Đặt Tên Hiển Thị Chuẩn Trên Google Flow (mYWVGd)
Để không bị lộn xộn giữa hàng chục video trên Google Flow, áp dụng cấu trúc:
`[{động tác - góc độ}] {tên nhân vật - số thứ tự}` *(ví dụ: `[bước xuống tàu - 45] Luna - 01`)*

```bash
curl -X POST http://127.0.0.1:8100/api/flow/video/rename \
  -H "Content-Type: application/json" \
  -d '{
    "asset_id": "<MEDIA_ID_HOẶC_OPERATION_ID>",
    "title": "[bước xuống tàu - 45] Luna - 01",
    "project_id": "<PID>"
  }'
```

---

### Bước 6: Kích Hoạt Dự Án Hiện Hành (Active Project)
Để Dashboard UI và các worker nhận diện đúng dự án vừa tạo:
```bash
curl -s -X PUT http://127.0.0.1:8100/api/active-project \
  -H "Content-Type: application/json" \
  -d '{"project_id":"<PID>"}'
```

Xác nhận:
```bash
curl -s http://127.0.0.1:8100/api/active-project
```

🎉 **Hoàn tất!** Bước tiếp theo là chạy `/fk-gen-refs` để sinh ảnh mẫu cho các nhân vật và địa điểm.
