# Flow Video & Agent Veo3 Coding Standards

> Quy tắc này được tự động áp dụng cho tất cả các phiên AI làm việc trong workspace `flow-video`.

Trước khi sửa code hiện có hoặc tạo code mới, AI phải tuân thủ nghiêm ngặt các quy tắc sau:

## 1. Giới Hạn Kích Thước File & Hàm (Universal Hard Rule)
- **Target size**: 150 – 500 dòng mỗi file.
- **Ngưỡng tối đa**: **Không bao giờ vượt quá 800 – 1.000 dòng**. Nếu file tiến gần 800 dòng, PHẢI tách module nhỏ hơn.
- **Hàm / Method**: Giữ trong khoảng **50 – 80 dòng**. Tách các bước dài thành helper functions chuyên biệt.

## 2. Quy Chuẩn Google Flow API & Media ID
1. **Media ID luôn là định dạng UUID**:
   - Định dạng chuẩn: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (36 ký tự).
   - Tuyệt đối không dùng chuỗi mã hóa base64 `CAMS...` làm `media_id`. Nếu API trả về URL chứa `fifeUrl`, hãy trích xuất UUID từ đường dẫn `/image/{UUID}` hoặc `/media/{UUID}`.
2. **Prompt Cảnh Phim (Scene Prompts)**:
   - **Chỉ mô tả HÀNH ĐỘNG (ACTION only)**: góc quay máy, ánh sáng, chuyển động cơ thể, môi trường tương tác.
   - **KHÔNG mô tả lại ngoại hình nhân vật** trong prompt cảnh. Ngoại hình được đồng bộ tự động thông qua `imageInputs` / reference images của character/entity.
3. **Thứ tự sinh Media**:
   - Tất cả Entity/Character reference images phải được sinh và có `media_id` hợp lệ trước khi sinh ảnh cảnh (scene images).
   - Entity là Nhân vật (character) dùng tỷ lệ PORTRAIT (dọc), Địa điểm (location) dùng LANDSCAPE (ngang).
4. **Cấu trúc Video Prompt theo Sub-clip Timing**:
   - Video 4s/6s/8s (Veo 2 / Veo 3) cần chia mốc thời gian rõ ràng:
     `0-3s: [mô tả hành động]. 3-6s: [mô tả chuyển động máy]. 6-8s: [kết thúc cảnh].`
   - Lời thoại nhân vật đặt trong dấu ngoặc kép: `Luna nói "Chào buổi sáng."`. Tối đa 10-15 từ mỗi phân đoạn 2-3 giây.

## 3. Kiến Trúc Backend (Python FastAPI + SQLite)
1. **Giao tiếp Agent ↔ Extension**:
   - Agent chạy WebSocket server tại `localhost:9222` (do MV3 Service Worker không thể làm WS server).
   - Chrome Extension tự động kết nối vào `localhost:9222` và giải mã token/reCAPTCHA.
   - Pre-flight check bắt buộc: `GET /health` phải trả về `extension_connected: true`.
2. **Thao tác Database an toàn**:
   - Luôn sử dụng connection với `PRAGMA busy_timeout=30000` để tránh lỗi database lock khi có nhiều tiến trình song song.
   - Mọi thao tác ghi DB phải thông qua async CRUD service, hỗ trợ upsert an toàn khi trùng `id`.
3. **Throttling & Batch API**:
   - Không tự viết script chạy vòng lặp gửi request dồn dập.
   - Sử dụng `POST /api/requests/batch` để gửi tác vụ, worker backend sẽ tự động throttle tối đa 5 requests đồng thời và 10 giây cooldown chống spam.
   - Kiểm tra trạng thái bằng `GET /api/requests/batch-status`.

## 4. Nguyên Tắc Tích Hợp Agent-Veo3 & FlowKit
- `flowkit/` là core engine gốc từ upstream.
- `agent-veo3/` chứa các mở rộng nâng cấp (Custom Veo3 durations 4s/6s/8s, FlowClient patches, custom routes).
- Luôn giữ tính nguyên vẹn của FlowKit core, áp dụng kỹ thuật **Non-invasive Runtime Patching** thông qua `agent-veo3/agent/flowkit_loader.py` và `extension_patcher.py`.

## 5. Tài Liệu Tham Khảo Trong Workspace
- Kiến trúc tổng thể: [flowkit/ARCHITECTURE.md](file:///e:/UngDung_PC/flow-video/flowkit/ARCHITECTURE.md)
- Kế hoạch & Endpoints: [agent-veo3/PLAN.md](file:///e:/UngDung_PC/flow-video/agent-veo3/PLAN.md)
- Bộ lệnh AI Skill: [flowkit/GEMINI.md](file:///e:/UngDung_PC/flow-video/flowkit/GEMINI.md)
