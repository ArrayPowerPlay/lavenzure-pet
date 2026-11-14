# DECISION_LOG — Lavenzure Desktop Pet

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
- **C1. Icon khay hệ thống vẽ đúng hình nhân vật:** đồng ý, **đã làm** (chờ user duyệt).
- **C2. Menu của icon khay hệ thống:** thay bằng quyết định mới bên dưới (mục "Menu khay hệ thống + cửa sổ Settings").
- **C3. Bật tự khởi động cùng Windows:** để sau.

### Giai đoạn E — nhân vật sống động hơn
- **E1. Biểu cảm theo nội dung chat:** đồng ý, **đã làm** (chờ user duyệt). AI gửi kèm một cảm xúc cho mỗi câu trả lời; có thêm lựa chọn **`other`** cho trường hợp AI không xác định được cảm xúc phù hợp — khi đó pet **không kích hoạt biểu cảm nào** (giữ nguyên nét mặt đang có, chỉ có miệng nói như bình thường).
- **E2. Hành vi theo ngữ cảnh:** đồng ý phần "ngủ gật khi máy không được dùng lâu" và "ban đêm lửa dịu hơn", **đã làm** (chờ user duyệt). Phần "gọi thì pet chạy lại gần con trỏ chuột": **tạm bỏ** (user chốt sau, xem bên dưới).
- **E3. Animation nâng cao theo ảnh mẫu (tay, củi, chảo trứng…):** chưa quyết.

### Cách làm việc trong phiên này
- Phiên 2026-11-12 (sau khi xong A, B, D) **chỉ bàn và ghi quyết định**, chưa code C1 / E1 / E2.

### Menu khay hệ thống + cửa sổ Settings (thay cho C2)
- **Quyết định:** menu chuột phải của icon khay hệ thống chỉ còn **2 mục: `Hide Pet`/`Show Pet` và `Settings`**.
- Bấm `Settings` mở **một cửa sổ nhỏ, đơn giản** để chỉnh cấu hình. **Chỉnh những cấu hình nào: user chưa chốt.**
- **Trạng thái:** **đã làm** theo bản 3 mục ở lượt 5 (`Hide/Show Pet`, `Settings` trống, `Quit App`); chờ user duyệt.

### Tương tác chuột với pet
- **Chuột trái vào pet:** pet chơi **một hoạt ảnh ngẫu nhiên** (chọn từ một bộ hoạt ảnh).
- **Chuột phải vào pet:** hiện menu nhỏ có 2 lựa chọn:
  - **`Chat`** — mở **bong bóng chat** cạnh pet để chat. Sau khoảng **30 giây không chat**, bong bóng chat **tự đóng**.
  - **`Idle`** — pet **nằm yên** một chỗ (thôi đi lại / bay / nhảy).
- **Trạng thái:** **đã làm** (chờ user duyệt). Thay cho cách cũ (chuột trái = mặt vui + câu thoại ngẫu nhiên; chuột phải = mở thẳng cửa sổ chat).

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
- **Dáng người không cố định:** Lavenzure là ngọn lửa biến dạng tùy ý, nên mỗi biểu cảm được tự do đổi hình dáng cơ thể (phình to, bè thành gần hình chữ nhật, kéo dài theo chiều dọc…) sao cho hợp nhất với cảm xúc, không bó buộc vào một khuôn dáng chung.

## Chốt sau (user chủ động để lại)

- Nội dung cửa sổ Settings.
- Hoạt ảnh nâng cao (E3): tay (cần cho mặt `angry`), ôm/gặm củi, trứng… Tư thế ngủ của Idle (sẽ vẽ khi làm).
- C3 tự khởi động, F đóng gói `.exe`, chat bằng giọng nói, phát triển lại hẹn giờ.

### Chốt thêm (2026-11-12, lượt 7) — trước khi code
- **Thứ tự làm:** G4 (tắt hẹn giờ) → G3 (bong bóng chat) → G1 + G2 (chuột trái/phải) → E1 (vui, hoảng, giận, bay trên củi + AI chọn cảm xúc) → E2 (tư thế ngủ, ngủ gật, ban đêm) → C1 + menu khay → `chill` + chảo.
- **Tư thế ngủ (dùng chung cho Idle và ngủ gật):** mặt mắt nhắm cười trong ảnh gốc (hàng 4, giữa); lửa lùn xuống, bè ra, thở chậm, thỉnh thoảng bay chữ "z".
- **E1 — biểu cảm giữ bao lâu:** khoảng 5 giây khi câu trả lời hiện ra, rồi về mặt bình thường.
- **Khúc củi lúc bay:** hiện ra kèm tia lửa khi cất cánh, tan thành tàn lửa khi đáp xuống.
- **Cửa sổ Settings:** **tạm để trống** (mục `Settings` trong menu khay vẫn có, nội dung chốt sau).
- **Ảnh tham khảo `docs/references/`:** **không đưa lên git** (repo public, ảnh là tranh của họa sĩ khác @nyatche); thư mục nằm trong `.gitignore`, chỉ giữ ở máy.

### Kết quả lượt 8 (2026-11-12) — đã code xong lượt 7, chờ user duyệt
- Đã làm: G4, G3, G1 + G2, E1, E2, C1 + menu khay, `chill` + chảo (từng phần một commit).
- **Biểu cảm bám theo ảnh user chọn** (`calcipher_picked.jpg`, user nhắc lại trong phiên): vui hình 1 (mắt lim dim liếc ngang, cười há) và hình 2 (mắt đảo lên một bên, cười há chữ D); hoảng hình 3 (lửa bè gần vuông, viền tua tủa, mắt to tròn tách xa, miệng há rất to); giận hình 6 (hai tay lửa mềm chìa ngang rồi cong lên thành nắm đấm) + lông mày chau, mắt nheo; bay hình 4 (bám khúc củi bằng hai tay nhỏ); cất cánh hình 5 (mắt tròn, miệng há); `chill` hình 7 (lửa bẹt, chảo rộng bằng thân đè trên đầu, mắt lim dim liếc ngang, miệng lượn sóng).
- **Claude tự quyết (user có thể đổi):** đang ngủ mà click trái thì pet tỉnh, chơi một phản ứng rồi ngủ lại; phản ứng không bao giờ lặp lại hai lần liền; khi pet đang bay (trên không) thì phản ứng vẫn chơi trên khúc củi; chọn `Idle` lúc đang bay thì pet lượn xuống đất (tối đa ~3 giây) rồi mới ngủ.

### Lượt 9 (2026-11-12) — user góp ý 7 điểm, đã sửa, chờ duyệt
- **Mặt bình thường:** miệng chuyển sang "ồ" giờ **biến hình liền một nét** (không còn mờ / chồng hai miệng); chữ "o" tròn thật.
- **Vui:** miệng bo tròn như hình 1 / 2 và **luôn nằm dưới mắt, có khoảng hở** (áp dụng cho mọi biểu cảm; riêng chỗ giữa hai mắt thì vòm miệng được nhô lên cao hơn, như hình 3).
- **Hoảng:** lửa tua tủa bằng các lưỡi lửa liền khối **bốc dần lên trên** (cao nhất ở hai góc đỉnh), không còn vệt cắt dọc / mảnh lửa rời; miệng vòm cung to, có cổ họng và lưỡi.
- **Giận:** theo ảnh a2 — **bỏ lông mày rời**, mí trên cắt chéo đậm (chính nó là lông mày), con ngươi trừng lên từ góc trong, miệng nhỏ có chóp nhọn; mắt miệng cách nhau rõ.
- **Chill:** mí phẳng lim dim, con ngươi liếc ngang, miệng cười lượn sóng dài; **chảo nằm trong ngọn lửa**: mép lửa trùm lên đáy chảo, lưỡi lửa liếm lên hai bên, thành chảo đỏ rực nóng; hơi nước / mỡ bắn vẫn bay phía trước.
- **Ngủ:** các thông số mặt chuyển kiểu "tăng tốc rồi giảm tốc" (không giật ngay khung đầu); lúc thiu thiu ngủ mí mắt sụp và mặt giãn ra chậm.
- **Bay trên củi:** hai tay là **một cục tròn** (như tay Doraemon), mọc ra từ thân, phủ lên mặt trước khúc củi; bỏ vạch ngón.

