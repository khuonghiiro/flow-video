# Universal Code Modularity & Line Limit Standards

> Quy tắc này tự động áp dụng cho toàn bộ dự án `flow-video` (Flow Kit Core, Agent Veo3, Dashboard UI và Chrome Extension).

## 1. Absolute File Line Limits (Hard Rule)
- **Mục tiêu**: 150 – 500 dòng mỗi file.
- **Ngưỡng tối đa**: **TUYỆT ĐỐI KHÔNG vượt quá 800 – 1.000 dòng trong BẤT KỲ file nào.**
- **Ngôn ngữ áp dụng**: Python (`.py`), TypeScript (`.ts`, `.tsx`), JavaScript (`.js`), CSS (`.css`), JSON (`.json`), Bash/Batch (`.bat`, `.sh`).
- **Hành động bắt buộc**: Khi một file chạm ngưỡng 800 dòng, bạn **PHẢI** phân tách và module hóa thành các sub-module/service nhỏ hơn theo đúng trách nhiệm (Single Responsibility Principle) trước khi thêm code mới.

## 2. Method / Function Size Limit
- Giữ các hàm / method dưới **50 – 80 dòng**.
- Tách các thuật toán phức tạp, vòng lặp lồng nhau hoặc luồng xử lý dài thành private helper functions hoặc pure utility functions.

## 3. Phân Tách Kiến Trúc Theo Từng Lớp Trong Dự Án flow-video

### A. Python Backend (`flowkit/agent/` & `agent-veo3/agent/`)
- **Phân tách các layer rõ ràng**:
  - `models/`: Pydantic schemas cho request/response validation và database models.
  - `api/`: Endpoint route handlers (tách file theo domain: `projects.py`, `scenes.py`, `media.py`, `pipelines.py`, v.v.).
  - `services/`: Business logic, Flow client bridge, worker task runner, post-processing ffmpeg, TTS engine.
  - `db/`: SQLite schema, migration helpers, async CRUD repositories.
  - `utils/`: Helper dùng chung (file I/O, prompt parser, media url helpers).
  - `config.py`: Cấu hình tập trung, hằng số môi trường và model registry.
- **Không bao giờ tạo monolithic `main.py`** chứa toàn bộ routes, models và logic trong một file.
- **Mở rộng Veo3 chuẩn mực**: Không sửa trực tiếp vào mã nguồn `flowkit/` gốc; sử dụng cơ chế non-invasive runtime patching thông qua `flowkit_loader.py` và `extension_patcher.py`.

### B. Dashboard Frontend (`flowkit/dashboard/`)
- **React / Vite / Tailwind**:
  - Tách nhỏ components: mỗi component chịu trách nhiệm một UI widget cụ thể (CharacterCard, SceneTimeline, VideoPlayer, ModelSelector, PromptEditor).
  - Custom Hooks (`src/hooks/`): tách stateful logic (fetching, polling status, websocket connection) ra khỏi render components.
  - Types (`src/types/`): định nghĩa TypeScript interfaces rõ ràng, đồng bộ với Pydantic backend models.
  - Utilities (`src/lib/`, `src/utils/`): format thời gian, resolve media url, api client.

### C. Chrome Extension (`extension/`)
- **Manifest V3**:
  - Tách bạch giữa `background.js` (service worker kết nối WebSocket tới agent), `content.js` (DOM/reCAPTCHA token capture trên Google Flow), và `popup.js` (UI điều khiển trạng thái).
  - Tránh gộp toàn bộ message listener và RPC client vào một file khổng lồ.

## 4. Kiểm Tra Xác Nhận (Verification)
- Trước khi hoàn thành task: Kiểm tra số dòng các file đã sửa/tạo mới để đảm bảo tuân thủ giới hạn.
- Đảm bảo 0 lỗi cú pháp và hệ thống hoạt động trơn tru.
