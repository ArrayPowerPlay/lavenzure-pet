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
- **C2. Menu của icon khay hệ thống:** thay bằng quyết định mới bên dưới (mục "Menu khay hệ thống + cửa sổ Settings").
- **C3. Bật tự khởi động cùng Windows:** để sau.

### Giai đoạn E — nhân vật sống động hơn
- **E1. Biểu cảm theo nội dung chat:** đồng ý, chờ làm. AI gửi kèm một cảm xúc cho mỗi câu trả lời; có thêm lựa chọn **`other`** cho trường hợp AI không xác định được cảm xúc phù hợp — khi đó pet **không kích hoạt biểu cảm nào** (giữ nguyên nét mặt đang có, chỉ có miệng nói như bình thường).
- **E2. Hành vi theo ngữ cảnh:** đồng ý phần "ngủ gật khi máy không được dùng lâu" và "ban đêm lửa dịu hơn", chờ làm. Phần "gọi thì pet chạy lại gần con trỏ chuột": **tạm bỏ** (user chốt sau, xem bên dưới).
- **E3. Animation nâng cao theo ảnh mẫu (tay, củi, chảo trứng…):** chưa quyết.

### Cách làm việc trong phiên này
- Phiên 2026-11-12 (sau khi xong A, B, D) **chỉ bàn và ghi quyết định**, chưa code C1 / E1 / E2.

### Menu khay hệ thống + cửa sổ Settings (thay cho C2)
- **Quyết định:** menu chuột phải của icon khay hệ thống chỉ còn **2 mục: `Hide Pet`/`Show Pet` và `Settings`**.
- Bấm `Settings` mở **một cửa sổ nhỏ, đơn giản** để chỉnh cấu hình. **Chỉnh những cấu hình nào: user chưa chốt.**
- **Trạng thái:** chờ làm (sau khi chốt các câu hỏi ở mục "Còn bàn").

### Tương tác chuột với pet
- **Chuột trái vào pet:** pet chơi **một hoạt ảnh ngẫu nhiên** (chọn từ một bộ hoạt ảnh).
- **Chuột phải vào pet:** hiện menu nhỏ có 2 lựa chọn:
  - **`Chat`** — mở **bong bóng chat** cạnh pet để chat. Sau khoảng **30 giây không chat**, bong bóng chat **tự đóng**.
  - **`Idle`** — pet **nằm yên** một chỗ (thôi đi lại / bay / nhảy).
- **Trạng thái:** chờ làm. Thay cho cách cũ (chuột trái = mặt vui + câu thoại ngẫu nhiên; chuột phải = mở thẳng cửa sổ chat).

### Hẹn giờ (`set_timer_reminder`)
- **Quyết định:** chưa phát triển thêm; user sẽ cân nhắc sau.

### "Gọi pet" (một phần của E2)
- **Quyết định:** tạm bỏ.

### `CLAUDE.md`
- **Quyết định:** giữ ở thư mục gốc (ngoại lệ duy nhất của quy tắc "mọi `.md` ngoài README nằm trong `docs/`"), vì Claude Code chỉ tự đọc file này ở thư mục gốc hoặc `.claude/`.

## Còn bàn

- **Settings:** cửa sổ Settings cho chỉnh những cấu hình nào.
- **Thoát app:** menu khay hệ thống không còn `Quit` và `Open Chat` → nút thoát app đặt ở đâu (trong cửa sổ Settings, giữ `Quit` trong menu, hay cách khác)?
- **Hẹn giờ:** công cụ `set_timer_reminder` hiện đã có và đang chạy — giữ nguyên như hiện tại, hay tạm tắt cho tới khi user quyết?
- **Chuột trái:** bộ hoạt ảnh ngẫu nhiên gồm những gì; pet còn nói câu thoại ngẫu nhiên kèm theo không.
- **Idle:** thoát khỏi Idle bằng cách nào (bấm lại mục đó, hay menu đổi thành `Wander`…); "nằm yên" là chỉ đứng yên hay có tư thế nằm/nghỉ riêng.
- **Bong bóng chat:** có thay hẳn cửa sổ chat hiện tại không; mốc 30 giây tính từ lúc nào (tin nhắn cuối / câu trả lời cuối), và có tạm dừng đếm khi đang gõ hoặc khi AI đang trả lời không; lịch sử chat hiển thị thế nào trong bong bóng.