### Lượt 10 (2026-11-12) — user góp ý 8 điểm + thêm hình 8, đã sửa, chờ duyệt
- **Chill (hình 7):** mắt hình hạt chanh, mí trên cong vòm, con ngươi nép dưới mí liếc ngang; miệng cười dài, hai khóe cuộn lên thành móc nhỏ (một nét liền). **Chảo đặt lên đầu, vẽ phía trước lửa**: đáy chảo nằm ngay trên mắt, chảo hơi nghiêng, cán chúc xuống một bên, lửa lộ ra hai bên và phía sau; chảo rơi xuống rồi đứng yên (không nảy đè lên mắt).
- **Chill không đi cùng khúc củi:** đang bay trên củi mà gặp `chill` thì hiện mặt vui thay; click ngẫu nhiên lúc đang bay không chọn `chill`.
- **Lửa của hoảng / chill:** lưỡi lửa hai bên chỉ mọc ở nửa trên thân và luôn uốn hướng lên; bỏ các cục nhọn chĩa ngang.
- **Trên khúc củi:** mặt nhích lên, miệng không bao giờ xuống quá một mức cố định; hai tay tròn dời ra hai bên → tay không che miệng.
- **Giận (hình 6):** miệng há rộng và cao, bo tròn; mắt nhìn thẳng phía trước, mắt đặt cao hơn để có chỗ cho miệng. Tay lửa là một đường cong mềm thuôn dần, nắm đấm tròn, lõi vàng; hết vệt cung lạ trong nắm đấm.
- **Vui:** không nhảy nữa (chỉ tia lửa + bùng lửa). Mặt 1 theo hình 1: mắt cong vòm, con ngươi nép dưới mí, bỏ nét ngang giống lông mày.
- **Ngủ:** không chớp mắt khi đang ngáp / ngủ → mắt chỉ nhắm một lần rồi ngủ luôn. Mắt nhắm là **một nét duy nhất** uốn dần từ mí nhắm sang vòng cung "^", không chồng hai hình.
- **Hình 8 — biểu cảm mới `yuck`:** hai mắt lệch nhau (một mắt nheo dưới mí chéo, mắt kia to, méo hình quả trứng, hơi nghiêng; hai con ngươi chụm vào giữa), miệng há méo lượn sóng, lưỡi thè ra ở một khóe. Mỗi lần chơi ngẫu nhiên lật trái/phải. Có trong bộ phản ứng khi click trái và nút "Yuck" trong `character_preview.py`.
- **Claude tự quyết (user có thể đổi):** `yuck` **chưa** thêm vào danh sách cảm xúc AI chọn khi chat; **chưa vẽ vỏ trứng** trong miệng (chỉ lưỡi thè).

### Lượt 11 (2026-11-12) — user góp ý 5 điểm sau lượt 10, đã sửa, chờ duyệt
- **Vui (hình 1):** mắt thành **một hình hạt hạnh nhân** liền nét (mép trên cong thấp, đáy tròn, hai khóe nhọn), con ngươi treo dưới mép trên; miệng là hình bầu dục bo tròn, bỏ chỗ lõm giữa môi trên.
- **Khoảng cách mắt – miệng:** miệng luôn cách mắt xa hơn trước (áp dụng cho mọi biểu cảm, gồm vui và ngáp / ngủ).
- **Chill (hình 7):** cùng kiểu mắt hạnh nhân; miệng là **một đường cong nhẹ liền nét**, hai đầu cuộn lên thành móc nhỏ (bỏ kiểu đáy phẳng gãy góc).
- **Ngồi trên khúc gỗ:** hai tay giờ **là một phần của ngọn lửa** (vẽ trong shader): đáy thân đặt phẳng lên khúc gỗ (khúc gỗ vẽ phía sau lửa), tay mọc ra từ thân với cùng viền đỏ, dải cam, lõi vàng → liền một khối, không còn viền chèn lên dải màu. Bộ vẽ dự phòng (`metaball` / `baked`) vẫn dùng tay vẽ riêng như cũ.
- **Giận:** **bỏ hẳn tay** (xóa cả phần code tay trong shader).

### Lượt 12 (2026-11-12) — user góp ý 4 điểm + 1 nhắc thêm, đã sửa, chờ duyệt
- **`yuck` vào danh sách cảm xúc AI chọn** (user trả lời câu hỏi lượt 10/11): AI giờ chọn được `[yuck]` (ghê / kinh / dở tệ). **Không vẽ vỏ trứng** trong miệng.
- **Ngủ không nhìn theo chuột:** lúc ngáp / ngủ (cả Idle lẫn ngủ gật) mặt và mắt không dõi theo con trỏ nữa, từ từ quay về nhìn thẳng.
- **Vui hình 1 và chill hình 7 — chép y hệt ảnh mẫu, không tự chế:** mắt và miệng của hai biểu cảm này được **dò lại (trace) từ chính ảnh `calcipher_picked.jpg`** rồi lưu thành dữ liệu (`src/overlay/face_refs.py`), không còn ước lượng bằng tham số. Mặt chuyển dần (morph) từ mặt thường sang mặt chép, vẫn chớp mắt được. Vui hình 1: mắt nửa vòm đáy phẳng, con ngươi dài treo dưới mép trên liếc phải; miệng mở có **chỗ lõm nhẹ giữa môi trên** đúng như hình (thay quyết định "bỏ chỗ lõm" ở lượt 11), lưỡi hồng nửa dưới. Chill hình 7: mặt nghiêng (bên phải cao hơn), mắt nửa vòm con ngươi to liếc phải, miệng một nét lượn sóng dài, mỗi khóe có một nét ngắn cắt ngang (lúm má).
- **Claude tự quyết (user có thể đổi):** hai mặt chép **không lật trái/phải** ngẫu nhiên nữa (để giống y ảnh); mặt vui hình 2 giữ nguyên (vẫn chọn ngẫu nhiên hình 1 / hình 2); khi đang nói, miệng chép của vui khép mở theo lời, miệng chill (đang khép) thì tạm mở ra như miệng nói thường.
- **Tay trên khúc gỗ theo hình 4:** thân ngồi đè lên khúc gỗ (nửa dưới bè rộng ra như có sức nặng), mép dưới thân phủ nhẹ xuống mặt trước khúc gỗ, hai tay là hai thùy tròn của chính thân đó buông xuống. Phần đè lên gỗ **toàn màu vàng tới tận viền** (hết dải cam / đỏ quanh tay và vệt cam ngang đáy), dải đỏ / cam hai bên thân chạy xuống tới khúc gỗ như hình 4.

### Lượt 13 (2026-11-12) — user duyệt hoạt ảnh lượt 12; làm README, A7 và hiệu năng
- **User duyệt hoạt ảnh** ("khá đẹp và ưng ý") → chuyển sang A7 (thử trên desktop thật) và Phase 12 (hiệu năng).
- **README** (cả hai bản): đầu trang là ảnh pet cắt từ khung hình thật của bộ vẽ shader (`docs/images/hero.png`), thêm dải biểu cảm (`docs/images/expressions.png`) và mục giới thiệu hoạt ảnh. Ảnh do code của repo tự vẽ, không dùng ảnh tham khảo của họa sĩ khác.
- **A7:** checklist ở `docs/TEST_CHECKLIST.md`; phần tự kiểm bằng `src/desktop_check.py` đã PASS.
- **Hiệu năng — Claude tự quyết (không đổi hình ảnh):** numpy chỉ dùng 1 luồng OpenBLAS (trước đó giữ sẵn ~490 MB RAM); đọc ảnh lửa từ GPU qua 2 bộ đệm PBO, ảnh lửa trễ 1 khung (~16 ms, mắt không thấy), hình giống hệt từng pixel.
- **Chat chậm (user hỏi, 2026-11-13):** API và mạng ổn (ping ~0,09 giây, không lỗi, không gọi lại). Nguyên nhân: `gemini-flash-latest` giờ là gemini-3.8-flash, bản Flash đầy đủ luôn "suy nghĩ" (~180-260 token) → 2,7-5,4 giây mỗi lần gọi, câu cần công cụ gọi 2 lần → 4-8 giây. **User chọn:** đổi sang **`gemini-flash-lite-latest`** (1,4-3,7 giây/câu) và **làm streaming luôn** (chữ hiện dần, mặt cảm xúc hiện ngay khi thẻ cảm xúc tới).
- **Claude tự quyết (user có thể đổi):** nếu model viết vài chữ rồi mới gọi công cụ, phần chữ đó bị thay bằng câu trả lời sau; nếu lỗi giữa chừng, phần chữ đã hiện vẫn giữ và câu báo lỗi hiện bên dưới; miệng pet nhép liên tục khi chữ đang tới.
- **Sửa lỗi có sẵn (phát hiện khi thử streaming):** câu trả lời của AI trước giờ được xử lý ở luồng phụ của agent chứ không phải luồng giao diện (vì `LavenzureApp` không phải `QObject`, PySide gọi thẳng hàm trong luồng phụ) → có thể làm app crash ngẫu nhiên khi chat. Giờ `LavenzureApp` là `QObject`, các hàm nhận câu trả lời là `@Slot` nối kiểu queued → luôn chạy ở luồng giao diện (đã thử 3 câu hỏi trên app thật).
- **Mục tiêu hiệu năng đề xuất** (user có thể đổi): CPU dưới 2% cả máy, GPU dưới 10%, RAM dưới 250 MB, không tăng dần theo giờ, ~60 fps.

### Lượt 14 (2026-11-13) — giảm CPU / GPU
- **Đo 60 phút sau tối ưu lượt 13:** CPU 3-4% cả máy, GPU 12-13%, RAM ~220 MB không tăng → vẫn trên mục tiêu CPU/GPU. Claude đưa 5 cách, **user chọn:**
  1. **Làm luôn** cách 1 (bớt tính toán thừa, không đổi hình ảnh).
  2. Cách 2 (tốc độ khung hình tự đổi) và cách 4 (lửa độ phân giải thấp) **thành chế độ bật/tắt** để user tự thử từng tổ hợp rồi duyệt.
  3. Cách 3 (tạm dừng khi có app toàn màn hình) và cách 5 (lửa 30 khung/giây, chuyển động 60) **chưa làm**.
