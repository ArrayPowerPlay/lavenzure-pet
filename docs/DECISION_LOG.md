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

### Chốt thêm (2026-11-12, lượt 5)
- **Chuột trái khi đang cảnh báo:** chỉ tắt cảnh báo như hiện tại, **không** chơi phản ứng ngẫu nhiên.
- **Câu nói tự động sau 15 phút rảnh (fact/joke):** **giữ**, nhưng **không nói khi pet đang ngủ** (Idle hoặc ngủ gật).
- **Câu trả lời ngắn hiện trên bong bóng thoại (B4):** **bỏ**, vì chat đã là bong bóng gắn với pet.
- **Trong lúc chat:** pet **đứng yên** khi bong bóng chat đang mở; đóng chat thì đi lại tiếp.
- **Idle gặp sự kiện:** chọn `Chat`, kéo pet, hoặc có cảnh báo khi pet đang ngủ thì pet **tỉnh dậy**; xong việc thì **quay lại ngủ**.
- **Ngôn ngữ trả lời trong chat:** AI **đáp theo ngôn ngữ user gõ** (gõ tiếng Việt thì đáp tiếng Việt). Các câu pet tự nói (click, fact/joke, cảnh báo) vẫn **tiếng Anh**.
- **Ứng dụng toàn màn hình:** **không** tự ẩn pet. Muốn tắt thì bấm `Hide Pet` trong menu khay hệ thống.

- **E2 — ngủ gật:** pet tự ngủ gật sau **10 phút** không đụng chuột/bàn phím, tự tỉnh khi user dùng máy lại. Khác Idle (Idle do user bảo, nằm tới khi bấm `Wander`).
- **E2 — ban đêm:** từ **20h tối đến 5h sáng** (user chọn, thay đề xuất 22h–6h). Ban đêm chỉ đổi dáng vẻ (lửa dịu, màu trầm, cử động chậm), **không** tự làm pet ngủ. Hai mốc này sau có thể cho chỉnh trong Settings.

### Chốt thêm (2026-11-12, lượt 6) — E1 biểu cảm
Ảnh tham khảo đã chuyển vào `docs/references/`: `calcipher.jpg` (ảnh gốc) và `calcipher_picked.jpg` (user đánh số 7 hình, gạch xanh). Danh sách này thay đề xuất 8 cảm xúc trước của Claude.
- **Vui (`happy`):** thay mặt vui hiện tại bằng **hình 1 và 2**, mỗi lần chọn ngẫu nhiên một mặt. 1 = mắt lim dim liếc ngang, cười mở; 2 = mắt nhìn lên, cười mở.
- **Hoảng hốt (`scared`):** **hình 3** — lửa bùng to, mắt tròn, miệng há rộng.
- **Tức giận (`angry`):** **hình 6**, thêm **lông mày chau xuống**, mắt hơi nheo để không lẫn với hình 3. Tạm thời lửa bùng ra hai bên thay cho tay; **sau này phải làm tay** (ghi ở E3).
- **Chill (`chill`):** **hình 7**, **vẽ cả cái chảo**. Ưu tiên thấp: làm sau các biểu cảm khác.
- **Tư thế bay (FLOAT):** **hình 4** khi bay bình thường, **hình 5** lúc vừa cất cánh ("triệu hồi" khúc củi để bay). Khúc củi được làm sớm, riêng cho lúc bay.
- **Giữ** `surprised`, `thinking` có sẵn. **Bỏ** `sad` và các cảm xúc Claude đề xuất trước đó.
- **Danh sách AI chọn:** `happy`, `scared`, `angry`, `chill`, `surprised`, `thinking`, `other`.
- **Dáng người không cố định:** Calcifer là ngọn lửa biến dạng tùy ý, nên mỗi biểu cảm được tự do đổi hình dáng cơ thể (phình to, bè thành gần hình chữ nhật, kéo dài theo chiều dọc…) sao cho hợp nhất với cảm xúc, không bó buộc vào một khuôn dáng chung.

## Chốt sau (user chủ động để lại)

- Nội dung cửa sổ Settings.
- Hoạt ảnh nâng cao (E3): tay (cần cho mặt `angry`), ôm/gặm củi, trứng… Tư thế ngủ của Idle (sẽ vẽ khi làm).
- C3 tự khởi động, F đóng gói `.exe`, chat bằng giọng nói, phát triển lại hẹn giờ.

## Còn bàn

Claude đề xuất (lượt 7), chờ user chốt trước khi code:
- **Thứ tự làm:** G4 → G3 (bong bóng chat) → G1 + G2 (chuột trái/phải) → E1 (vui, hoảng, giận, bay trên củi + AI chọn cảm xúc) → E2 (tư thế ngủ, ngủ gật, ban đêm) → C1 + menu khay → `chill` + chảo.
- **Tư thế ngủ (dùng chung cho Idle và ngủ gật):** lấy mặt mắt nhắm cười trong ảnh gốc (hàng 4, giữa); lửa lùn xuống, bè ra, thở chậm, thỉnh thoảng bay chữ "z".
- **E1 — biểu cảm giữ bao lâu:** khoảng 5 giây khi câu trả lời hiện ra, rồi về mặt bình thường.
- **Khúc củi lúc bay:** hiện ra kèm tia lửa khi cất cánh, tan thành tàn lửa khi đáp xuống.
- **Cửa sổ Settings (tạm):** chỉ gồm 2 mục đã có số: thời gian ngủ gật, khung giờ ban đêm.
- **Ảnh tham khảo `docs/references/`:** repo GitHub đang **public** và ảnh là tranh của họa sĩ khác (@nyatche) → không đưa lên git, thêm thư mục vào `.gitignore`, chỉ giữ ở máy.
