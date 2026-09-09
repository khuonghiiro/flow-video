# CRITICAL RULE: Skill Override Hierarchy (OOP Inheritance Model)

> Áp dụng cho toàn bộ quy trình tra cứu, tải và thực thi kỹ năng (`fk-*.md`) trong workspace `flow-video`.

---

## 1. Bản Chất Kế Thừa (OOP Inheritance & Method Overriding)

Hệ thống kỹ năng trong dự án tuân theo mô hình kế thừa hướng đối tượng (Object-Oriented Inheritance):

* **Lớp Cha (Base / Parent Layer) — `flowkit/skills/`**:  
  Chứa các kỹ năng gốc cơ sở từ engine upstream FlowKit. Giữ nguyên bản 100%, không chỉnh sửa.
* **Lớp Con (Override / Derived Layer) — `agent-veo3/skills/`**:  
  Chứa các kỹ năng cải tiến, bổ sung protocol mới (Veo3, F2F chaining, auto-create project, unwatermark, v.v.). Khi có logic mới, lớp con sẽ **ghi đè (Override)** hoàn toàn lớp cha.

---

## 2. Thứ Tự Phân Giải Kỹ Năng (Skill Resolution Order)

Khi Agent hoặc User gọi bất kỳ lệnh/kỹ năng nào dạng `/fk-<name>` hoặc `fk-<name>.md`:

```
┌────────────────────────────────────────────────────────┐
│ Tra cứu 1: agent-veo3/skills/fk-<name>.md              │
│ ➔ NẾU TỒN TẠI: THỰC THI NGAY & BỎ QUA flowkit/skills/ │
└──────────────────────────┬─────────────────────────────┘
                           │ (Nếu KHÔNG tìm thấy)
                           ▼
┌────────────────────────────────────────────────────────┐
│ Tra cứu 2: flowkit/skills/fk-<name>.md                 │
│ ➔ NẾU TỒN TẠI: Thực thi như kỹ năng cơ sở (Base)       │
└──────────────────────────┬─────────────────────────────┘
                           │ (Nếu KHÔNG tìm thấy)
                           ▼
┌────────────────────────────────────────────────────────┐
│ Báo lỗi: Không tìm thấy kỹ năng fk-<name>.md           │
└────────────────────────────────────────────────────────┘
```

### Quy tắc bất di bất dịch:
1. **Ưu tiên tuyệt đối cho `agent-veo3/skills/`:**  
   Nếu một file skill tồn tại ở cả `agent-veo3/skills/fk-xyz.md` và `flowkit/skills/fk-xyz.md`, Agent **PHẢI** đọc và làm theo chỉ dẫn trong `agent-veo3/skills/fk-xyz.md`. Tuyệt đối không đọc hoặc áp dụng chỉ dẫn cũ trong `flowkit/skills/fk-xyz.md`.
2. **Tham chiếu Tiếng Việt (`agent-veo3/skills_vi/`):**  
   Khi người dùng giao tiếp bằng Tiếng Việt hoặc yêu cầu giải thích luồng hoạt động, Agent ưu tiên đối chiếu thêm tài liệu chi tiết tại `agent-veo3/skills_vi/fk-xyz.md`.
3. **Tránh trùng lặp file thừa:**  
   Không sao chép file từ `flowkit/skills/` sang `agent-veo3/skills/` nếu không có thay đổi logic. Chỉ tạo file mới trong `agent-veo3/skills/` khi cần bổ sung tính năng mới hoặc ghi đè (override) hành vi của FlowKit gốc.