- **Cách 1 (đã làm):** giá trị biểu cảm đã tới đích thì dừng tính; hình học mắt (bị hỏi 6 lần mỗi khung) tính 1 lần; môi, vùng an toàn, viền mắt chép tính bằng numpy; ngữ cảnh OpenGL giữ nguyên giữa các khung; mép trên ngọn lửa (chỗ sinh tàn lửa) chỉ đọc 1/3 số cột. Ảnh vẽ từng khung so với trước giống hệt (chỉ lệch dưới 1 pixel / vị trí tàn lửa ngẫu nhiên). Đo thử: ~8,5 → ~7,2 ms/khung.
- **Claude tự quyết (user có thể đổi):** hai chế độ nằm trong **cửa sổ Settings** (khay → `Settings`), bật/tắt có hiệu lực ngay, kèm dòng hiển thị số khung/giây đang vẽ và lý do (đang di chuyển / đứng yên / ngủ). Lựa chọn được nhớ trong `%LOCALAPPDATA%\Lavenzure\settings.json`; mặc định (cả hai tắt) nằm ở `config.yaml` mục `performance`. "Tốc độ tự đổi": 60 fps khi đi / bay / nhảy / bị kéo / đang phản ứng (click, cảm xúc AI) / đang nói; 30 fps khi đứng yên; 15 fps khi ngủ (số chỉnh trong `config.yaml`). "Lửa nhẹ": độ phân giải lửa 1,5 thay vì 2,0 (~56% số điểm ảnh).
- **Đo nhanh trên app thật** (mỗi tổ hợp 60 giây, pet chủ yếu đứng yên; máy 16 luồng): tắt cả hai 3,2% CPU / GPU 12%; tốc độ tự đổi 2,0%; lửa nhẹ 2,9%; cả hai 1,7%.

### Lượt 15 (2026-11-13) — user chốt lửa nhẹ, thử 45 / 30 fps
- **User chốt "lửa nhẹ"** → `performance.lite_flame: true` (luôn bật; theo yêu cầu user, ô bật/tắt "Lite flame" đã **bỏ khỏi Settings** vì đã là mặc định — muốn tắt thì sửa `config.yaml`).
- **User muốn thử 30 fps và 45 fps cho mọi hoạt ảnh** → Settings có thêm mục **Frame rate: 60 / 45 / 30 fps** (giới hạn số khung/giây cho mọi hoạt ảnh, bật ngay, được nhớ; mặc định = `character.fps` 60).
- **Claude tự quyết (user có thể đổi):** chế độ "tốc độ tự đổi" vẫn giữ để thử kèm, mức đứng yên / ngủ không bao giờ vượt giới hạn đã chọn. Màn hình 60 Hz chỉ hiện được khung ở mỗi lần làm mới (16,7 ms), nên 45 fps = vẽ 3 lần trong mỗi 4 lần làm mới → nhịp không đều tuyệt đối (16,7 / 16,7 / 33,3 ms), có thể thấy hơi lắc nhẹ khi pet di chuyển; 30 fps thì đều.

### Lượt 16 (2026-11-13) — user chốt 30 fps
- **User chốt 30 fps mặc định** cho mọi hoạt ảnh (`character.fps: 30`); Settings vẫn cho chọn **45 / 60**. Settings giờ chỉ còn mục Frame rate (thứ tự 30 / 45 / 60).
- **Bỏ chế độ "tốc độ khung hình tự đổi"** (ô Adaptive trong Settings và toàn bộ code của nó: mức đứng yên / ngủ, `calm_fps`, `sleep_fps`).
- **User hỏi 45 fps có phổ biến không:** không. Các mức hay dùng: 24 (phim), 25 / 50 (TV châu Âu), 30 / 60 (video, game, màn hình 60 Hz), 120 / 144 (màn hình tần số cao). Màn hình 60 Hz chỉ hiện đều các mức chia hết 60 (60, 30, 20, 15); 45 phải vẽ 3 lần bỏ 1 lần nên nhịp không đều. **Claude tự quyết (user có thể đổi):** vẫn giữ nút 45 vì user muốn có; nếu muốn thay bằng mức khác thì báo.

### Lượt 17 (2026-11-13) — bỏ mức 45 fps
- **User yêu cầu bỏ mốc 45 fps** trong code và Settings; chỉ giữ **30 và 60**. Settings Frame rate giờ có 2 nút: 30 (mặc định) / 60.
- **Claude tự quyết (user có thể đổi):** nếu file settings cũ lưu 45 thì app tự chuyển về mức gần nhất còn lại (30 hoặc 60) khi mở. `FramePacer` giữ nguyên (vẫn giúp nhịp đều khi timer lệch nhẹ), chỉ bỏ phần mô tả riêng cho 45 fps.

### Lượt 18 (2026-11-14) — cảnh báo bớt phiền, Hide Pet ở chuột phải, khung tin nhắn
- **Lý do:** RAM máy user thường ở ~93% (Chrome, WSL, WebView2, phần mềm Dell, VNPT Threat Protection…; pet chỉ ~0,3 GB). Click tắt cảnh báo thì 45 giây sau pet báo lại, nên báo liên tục.
- **User chốt:** click tắt cảnh báo → pet **im 10 phút** rồi mới báo lại nếu vẫn quá ngưỡng (`system_status.snooze_minutes: 10`, áp cho cả CPU / RAM / pin).
- **User chốt:** đang cảnh báo mà chọn `Idle` → tắt cảnh báo (cũng im 10 phút) và pet đi ngủ luôn.
- **User chốt:** thêm **`Hide Pet`** vào menu chuột phải của pet (không cần vào icon khay); hiện lại bằng icon khay → `Show Pet`.
- **User chốt:** trong bong bóng chat, **mỗi tin nhắn có khung bo tròn riêng**. **Claude tự quyết (user có thể đổi):** tin của user bên phải, nền cam nhạt viền cam; tin của pet bên trái, nền trắng viền đỏ nâu; khung ôm vừa chữ.
- **Claude tự quyết (user có thể đổi):** hết 10 phút mà pet đang ngủ (Idle) và máy vẫn quá ngưỡng thì cảnh báo vẫn đánh thức pet như trước.

### Lượt 19 (2026-11-14) — chọn cải tiến, lập TASKS.md
- Claude đề xuất 8 cải tiến; **user chỉ thấy 2 mục đáng làm:** nhắc việc + Pomodoro, kéo file thả vào pet. Cả hai **pending**: chỉ làm khi user chốt.
- Lập **`docs/TASKS.md`** (danh sách việc cần làm: pending / nghiên cứu / không chọn).
- User hỏi về tương tác với icon desktop và thành phần trong app / web → Claude thử thật (chỉ đọc) và ghi 7 hướng (N1-N7) kèm độ khả thi vào `TASKS.md`; chờ user chọn.

### Lượt 20 (2026-11-14) — câu quan tâm mỗi 5 phút, Pomodoro, biểu cảm cool (CHƯA CODE)

> User yêu cầu ghi lại, **chưa code**. Các chi tiết ghi "Claude đề xuất" là gợi ý, chờ user chốt.

#### 1. Câu quan tâm mỗi 5 phút
- **User chốt ý tưởng:** cứ **5 phút** pet nói 1 câu quan tâm tới user (nhắc ngủ sớm, hỏi ăn sáng chưa, hỏi ngày hôm nay thế nào, mong sự xuất hiện của pet sưởi ấm trái tim user…). Có **khoảng 20 câu tiếng Anh + 20 câu tiếng Việt**; ngôn ngữ theo mục **Language** trong Settings.
- **Hiện trạng:** Settings hiện **chưa có mục Language** (chỉ có Frame rate) → phải thêm mục này: `English` / `Tiếng Việt`. Quy tắc "mọi câu pet nói trên màn hình là tiếng Anh" trong `CLAUDE.md` sẽ phải sửa khi làm.
- **Claude đề xuất cách chạy:**
  - Câu nằm trong file dữ liệu `data/care_lines.json` (mỗi ngôn ngữ một danh sách), sửa câu không cần đụng code. Chu kỳ chỉnh trong `config.yaml` (`care_lines.interval_minutes: 5`).
  - Một số câu **chỉ hợp vài giờ trong ngày** (hỏi ăn sáng chỉ buổi sáng, nhắc ngủ chỉ buổi tối / khuya) → mỗi câu có khung giờ, tới lượt thì chỉ bốc trong các câu hợp giờ.
  - Bốc kiểu "xáo bài": nói hết các câu hợp giờ rồi mới lặp lại, không bao giờ nói 2 lần liền một câu. Lưu ý: 5 phút/câu = 12 câu/giờ, nên với 20 câu thì **khoảng 1,5 giờ là bắt đầu lặp** — muốn ít lặp thì thêm câu hoặc giãn chu kỳ.
  - **Không nói khi:** pet đang ngủ / user đi vắng (không có ai đọc), đang có cảnh báo, đang mở bong bóng chat, đang trong giờ tập trung Pomodoro. Bị bỏ qua thì đếm lại 5 phút từ lúc rảnh.
  - Bong bóng tự tắt sau ~8 giây; pet làm mặt `happy` hoặc `chill` khi nói.
