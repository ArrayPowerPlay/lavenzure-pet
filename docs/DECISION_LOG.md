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

## Còn bàn

- Đo lại 60 phút ở 30 fps + lửa nhẹ (`src/perf_check.py`, cần thoát pet đang chạy).
- Cách 3 (tạm dừng khi có app toàn màn hình) và cách 5 (lửa 30 khung/giây) — user để lại, chưa làm.
