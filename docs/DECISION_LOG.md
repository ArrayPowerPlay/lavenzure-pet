# DECISION_LOG — Calcifer Desktop Pet

> Nhật ký các quyết định đã chốt giữa user và AI agent, mới nhất ở dưới cùng. Mỗi mục ghi: quyết định, lý do (nếu có), và trạng thái (đã làm / chờ làm / còn bàn).
> Các quyết định kỹ thuật tổng thể từ trước ngày 2026-11-12 nằm trong [CONTEXT.md](./CONTEXT.md) (§3 bảng quyết định, §7 lịch sử thay đổi); file này bắt đầu ghi từ 2026-11-12.
> Kế hoạch theo giai đoạn (A-F) nằm ở cuối [implementation_plan.md](./implementation_plan.md), mục "Kế hoạch tiếp theo".

## 2026-11-12

### Model Gemini cho chat
- **Quyết định:** dùng `gemini-flash-latest` (gọi qua endpoint `v1beta`, khai báo `llm.api_version` trong `config.yaml`).
- **Lý do:** Google đã ngừng `gemini-2.0-flash` (API trả lỗi 404), làm chat hỏng hoàn toàn. `gemini-flash-latest` là tên luôn trỏ tới bản Flash mới nhất, nên không bị hỏng lại khi Google ngừng một bản cụ thể.
- **Trạng thái:** đã làm.

### README hai ngôn ngữ
- **Quyết định:** `README.md` là bản tiếng Anh, `README_vi.md` là bản tiếng Việt, hai bản luôn cập nhật cùng nhau.
- **Trạng thái:** đã làm.

### Vị trí tài liệu
- **Quyết định:** mọi file `.md` ngoài README đều nằm trong `docs/`.
- **Trạng thái:** đã chuyển `CONTEXT.md`, `implementation_plan.md`, `ANIMATION_TUTORIAL.md` và file này vào `docs/`. Riêng `CLAUDE.md` vẫn ở thư mục gốc (đang chờ user quyết, xem mục "Còn bàn").

### Kế hoạch giai đoạn A, B, D, F
- **A — cho app dùng được hằng ngày:** đồng ý. Đã làm A1-A6 (đổi model, báo lỗi dễ hiểu, log ra file, không crash khi thiếu key, công cụ chịu lỗi mạng, chỉ chạy 1 bản). Còn A7: user thử trên desktop thật.
- **B — chat và bong bóng thoại:** đồng ý. Đã làm B1-B5.
- **D — chất lượng code:** đồng ý. Đã làm D1-D4 (pytest, ruff, docstring, dọn tài liệu).
- **F — đóng gói `.exe`:** để sau.

### Giai đoạn C — khay hệ thống
- **C1. Icon khay hệ thống vẽ đúng hình nhân vật:** đồng ý, chờ làm.
- **C2. Thêm mục vào menu chuột phải của icon khay hệ thống:** còn bàn (user hỏi lại ý nghĩa).
- **C3. Bật tự khởi động cùng Windows:** để sau.

### Giai đoạn E — nhân vật sống động hơn
- **E1. Biểu cảm theo nội dung chat:** đồng ý, chờ làm. AI gửi kèm một cảm xúc cho mỗi câu trả lời; có thêm lựa chọn **`other`** cho trường hợp AI không xác định được cảm xúc phù hợp — khi đó pet **không kích hoạt biểu cảm nào** (giữ nguyên nét mặt đang có, chỉ có miệng nói như bình thường).
- **E2. Hành vi theo ngữ cảnh:** đồng ý phần "ngủ gật khi máy không được dùng lâu" và "ban đêm lửa dịu hơn", chờ làm. Phần "gọi thì pet chạy lại gần con trỏ chuột" còn bàn (chưa rõ thế nào là "gọi").
- **E3. Animation nâng cao theo ảnh mẫu (tay, củi, chảo trứng…):** chưa quyết.

### Cách làm việc trong phiên này
- Phiên 2026-11-12 (sau khi xong A, B, D) **chỉ bàn và ghi quyết định**, chưa code C1 / E1 / E2.

## Còn bàn

- **C2:** có thêm các mục "Đứng yên", đổi kích thước/fps, "Mở config.yaml", bật/tắt tự khởi động vào menu của icon khay hệ thống hay không.
- **E2 — "gọi pet":** cách "gọi" là gì (phím tắt toàn cục, bấm icon khay hệ thống, nhắc tên trong chat…), hoặc bỏ hẳn tính năng này.
- **Vị trí `CLAUDE.md`:** Claude Code chỉ tự đọc file này khi nó ở thư mục gốc hoặc trong `.claude/`; chuyển vào `docs/` thì AI agent sẽ không tự đọc nữa.
