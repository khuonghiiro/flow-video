# Universal AI Workflow & Execution Guidelines

> Áp dụng cho toàn bộ dự án `flow-video` (gồm FlowKit Core, Agent Veo3, Dashboard UI và Extension).

## 1. Tối Ưu Tốc Độ Thực Hiện (Speed Optimization)
- **Thực hiện trực tiếp, không tạo Plan thừa**:
  - Đối với các yêu cầu sửa bug, sửa file batch, tối ưu logic, tinh chỉnh giao diện, thêm tính năng cục bộ: **Sửa và cập nhật file trực tiếp ngay lập tức**.
  - **KHÔNG** kích hoạt Planning mode tạo `implementation_plan.md` làm chậm dòng tương tác, trừ khi người dùng yêu cầu lập kế hoạch trước hoặc tái cấu trúc quy mô lớn.
- **Phản hồi súc tích, đi thẳng vào vấn đề**:
  - Tập trung vào nội dung thay đổi, kết quả xác minh thực tế, không viết văn giải thích rườm rà.

## 2. Độ Chính Xác & Bảo Toàn Mã Nguồn
- Luôn đọc nội dung file trước khi sửa để nắm đúng ngữ cảnh và cấu trúc hiện tại.
- Bảo toàn comment, kiểu dữ liệu, các hàm tiện ích và logic đang hoạt động ổn định.
- Chạy lệnh xác minh sau khi sửa đổi để đảm bảo không phát sinh lỗi cú pháp hay lỗi khởi chạy.