- **Cần chốt trước khi làm:**
  - Language chỉ đổi câu quan tâm, hay đổi **mọi câu pet nói** (phản ứng khi click, fact/joke, cảnh báo, nhắc việc)? Claude đề xuất: đổi tất cả cho thống nhất (khi đó phải dịch thêm các file câu có sẵn). Chat với AI vẫn trả lời theo ngôn ngữ user gõ như hiện nay.
  - Giữ hay bỏ **fact/joke khi rảnh 15 phút** đang có (dễ chồng lên câu quan tâm)? Claude đề xuất: gộp chung một nhịp — mỗi 5 phút bốc câu quan tâm là chính, thỉnh thoảng (vd 1/4) thay bằng fact/joke.
  - Có cho tắt / chỉnh chu kỳ trong Settings không, hay chỉ trong `config.yaml`?
- **Danh sách câu (Claude soạn, user sửa thoải mái).** Khung giờ: *sáng* 5-10h, *trưa* 11-13h, *tối* 17-20h, *đêm* 22-4h, *chiều tối* 18-23h; không ghi = lúc nào cũng được.

| # | English | Tiếng Việt | Khung giờ |
|---|---|---|---|
| 1 | Good morning! Let's make today a good one. | Chào buổi sáng! Hôm nay cùng cố lên nhé. | sáng |
| 2 | Have you had breakfast yet? Don't skip it! | Bạn ăn sáng chưa đó? Đừng bỏ bữa nha! | sáng |
| 3 | Lunch time soon. Eat something warm, okay? | Sắp trưa rồi, nhớ ăn gì đó cho ấm bụng nhé. | trưa |
| 4 | Dinner time! Did you eat yet? | Tới giờ ăn tối rồi, bạn ăn chưa? | tối |
| 5 | It's getting late. Try to sleep early tonight, okay? | Khuya rồi đó, tối nay ngủ sớm chút nha. | đêm |
| 6 | Still up? Your bed misses you. Go get some sleep! | Vẫn còn thức à? Đi ngủ thôi, mai còn có sức nè. | đêm |
| 7 | Rough day? Be kind to yourself tonight. | Hôm nay mệt hả? Tối nay nhớ thương bản thân một chút nha. | chiều tối |
| 8 | How's your day going so far? | Hôm nay của bạn thế nào rồi? | |
| 9 | Take a sip of water. I'll wait! | Uống một ngụm nước đi, mình đợi nè! | |
| 10 | Give your eyes a break. Look at something far away for 20 seconds. | Cho mắt nghỉ chút đi: nhìn ra xa 20 giây nhé. | |
| 11 | Stretch your shoulders a little. Ahh, better? | Vươn vai một cái nào. Dễ chịu hơn chưa? | |
| 12 | Sit up straight! Your back will thank you. | Ngồi thẳng lưng lên nào, lưng bạn sẽ cảm ơn đó. | |
| 13 | You've been sitting a while. How about a short walk? | Ngồi lâu rồi đó, đứng dậy đi lại chút nhé. | |
| 14 | Breathe in... and out. Feeling lighter? | Hít một hơi thật sâu... rồi thở ra. Thấy nhẹ hơn chưa? | |
| 15 | I hope my little flame keeps your heart warm today. | Mong ngọn lửa nhỏ này sưởi ấm trái tim bạn hôm nay. | |
| 16 | You're doing great. Really. | Bạn đang làm tốt lắm, thật đó. | |
| 17 | Whatever happens today, I'm right here with you. | Dù hôm nay ra sao, mình vẫn ở đây với bạn. | |
| 18 | Proud of you for trying your best today. | Mình tự hào về bạn vì đã cố gắng hôm nay. | |
| 19 | If something's bothering you, tell me. Right-click me anytime. | Có chuyện gì buồn thì kể mình nghe nha, click chuột phải vào mình là được. | |
| 20 | Smile a little. It suits you! | Cười lên một chút nào, bạn cười xinh lắm! | |

  Xưng hô tiếng Việt: pet xưng **"mình"**, gọi user là **"bạn"** (Claude chọn; muốn "tớ / cậu" hay khác thì báo).

#### 2. Pomodoro dự định hoạt động thế nào (giải thích, thuộc mục P1 trong `TASKS.md`)
- **Pomodoro là gì:** chia thời gian làm việc thành từng "hiệp": **25 phút tập trung → 5 phút nghỉ ngắn**; sau **4 hiệp** thì **nghỉ dài 15 phút**. Mục đích: tập trung sâu trong thời gian ngắn và nghỉ đều để không đuối.
- **Bắt đầu:** chọn `Focus` trong menu chuột phải của pet, hoặc chat "bắt đầu pomodoro" / "tập trung 50 phút" (AI có thêm công cụ `start_focus`). Có thể chỉnh độ dài khi gọi bằng chat.
- **Trong 25 phút tập trung:** pet **ngồi yên** ở góc dưới màn hình (không đi lang thang, không câu quan tâm, không fact/joke), mặt bình thản. Rê chuột lên pet thì hiện số phút còn lại. Click pet vẫn phản ứng nhẹ nhưng không nhảy nhót. Cảnh báo máy (CPU / RAM) **dời tới giờ nghỉ**, riêng pin yếu vẫn báo ngay.
- **Hết giờ tập trung:** pet bật dậy, bong bóng "Time for a break! Stand up and drink some water." Bong bóng giữ tới khi user click pet (để không bị lỡ).
- **Trong giờ nghỉ:** pet chơi tự do như thường, có thể nhắc vươn vai / uống nước. Hết giờ nghỉ: "Ready for round 2?" — **chờ user click mới bắt đầu hiệp tiếp** (không tự ép làm tiếp), hoặc tự chạy tiếp nếu user chọn vậy.
- **Dừng / tạm dừng:** menu chuột phải có `Pause` / `Stop focus` khi đang chạy. Máy ngủ (gập laptop) quá giờ thì khi mở lại pet báo luôn là đã hết giờ.
- **Lưu ở đâu:** chỉ trong RAM — tắt app là mất hiệp đang chạy (giống chat). Có thể đếm số hiệp xong trong ngày ("3 pomodoros today!").
- **Khác với nhắc việc:** nhắc việc (`set_timer_reminder`) là hẹn **một lần** ("nhắc tôi uống nước sau 30 phút"); Pomodoro là **chu kỳ lặp** kèm thay đổi cách pet cư xử. Hai cái dùng chung bộ đếm giờ trong `BackgroundMonitor`.
- **Vẫn cần chốt (như đã ghi ở P1):** bật bằng menu, chat hay cả hai; độ dài mặc định (25/5/15, 4 hiệp); hết giờ nghỉ tự chạy tiếp hay chờ click; bong bóng hết giờ giữ tới khi click hay tự tắt.

#### 3. Biểu cảm mới: `cool` (ngầu)
- **User yêu cầu:** miệng **cười nhếch mép** (một khoé miệng nhếch lên, lệch một bên) + **đeo kính râm che mắt**.
- **Claude đề xuất chi tiết:**
  - Kính râm đen, hai tròng ôm theo vị trí mắt, có một vệt sáng chạy chéo qua tròng kính lúc vừa đeo. Kính là đồ vật vẽ thêm (như cái chảo của `chill`), không thay hình mắt.
  - Kính **rơi từ trên xuống** đậu vào mắt khi bắt đầu, lúc hết thì **đẩy lên** biến mất. Đeo kính nên mắt không nhìn theo chuột.
  - Lửa cháy đều, hơi ngả nhẹ người sang một bên cho "ngầu".
- **Cần chốt:** `cool` có vào nhóm hoạt ảnh ngẫu nhiên khi click không; có thêm vào danh sách cảm xúc AI chọn khi chat không (vd khi user khen pet); user có **hình tham khảo** không (như các hình 1-8 trong `docs/references/`) — nếu có thì Claude sẽ vẽ theo đúng hình.

#### 4. Thêm tính năng cho pet (Claude đề xuất, chờ user chọn; đã tránh các mục trong "Không chọn" của `TASKS.md`)

