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
- **Trạng thái:** đã chuyển `CONTEXT.md`, `implementation_plan.md`, `ANIMATION_TUTORIAL.md` và file này vào `docs/`. Riêng `CLAUDE.md` vẫn ở thư mục gốc (đã chốt, xem mục `CLAUDE.md` bên dưới).

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

### Chốt thêm (2026-11-12, lượt 3)
- **Menu khay hệ thống:** sửa lại thành **3 mục: `Hide Pet`/`Show Pet`, `Settings`, `Quit App`** (thay cho quyết định 2 mục ở trên).
- **Hẹn giờ (`set_timer_reminder`):** **tạm tắt** — gỡ khỏi danh sách công cụ của AI cho tới khi user quyết phát triển lại (giữ code để bật lại sau).
- **Chuột trái — bộ phản ứng ngẫu nhiên:** mỗi lần click, pet chọn ngẫu nhiên **một** phản ứng trong bộ; "nói một câu ngẫu nhiên" (từ `data/click_reactions.json`) là **một phản ứng trong bộ**, không đi kèm mọi lần. Bộ gồm **tất cả hoạt ảnh của pet đã có và sẽ có** → khi làm, mỗi hoạt ảnh mới phải tự đăng ký vào bộ này.
- **Idle:** khi pet đang Idle, mục trong menu chuột phải đổi thành **`Wander`** để cho pet đi lại tiếp. Idle có **tư thế nằm nghỉ / ngủ riêng** (hoạt ảnh mới cần vẽ).
- **Bong bóng chat — đếm 30 giây:** **không đếm** khi user đang gõ hoặc khi AI đang trả lời.
- **Bong bóng chat — lịch sử:** cuộn lên để đọc lại tin cũ, chat bao nhiêu cũng được. Không chat trong **15 phút** thì xóa toàn bộ lịch sử (cả phần AI nhớ), không có cách nào lấy lại. Bong bóng tự đóng sau 30 giây **không** xóa lịch sử — mở lại trong vòng 15 phút vẫn thấy tin cũ. (User đề xuất, Claude đồng ý; thay mốc 10 phút cũ trong CONTEXT.md, code vẫn đang 10 phút cho tới khi làm.)
- **Pet hiện ở đâu:** giữ quyết định cũ (2026-08-13) — pet **luôn nổi trên mọi ứng dụng/web**, không chỉ ở desktop.

### Chốt thêm (2026-11-12, lượt 4)
- **Chat:** dùng **bong bóng chat** (khung bo tròn có đuôi chỉ vào pet, dính theo pet, cỡ gọn, cuộn được, tự đóng) **thay hẳn cửa sổ chat** hiện tại.
- **Bộ phản ứng ngẫu nhiên (chuột trái):** **không** gồm mặt cảnh báo (`alert`) và tư thế ngủ (dành cho Idle).
- **Nội dung cửa sổ Settings:** chốt sau.

## Chốt sau (user chủ động để lại)

- Nội dung cửa sổ Settings.
- Hoạt ảnh nâng cao chưa vẽ (E3: tay, củi, chảo trứng…) và tư thế ngủ của Idle (sẽ vẽ khi làm).
- C3 tự khởi động, F đóng gói `.exe`, chat bằng giọng nói, phát triển lại hẹn giờ.

## Còn bàn

- **Ứng dụng toàn màn hình:** có tự ẩn pet khi đang xem phim/chơi game toàn màn hình không.
- **Chuột trái khi đang cảnh báo:** vẫn chỉ tắt cảnh báo như hiện tại (không chơi phản ứng ngẫu nhiên) không.
- **Câu nói tự động sau 15 phút rảnh:** còn giữ không, khi "nói 1 câu" đã nằm trong bộ phản ứng của chuột trái.
- **Câu trả lời ngắn hiện trên bong bóng thoại (B4):** bỏ đi không, vì chat đã là bong bóng gắn với pet.
- **Trong lúc chat:** pet có đứng yên trong khi bong bóng chat đang mở không.
- **Idle gặp sự kiện:** chọn `Chat`, kéo pet, hoặc có cảnh báo khi pet đang ngủ thì pet tỉnh dậy hay ngủ tiếp; xong việc có quay lại ngủ không.
- **E1 — danh sách cảm xúc:** gồm những cảm xúc nào (ngoài `other`).
- **E2 — mốc thời gian:** bao lâu không đụng máy thì ngủ gật; "ban đêm" là từ mấy giờ tới mấy giờ.
- **Ngôn ngữ trả lời trong chat:** AI trả lời theo ngôn ngữ user gõ (tiếng Việt thì đáp tiếng Việt) hay luôn tiếng Anh.