| # | Ý tưởng | Pet làm gì | Công sức | Lưu ý |
|---|---|---|---|---|
| T1 | Chào khi quay lại | User rời máy lâu (đã có bộ đo thời gian không dùng chuột/phím) rồi quay lại → pet chạy ra "Welcome back!"; lần đầu mở máy trong ngày thì chào buổi sáng | Ít | Dùng lại code ngủ gật (E2) |
| T2 | Bản tin thời tiết buổi sáng | Lần đầu thấy user trong ngày, pet báo thời tiết hôm nay, trời mưa thì nhắc mang ô | Ít | Dùng lại công cụ `weather` (Open-Meteo, không tốn quota AI); cần chốt thành phố |
| T3 | Vuốt ve pet | Rê chuột qua lại trên pet vài lần → pet nheo mắt sướng, lửa bùng nhẹ | Ít | Không cần click, rất "pet" |
| T4 | Nhắc nghỉ theo thời gian dùng máy thật | Dùng máy liên tục 60 phút không nghỉ → pet nhắc đứng dậy (thông minh hơn câu quan tâm theo giờ) | Ít | Có thể gộp vào mục 1 |
| T5 | Nhún theo nhạc | Máy đang phát nhạc (Spotify, YouTube…) → pet lắc lư theo, rê chuột thấy tên bài | Vừa | Đọc qua "Media controls" của Windows, chỉ đọc trên máy |
| T6 | Ngày lễ | Tết đội nón / lì xì, Giáng sinh đội mũ Noel, sinh nhật user có câu chúc | Vừa | Cần vẽ thêm đồ vật; ngày sinh nhật user tự nhập |

#### 5. Có nên làm pet thành một "agent" không? (Claude phân tích)
- **Hiện tại pet đã là agent một nửa:** khung chat dùng agent có công cụ (thời tiết, tìm web, trạng thái máy), nhưng **chỉ chạy khi user hỏi**. Phần còn lại (đi lại, biểu cảm, cảnh báo, câu nói) là luật viết sẵn.
- **Ba mức có thể đi tiếp:**
  1. **Agent khi được gọi (như bây giờ) + thêm công cụ:** bật Pomodoro, đặt nhắc việc, đọc file thả vào (P2), nhìn màn hình khi user bảo (N7), mở trang web / app (có hỏi xác nhận). Rẻ, an toàn, hữu ích ngay.
  2. **Agent chủ động:** cứ vài phút AI tự xem tình hình (giờ, user đang dùng app gì, thời tiết, câu chat gần đây) rồi tự quyết có nói gì / làm mặt gì. Nghe "sống" hơn nhưng: tốn quota Gemini liên tục, chậm, cần mạng, phải gửi thông tin máy (tên app, tiêu đề cửa sổ) lên Google, và AI có thể nói linh tinh / lặp.
  3. **Agent điều khiển máy:** tự mở app, sửa file, click chuột thay user. Rủi ro cao (làm sai là mất dữ liệu), không hợp một pet cá nhân.
- **Claude đề xuất:** **giữ mô hình lai.** Những gì xảy ra thường xuyên (câu quan tâm, Pomodoro, phản ứng, cảnh báo) dùng **luật viết sẵn** — miễn phí, tức thì, chạy cả khi mất mạng. AI chỉ dùng khi user chủ động (mức 1) và được thêm dần công cụ an toàn. Nếu muốn pet "thông minh" hơn mà vẫn rẻ: cho AI viết **vài câu quan tâm riêng mỗi ngày** dựa trên thời tiết / giờ (tối đa vài lần/ngày, bật tắt được) thay vì để AI chạy liên tục. Không làm mức 3.
- **Chờ user chọn** hướng nào.

### Lượt 21 (2026-11-14) — user trả lời lượt 20 (CHƯA CODE)

#### Câu quan tâm + fact/joke
- **User chốt:** **gộp** câu quan tâm với fact/joke thành một nhịp; fact/joke có thêm **bản tiếng Việt** (giống câu quan tâm); hiện **sau 5 phút** thay vì 15 phút.
- **Giải thích câu hỏi "Language đổi những gì":** pet đang nói ở 5 chỗ, hiện tất cả là tiếng Anh: (a) 20 câu phản ứng khi click, (b) 100 câu fact/joke, (c) câu quan tâm (mới), (d) cảnh báo máy ("RAM usage is at 93%…"), (e) chữ "Reminder:" khi nhắc việc. Câu hỏi là chọn `Tiếng Việt` thì đổi cả (a)-(e) hay chỉ một phần. Riêng câu trả lời của AI trong chat vẫn theo ngôn ngữ user gõ.
  - **Claude đề xuất:** đổi **cả (a)-(e)**. Fact/joke tiếng Việt **viết lại cho tự nhiên** (chơi chữ tiếng Anh dịch ra thường mất vui), đủ 100 câu như bản Anh. **Chờ user xác nhận.**
- **Giải thích "làm sao biết đang giờ tập trung":** giờ tập trung là bộ đếm Pomodoro do chính pet chạy, nên pet tự biết. Nay **Pomodoro bỏ** (xem dưới) → điều kiện này bỏ luôn. Pet vẫn im khi: đang ngủ / user đi vắng, đang cảnh báo, đang mở bong bóng chat, đang ẩn.
- **Claude đề xuất (user có thể đổi):** 5 phút tính từ câu gần nhất; trộn **xen kẽ** câu quan tâm và fact/joke (quan tâm → fact/joke → quan tâm…), mỗi loại bốc kiểu "xáo bài", câu quan tâm vẫn theo khung giờ. `config.yaml`: `ambient.interval_minutes: 5`.

#### Pomodoro
- **User:** không cần lắm (đã có cơ chế ngủ gật khi rời máy) → **bỏ Pomodoro**, chuyển sang "Không chọn" trong `TASKS.md`.

#### Nhắc việc ("nhắc tôi sau 30 phút…", "nhắc tôi lúc 11 giờ…") — cách triển khai (Claude đề xuất)
- **Hiện trạng:** đã có sẵn công cụ `set_timer_reminder` (chỉ nhận **số phút**, tối đa 24 giờ) và phần đếm giờ trong `BackgroundMonitor` (kiểm mỗi giây, tới giờ thì pet nhảy lên + bong bóng 8 giây). Đang **tắt** từ 2026-11-12 (AI được dặn trả lời "chưa đặt nhắc được").
- **Luồng chạy:**
  1. User chat "nhắc tôi lúc 11 giờ gọi cho mẹ". AI hiểu câu và gọi công cụ với `message="gọi cho mẹ"`, `at="11:00"` (hoặc `minutes=30` nếu nói "sau 30 phút").
  2. **Code tự tính giờ**, không để AI tính (AI hay tính sai giờ): `at` đã qua trong hôm nay → hiểu là ngày mai và nói rõ cho user ("11:00 sáng mai nhé"). Mỗi lần chat, AI được cho biết giờ hiện tại của máy để hiểu "tối nay", "chiều mai".
  3. Pet trả lời xác nhận trong chat: "Okay! 11:00 mình nhắc bạn gọi cho mẹ."
  4. Tới giờ: pet (đang ngủ thì thức dậy, đang ẩn thì tạm hiện) nhảy lên, bong bóng "Reminder: gọi cho mẹ" **giữ tới khi user click pet** để không bị lỡ.
- **Thêm 2 công cụ nhỏ:** "đang có nhắc gì?" → liệt kê; "huỷ nhắc lúc 11 giờ" → huỷ.
- **Máy ngủ / gập laptop qua giờ hẹn:** mở máy lên là pet nhắc ngay (kèm "trễ 10 phút").
- **Cần chốt:**
  - Lưu nhắc **chỉ trong RAM** (tắt app là mất) hay **lưu ra file** `%LOCALAPPDATA%\Lavenzure\reminders.json` (mở lại app vẫn còn, hẹn được xa hơn 24 giờ). Claude đề xuất: lưu ra file.
  - Có cần nhắc **lặp lại** không ("mỗi ngày 7h nhắc uống thuốc")? Claude đề xuất: chưa làm, để sau.
  - Bong bóng giữ tới khi click (Claude đề xuất) hay tự tắt sau vài giây; có phát **âm thanh** không.

#### Biểu cảm `cool`
- **User:** chưa có ảnh tham khảo → **Claude tự thiết kế** (theo mô tả lượt 20: kính râm rơi xuống, miệng nhếch mép một bên, vệt sáng lướt trên kính).
- **Claude tự quyết (user có thể đổi):** `cool` vào nhóm hoạt ảnh ngẫu nhiên khi click, và vào danh sách cảm xúc AI chọn khi chat (vd được khen, khoe điều gì đó).

#### Giải thích T1, T6
- **T1 "quay lại máy":** user không đụng chuột / bàn phím một lúc (đi ăn, đi họp…), sau 10 phút pet đã tự ngủ gật như hiện nay. Khi user quay lại và đụng chuột, hiện pet chỉ **thức dậy**; T1 thêm một câu chào kiểu "Welcome back! You were away 25 minutes." Chỉ chào khi vắng đủ lâu (vd từ 10 phút) để không chào liên tục.
- **T6 "ngày lễ":** vào các ngày đặc biệt pet **đeo thêm đồ** và có **câu chúc riêng** trong ngày đó, ví dụ: Tết âm lịch → khăn đỏ / cầm bao lì xì, "Chúc mừng năm mới!"; Giáng sinh → mũ Noel; Halloween → đèn bí ngô; **sinh nhật user** (user tự ghi ngày trong `config.yaml`) → mũ tiệc + "Happy birthday!" và pháo giấy. Ngày khác thì pet như bình thường.
- T1-T6 vẫn **chờ user chọn**.

### Lượt 22 (2026-11-14) — user chốt phần lớn lượt 21 (CHƯA CODE)

#### Ngôn ngữ + câu nói
- **User chốt:** chọn `Tiếng Việt` trong Settings thì **đổi hết** mọi câu pet nói (câu click, câu quan tâm, fact/joke, cảnh báo máy, chữ "Reminder:"). Chat với AI vẫn theo ngôn ngữ user gõ.
- **User chốt:** mỗi ngôn ngữ có **25 câu quan tâm + 50 câu fact/joke = 75 câu**. Fact/joke giảm từ 100 xuống 50 (Claude chọn 50 câu hay nhất của bản Anh, viết bản Việt tương ứng cho tự nhiên).
- **User chốt:** click vào pet mà ra hoạt ảnh "nói" thì câu nói **bốc ngẫu nhiên trong 75 câu đó** → bỏ danh sách 20 câu click riêng (`data/click_reactions.json`, kiểu "Ow, that tickles!"). Câu quan tâm có khung giờ thì lúc click cũng chỉ bốc câu hợp giờ.
- Nhịp tự nói: 5 phút một câu, xen kẽ câu quan tâm / fact/joke (lượt 21).
- **Thêm 5 câu quan tâm** (nối tiếp bảng lượt 20; khung *chiều* = 13-17h):

| # | English | Tiếng Việt | Khung giờ |
|---|---|---|---|
| 21 | Afternoon slump? A glass of water helps more than you think. | Buồn ngủ buổi chiều hả? Một cốc nước giúp nhiều hơn bạn nghĩ đó. | chiều |
| 22 | Remember to eat some fruit today! | Hôm nay nhớ ăn chút trái cây nha! | |
| 23 | Don't forget to message someone you love today. | Hôm nay nhớ nhắn hỏi thăm người thân nhé. | |
| 24 | A short break now will make you faster later. | Nghỉ một chút bây giờ, lát làm sẽ nhanh hơn đó. | |
| 25 | Thank you for keeping me company today. | Cảm ơn bạn đã cho mình ở bên hôm nay. | |

#### Nhắc việc
- **User chốt:** bong bóng nhắc việc **chỉ tắt khi user click vào pet**. **Không** làm lệnh liệt kê / huỷ nhắc.
- **User hỏi:** chat tự xoá sau 15 phút không nói chuyện (`memory.idle_timeout_minutes: 15`) thì nhắc việc có mất không?
  - **Trả lời:** **không mất.** Lịch sử chat và danh sách nhắc việc là **hai chỗ riêng**. Khi user chat "nhắc tôi lúc 11 giờ…", AI gọi công cụ, công cụ đưa lời nhắc vào danh sách của `BackgroundMonitor` (bộ đếm giờ chạy suốt khi app mở). Sau đó lịch sử chat bị xoá cũng không ảnh hưởng: tới giờ thì `BackgroundMonitor` tự bật nhắc, không cần AI nhớ gì nữa.
  - Thứ duy nhất làm mất lời nhắc là **tắt app / tắt máy** khi nhắc chỉ lưu trong RAM → câu hỏi lưu RAM hay ra file vẫn **chờ chốt**.
- **Còn chờ chốt:** lưu RAM hay file (Claude đề xuất file); có phát âm thanh không; nhắc lặp lại để sau (Claude đề xuất).

#### Biểu cảm `cool`
- **User đồng ý** đề xuất lượt 21 (Claude tự thiết kế; có trong nhóm click ngẫu nhiên và trong cảm xúc AI).

#### T1, T6
- **User:** T1 (chào khi quay lại máy) và T6 (đồ + câu chúc ngày lễ, sinh nhật) là tính năng hay nhưng tốn nhiều công thiết kế → **pending**, chưa làm. T2-T5 chưa được chọn.

### Lượt 23 (2026-11-14) — file nhắc việc, âm thanh, agent, ước lượng T6 (CHƯA CODE)

- **User hỏi:** lưu nhắc việc ra file thì máy có thêm một file, có bất tiện không?
  - **Trả lời:** gần như không. App **đã có sẵn** thư mục `%LOCALAPPDATA%\Lavenzure\` (đang chứa `settings.json` của Settings) → chỉ thêm `reminders.json` vào cùng chỗ, không tạo thư mục mới. Thư mục này nằm trong AppData (Windows ẩn sẵn, nơi mọi app lưu cài đặt), user không bao giờ thấy trên Desktop / Documents. File chỉ vài trăm byte, nhắc xong thì dòng đó tự xoá, hết nhắc thì file rỗng. Xoá app thì xoá luôn thư mục này.
  - **Chờ user chốt** lưu file hay RAM.
- **User chốt:** **âm thanh để sau**, làm chung với đợt thêm âm thanh cho hoạt ảnh.
- **User chốt:** **chưa làm hướng agent** (giữ như hiện tại: AI chỉ chạy khi user chat).
- **User hỏi:** thiết kế trang phục T6 có lâu không? **Claude ước lượng:**
  - **Phần khung (nhanh, ~1 lượt làm):** kiểm ngày khi mở app và lúc qua nửa đêm; ngày sinh nhật user ghi trong `config.yaml`; **ngày Tết âm lịch đổi mỗi năm** → ghi sẵn bảng ngày Tết 10 năm tới (đơn giản hơn thêm thư viện lịch âm); câu chúc riêng Anh / Việt.
  - **Phần vẽ là phần lâu.** Đồ được vẽ bằng code như cái chảo của `chill` (chảo ~230 dòng code, mất khoảng 4 lượt góp ý mới ưng). Cái khó chung: đầu ngọn lửa luôn lay động, co giãn, nghiêng theo chuyển động, nên đồ phải bám theo đúng chỗ mà không trông như dán đè.

| Đồ | Độ khó | Lý do |
|---|---|---|
| Mũ tiệc sinh nhật + pháo giấy | Dễ | Mũ hình nón đơn giản, đặt trên đầu như chảo; pháo giấy dùng lại hệ thống tàn lửa có sẵn |
| Mũ Noel (+ tuyết rơi nhẹ) | Dễ - vừa | Nón mềm có quả bông, phần chóp nên đung đưa theo chuyển động |
| Bao lì xì cầm tay (Tết) | Vừa | Pet không có tay rõ ràng (chỉ có tay lúc ngồi khúc gỗ) → phải thêm cách "cầm" |
| Khăn quàng đỏ (Tết) | Khó | Phải ôm theo thân lửa luôn đổi hình |
| Đèn bí ngô (Halloween) | Vừa | Đồ đặt cạnh pet, không phải bám theo người; Halloween không phổ biến lắm ở VN, có thể bỏ |

  - **Tổng:** khoảng **1 lượt khung + 1-2 lượt cho mỗi món dễ, 3-4 lượt cho món khó** (tính cả góp ý của user). **Claude đề xuất** nếu làm: bắt đầu với mũ tiệc + mũ Noel + bao lì xì (đều là đồ đặt trên đầu / bên cạnh), bỏ khăn quàng và Halloween ở đợt đầu.
  - T6 vẫn **pending**.

### Lượt 24 (2026-11-14) — user chốt lưu file, Claude làm các phần đã chốt (ĐÃ CODE)
- **User chốt:** nhắc việc **lưu ra file** (`%LOCALAPPDATA%\Lavenzure\reminders.json`), rồi yêu cầu làm mọi phần đã chốt ở lượt 20-23.
- **Đã làm:**
  - **Settings → Language** (English / Tiếng Việt), đổi ngay, được nhớ; mặc định `language: en` trong `config.yaml`. Đổi mọi câu pet nói: câu click, câu quan tâm, fact/joke, cảnh báo máy, chữ "Reminder:" (`src/pet_lines.py`).
  - **Pet tự nói mỗi 5 phút** (`ambient.interval_minutes: 5`, tính từ câu / click / chat gần nhất), xen kẽ câu quan tâm (`data/care_lines.json`, 25 câu như bảng lượt 20 + 22, kèm khung giờ) và fact/joke (`data/facts_jokes.json`, 50 câu chọn từ 100 câu Anh cũ + bản Việt viết lại). Bốc kiểu xáo bài, không lặp tới khi hết bộ. Không nói khi pet ẩn / ngủ, đang mở chat, đang có bong bóng giữ. Câu click "nói" bốc trong 75 câu; **xoá** `data/click_reactions.json`.
  - **Nhắc việc bật lại:** AI gọi công cụ với `minutes` hoặc `at`; code tự tính giờ; mỗi lần chat AI được cho biết giờ hiện tại của máy. Tới giờ: pet đang ẩn thì hiện ra, đang ngủ thì thức dậy và nhảy lên, bong bóng **giữ tới khi click vào pet** (chung với cảnh báo nếu có). Lỡ giờ (máy ngủ / app tắt) thì nhắc ngay khi có thể kèm "trễ N phút".
  - **Biểu cảm `cool`:** kính râm đen rơi từ trên xuống, có vệt sáng lướt qua tròng kính khi đáp, cười nhếch mép một bên, đầu hơi nghiêng; hết thì kính đẩy lên và mờ dần. Có trong phản ứng click (3 giây) và cảm xúc AI `[cool]` (khi được khen / khoe).
- **Claude tự quyết (user có thể đổi):**
  - Hẹn nhắc xa nhất **7 ngày**; "lúc 11 giờ" mà 11 giờ hôm nay đã qua thì hiểu là 11 giờ ngày mai.
  - Bong bóng câu tự nói hiện 4-9 giây tuỳ độ dài câu; khi tự nói pet làm mặt `happy` ngắn và nhép miệng.
  - Click khi đang có nhắc việc / cảnh báo thì chỉ tắt bong bóng đó (không chạy hoạt ảnh).
  - Cửa sổ Settings vẫn ghi bằng tiếng Anh (chỉ câu pet nói đổi theo Language).
- **Kiểm tra:** 140+ test tự động đều qua; chạy thử app thật ở chế độ không màn hình với Gemini thật: đổi sang tiếng Việt → câu tự nói / câu click ra tiếng Việt; chat "nhắc tôi uống nước sau 1 phút nhé" → file nhắc có lời nhắc, pet đang ẩn tự hiện ra, bong bóng "Nhắc nhở: Uống nước" vẫn còn sau 10 giây, click thì tắt và file rỗng; "nhắc tôi lúc 11 giờ gọi cho mẹ" (lúc 2 giờ sáng) → 11:00 hôm nay; "remind me tomorrow at 7:30…" → 7:30 ngày mai. **Chưa thử trên desktop thật** (pet của user đang chạy; cần tắt và mở lại pet để có tính năng mới).

### Lượt 25 (2026-11-14) — nhắc việc: hỏi giờ, huỷ nhắc, tab Reminders (ĐÃ CODE)
- **User chốt:**
  - Hẹn mà **không có giờ hoặc giờ mơ hồ** ("tối nay", "lát nữa") → gộp làm một: pet **hỏi lại kèm giờ gợi ý** ("Mấy giờ nhắc bạn? Mình đề xuất 20:00 nhé?"), user "ok" hoặc nói giờ khác thì mới đặt. Giờ gợi ý: sáng 08:00, trưa 12:00, chiều 15:00, tối 20:00, khuya 22:00, không nói gì thì 30 phút nữa (`config.yaml` `reminders.*`).
  - "Nhắc mình / nhắc tớ / nhớ báo mình…": **tin Gemini tự hiểu**, không làm bộ câu kiểm tra (chỉ thêm vài ví dụ vào hướng dẫn cho AI).
  - **Huỷ nhắc làm cả hai cách:** qua chat ("thôi khỏi nhắc nữa", "đổi sang 22h") và **tab "Reminders"** trong bong bóng chat (tên tiếng Anh), mỗi dòng có nút ✕ để gỡ. Thay quyết định lượt 22 "không làm lệnh liệt kê / huỷ".
- **Đã làm:**
  - Công cụ mới cho AI: `list_reminders`, `cancel_reminder` (theo số), `dismiss_reminder_bubble` (tắt nhắc đang hiện trên pet, giống click). Đổi giờ = huỷ cái cũ + đặt cái mới. Một nhắc duy nhất / vừa nói tới thì huỷ luôn; nhiều cái mà không rõ thì hỏi lại kèm danh sách.
  - Mỗi lời nhắc có **số** (lưu trong `reminders.json`; file cũ chưa có số tự được đánh số).
  - Bong bóng chat có 2 tab **Chat | Reminders (N)**; mở bong bóng luôn vào tab Chat; danh sách tự cập nhật khi đặt / huỷ / tới giờ.
- **Claude tự quyết (user có thể đổi):** bấm ✕ là gỡ ngay, không hỏi xác nhận; không thêm dòng xác nhận do code viết trong chat (tab Reminders đã cho thấy giờ đã đặt).
- **Kiểm tra:** test tự động đều qua; thử với Gemini thật: "nhắc mình gọi mẹ nhé" → hỏi lại, gợi ý 30 phút, "ok" → đặt; "tối nay nhắc tớ đi đổ rác" → gợi ý 20:00, "9h đi" → 21:00; "nhớ báo mình lúc 7h sáng mai…", "đừng để mình quên uống thuốc sau 45 phút" → đặt đúng; "thôi khỏi nhắc vụ đổ rác nữa" → huỷ đúng cái; "đổi giờ gọi mẹ sang 22h" → huỷ + đặt lại 22:00; chat mới "thôi không cần nhắc nữa" (3 nhắc) → hỏi cái nào. **Chưa thử trên desktop thật.**

#### Biểu cảm `chill` khi click (user hỏi)
- **Kết quả kiểm tra:** `chill` **có** trong bộ phản ứng click (10 phản ứng: happy, surprised, scared, angry, thinking, chill, yuck, cool, speak, fly; bốc thử 400 lần: chill ra 42 lần ≈ 1/10). Nhưng theo quyết định lượt 10, **khi pet đang bay trên khúc củi thì click không bao giờ ra `chill`** (chảo không đi với khúc củi). Pet bay khá nhiều (25% thời gian đi lang thang + phản ứng `fly`), nên dễ có cảm giác chill không bao giờ hiện. **Chờ user chọn** có đổi không.

### Lượt 26 (2026-11-14) — tab Reminders không cập nhật, gọn menu
- **User báo:** chat bảo pet nhắc nhưng tab Reminders không thấy gì. **Chưa sửa** (user dặn chỉ tìm nguyên nhân + hướng fix). Nguyên nhân và hướng fix: xem câu trả lời lượt 26 (chờ user chọn).
  - Log + file `reminders.json` cho thấy lần chat đó AI **không gọi công cụ đặt nhắc**, chỉ trả lời như đã đặt. Thử lại: hướng dẫn mới của lượt 25 làm Gemini flash-lite gần như không gọi công cụ nữa (1/16 lần), hướng dẫn cũ 16/16; thêm một câu "chưa gọi công cụ thì không được nói đã đặt" đưa về 16/16.
- **User chốt + đã làm:** bỏ `Hide Pet` khỏi menu khay (đã có ở menu chuột phải); khay chỉ hiện `Show Pet` khi pet đang ẩn (Claude tự quyết để còn cách gọi pet về). Bỏ vạch ngăn màu cam trong menu chuột phải của pet.

### Lượt 27 (2026-11-14) — sửa lỗi nhắc giả, giải thích `hours`, lỗi Alt+Tab
- **User chốt:** làm cả 3 hướng sửa lỗi "pet nói đã đặt nhắc nhưng không đặt" (lượt 26). **Đã làm:**
  1. Hướng dẫn cho AI nói rõ: viết chữ "đã đặt" không tạo được nhắc, phải gọi công cụ trước rồi mới báo (bỏ câu trích nguyên văn kết quả công cụ vì AI bắt chước in ra luôn). Thử với Gemini thật: 33/33, 15/15, 31/33 (2 lần trượt cùng một câu, sau đó chạy lại 33/33).
  2. Mỗi khi nhắc **thật sự** được đặt / huỷ qua chat, khung chat có một dòng nhỏ ở giữa do **code** viết: "⏰ Đã đặt nhắc: 21:00 hôm nay · đi đổ rác" (Anh / Việt theo Settings). Gỡ bằng nút × ở tab Reminders thì không có dòng này.
  3. `src/reminder_check.py`: chạy 11 tình huống (đặt, hỏi lại, huỷ) với Gemini thật, kiểm tra danh sách nhắc thật chứ không tin câu trả lời; chạy lại mỗi khi sửa hướng dẫn cho AI.
- **User hỏi:** trường `hours` trong `data/care_lines.json` làm gì, có phải gọi API xem giờ không? **Trả lời:** không gọi API; chỉ đọc đồng hồ của máy đúng lúc pet sắp nói (xem câu trả lời lượt 27).
- **User báo lỗi:** Alt+Tab thì pet bị ẩn, Alt+Tab lần nữa không chuyển được. Đang tìm nguyên nhân, **chưa sửa**.

### Lượt 28 (2026-11-14) — sửa lỗi Alt+Tab (pet không bao giờ thành cửa sổ đang dùng)
- **Nguyên nhân:** bấm hoặc kéo pet làm Windows coi pet là cửa sổ đang dùng, dù pet không có nút taskbar và không có trong danh sách Alt+Tab → Alt+Tab bị rối. Đã tái hiện bằng chuột thật (script thử trên desktop thật): trước khi sửa, bấm/kéo pet thì cửa sổ đang dùng đổi thành pet; sau khi sửa thì giữ nguyên app cũ.
- **Đã sửa:** cửa sổ pet thêm cờ `WindowDoesNotAcceptFocus` (Windows: `WS_EX_NOACTIVATE`) + `WA_ShowWithoutActivating` (`overlay_window.py`). Bấm, kéo, chuột phải (menu Chat / Idle / Hide Pet) vẫn chạy như cũ — đã thử: menu hiện, chọn Chat mở được khung chat, kéo pet đi theo chuột.
- **VS Code che mất pet:** lúc kiểm tra thấy cửa sổ VS Code đang ở chế độ "luôn nằm trên cùng" (có công cụ ghim ngoài, không phải của pet). Khi cả hai cùng "luôn nằm trên cùng" thì cửa sổ vừa được bấm sẽ nổi lên trước → VS Code che pet. User tự tắt ghim của VS Code; pet không đổi gì cho phần này.
- **Nhắc nhở đơn điệu ("Nhắc nhở: học bài"):** user báo lời nhắc chưa giống một con pet. **User chốt cách A, không cần câu dự phòng ngẫu nhiên. Đã làm:** khi đặt nhắc, AI viết thêm `line` = câu pet tự nói lúc nhắc đến giờ (giọng Lavenzure, đúng ngôn ngữ user, nhắc đúng việc); lưu cùng nhắc trong `reminders.json`, đến giờ hiện nguyên câu đó (trễ thì thêm "(trễ N phút)"). `line` là bắt buộc — AI thiếu hoặc để trống thì công cụ báo lỗi để AI gọi lại. Tab Reminders và dòng ghi chú trong chat vẫn hiện việc ngắn gọn (`message`). Chỉ nhắc cũ đã lưu trước đây (không có `line`) mới còn hiện "Nhắc nhở: <việc>". Thử với Gemini thật (`reminder_check.py`): 10/10 ca đặt/hỏi lại/huỷ qua, câu nhắc đúng giọng pet. Biểu cảm riêng cho lúc nhắc (mặt/hoạt ảnh) **để sau**: ghi vào `TASKS.md` P5.
- **Câu hỏi han tiếng Việt thiếu tự nhiên:** user gửi 6 câu, đã viết lại trong `data/care_lines.json` (bỏ "bạn cười xinh lắm" vì đoán giới tính, bỏ lối dịch từ tiếng Anh như "cho mình ở bên", "một cốc nước giúp nhiều hơn bạn nghĩ").
- **VS Code luôn nằm trên cùng:** đã gỡ ghim cửa sổ VS Code bằng `SetWindowPos(HWND_NOTOPMOST)` (không thấy công cụ ghim nào đang chạy nên chưa rõ ai ghim; nếu bị ghim lại thì dùng `Win+Ctrl+T` của PowerToys Always On Top hoặc chạy lại lệnh gỡ).

### Lượt 29 (2026-11-14) — viết lại toàn bộ fact/joke cho tự nhiên
- **User báo:** nhiều câu trong `data/facts_jokes.json` cringe và thiếu tự nhiên (ví dụ "đèn ngủ... có cá tính", "đốt calo bằng cách tồn tại", "mẹo an toàn... trừ mình ra"). Yêu cầu tập trung vào fact về lửa dễ hiểu ngay hoặc câu thể hiện cá tính; check cả Anh lẫn Việt.
- **Đã làm:** viết lại cả 50 câu mỗi ngôn ngữ (vẫn đủ 50 vì test kiểm tra số lượng): **25 fact về lửa + 25 câu cá tính**. Bỏ hết các câu đố "Vì sao ngọn lửa...?", knock-knock và chơi chữ gượng. Bản Anh và bản Việt viết riêng cho tự nhiên, không dịch từ nhau. Sửa vài fact sai/mơ hồ (tiếng nổ lách tách không phải do "không khí bị nhốt"; "chỗ nóng nhất ngay trên chân xanh"; "lửa nóng nhất gần như vô hình"; "tia lửa bằng hạt cát gây cháy rừng"). Thêm fact mới: gỗ không tự cháy, ngọn nến trong không trọng lực, Mặt trời không "cháy", lốc lửa, đuốc Olympic, chảo dầu cháy không tạt nước...
### Lượt 30 (2026-11-14) — soát lại fact/joke lần 2, câu quan tâm còn 20 câu
- **User chốt:** câu quan tâm giảm còn **20 câu mỗi ngôn ngữ** (user tự sửa `data/care_lines.json`) → tổng câu click "nói" là 20 + 50 = **70 câu**. Đã cập nhật test, docstring và tài liệu cho khớp.
- **User góp ý 7 câu fact chưa ổn** (bếp gas xanh, nến vàng, gỗ không tự cháy, lon nhôm, phượng hoàng, bonfire, lửa lên dốc) và nhờ soát lại cả bản Việt lẫn Anh; cho phép dùng fact không liên quan lửa và thêm emoticon `-.-` `^.^` `:3` `:>`.
- **Đã làm:** viết lại các câu đó cho gần lời nói hơn (bếp gas + nến gộp thành một câu, bỏ chữ "cháy rất hết"/"hong khô"); bỏ phượng hoàng và bonfire (không phải fact kiểm chứng được / hơi rợn). Thay bằng: mẹo thắp lại nến qua làn khói, lính cứu hỏa dùng lửa dập lửa, mật ong không hỏng, đốt củi chỉ còn ~1% tro, người nhìn màn hình chớp mắt ít một nửa. Bỏ câu "khói bay lên vì khí nóng nhẹ" (nhạt) và câu "nấu chín làm não to" (chỉ là giả thuyết). Giữ nguyên 2 câu đầu bản Việt mà user đã tự sửa. Thêm emoticon vào ~10 câu mỗi ngôn ngữ, chủ yếu câu cá tính. Vẫn 25 fact + 25 câu cá tính = 50.

### Lượt 31 (2026-11-14) — biểu cảm riêng khi nhắc lịch (CHỈ CHỐT, CHƯA CODE)
- **User hỏi:** nên hiện emoji gì khi nhắc nhở, cần một biểu cảm riêng. Claude tra emoji "reminder": ⏰ phổ biến nhất, 🔔 quá chung (lẫn với cảnh báo máy), 🎗️ tên đúng nhưng không ai hiểu, 📌 hợp ghi chú hơn giờ hẹn.
- **User chốt:** biểu tượng là **⏰ đồng hồ báo thức**; đồng hồ **rung liên tục đến khi user click** vào pet thì mới biến mất. Chi tiết thiết kế (mood `REMIND` + `AlarmClockProp`) ghi ở `TASKS.md` mục P5; chờ user nói bắt đầu code.

### Lượt 32 (2026-11-14) — ĐÃ CODE P5 (biểu cảm nhắc lịch) và P3/T1 (chào khi quay lại)
- **User:** code P3 (T1) và P5; lưu ý khi click lúc pet đang nhắc thì đồng hồ rút đi và pet chớp mắt cười ~1 giây kiểu "ok nhé".
- **P5 đã làm:** mood `REMIND` + `AlarmClockProp` (⏰ mặt kem, vỏ nâu đỏ, chuông + chân xanh ngọc). Đồng hồ nảy vào, **rung liên tục** tới khi click (kèm vạch "kring" hai bên nhấp nháy, búa gõ qua lại, kim giây nhích mỗi giây). Pet **đứng yên** tại chỗ trong lúc nhắc (trạng thái `REMIND`, ưu tiên ngay dưới cảnh báo máy), đang ngủ thì thức dậy. Click → đồng hồ thu nhỏ biến mất (kèm làn "poof") + mood `OK`: mắt nhắm "^ ^" cười, gật nhẹ, 1 giây; rồi pet đi lại bình thường (hoặc ngủ tiếp nếu đang Idle). AI tắt nhắc (`dismiss`) cũng vậy.
- **Hai điểm "còn mở" Claude tự chọn:** đồng hồ **lơ lửng bên phải** đầu pet (pet không có tay, vẽ tay cầm sẽ lệch phong cách); rung **6 lần/giây**, 4 giây đầu nghiêng 11° rồi dịu xuống 6° để để lâu không khó chịu. Đang có cảnh báo máy thì mặt cảnh báo thắng nhưng đồng hồ vẫn rung; một click tắt cả hai.
- **T1 đã làm:** khi pet đã ngủ gật (không đụng máy ≥ 10 phút) và user quay lại, pet thức dậy rồi ~1 giây sau cười và nói (theo ngôn ngữ Settings, 3 cách nói mỗi ngôn ngữ), vd "Welcome back! You were away for 25 minutes." / "Mừng bạn quay lại! Bạn đi vắng 25 phút đó." Thời gian tính từ lần đụng chuột/phím cuối: dưới 60 phút thì làm tròn phút; từ 60 phút trở lên **chỉ nói số giờ tròn** kèm "over" (user chốt sau: 1h15 hay 1h45 đều là "Welcome back! You were away for over 1 hour." / "... hơn 1 tiếng"). Không chào khi pet đang ẩn, đang Idle (vẫn ngủ), đang mở chat, hoặc đang có bong bóng nhắc / cảnh báo chờ click. Không làm phần "chào buổi sáng lần đầu trong ngày" (đã có câu quan tâm buổi sáng).
- **Đã kiểm:** test tự động (behavior, user_activity, pet_lines) + chạy thử app thật offscreen (nhắc → đứng yên + đồng hồ → click → OK → đi tiếp; nhắc đánh thức pet đang ngủ; ngủ gật 25 phút → quay lại → câu chào). **Chưa thử trên desktop thật** (cần khởi động lại pet).

## Còn bàn

- Đo lại 60 phút ở 30 fps + lửa nhẹ (`src/perf_check.py`, cần thoát pet đang chạy).
- Cách 3 (tạm dừng khi có app toàn màn hình) và cách 5 (lửa 30 khung/giây) — user để lại, chưa làm.
- Lượt 24: user thử các tính năng mới trên desktop thật và góp ý; T1, T6, P2 vẫn pending; âm thanh và hướng agent để sau.
