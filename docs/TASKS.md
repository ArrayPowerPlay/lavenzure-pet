# TASKS — các mục cần làm

File này liệt kê những việc **sẽ làm hoặc đang cân nhắc** cho pet. Trạng thái:

- **Pending** — đã chọn là đáng làm nhưng **chưa chốt**: chỉ bắt tay làm khi user nói "chốt".
- **Nghiên cứu** — ý tưởng đã tìm hiểu xem có làm được không, chờ user chọn.
- **Không chọn** — đã bàn, user thấy chưa đáng làm (giữ lại để khỏi đề xuất lại).

Khi một mục được chốt: ghi quyết định vào `DECISION_LOG.md`, chuyển mục sang `implementation_plan.md`, rồi xoá hoặc đánh dấu ở đây.

---

## Pending (chờ chốt mới làm)

### P1. Nhắc việc qua chat — **đã làm** (lượt 24, xem `implementation_plan.md` H3)

### P2. Kéo file thả vào pet
- **Ý tưởng:** kéo một file (PDF, ảnh, văn bản) thả lên pet → pet "ăn" file (hoạt ảnh nhai), mở khung chat và tóm tắt / trả lời câu hỏi về file đó.
- **Cách làm:** cửa sổ pet nhận drag & drop của Qt (`setAcceptDrops`); gửi nội dung file cho Gemini (Gemini đọc được ảnh và PDF trực tiếp); câu trả lời hiện trong khung chat như bình thường.
- **Cần chốt trước khi làm:** loại file nào, giới hạn dung lượng; thả file xong thì tự tóm tắt luôn hay chờ user hỏi; có hoạt ảnh "ăn" riêng không. Lưu ý: nội dung file được gửi lên Google.

### P5. Biểu cảm riêng khi nhắc lịch — **đã làm** (lượt 32, xem `implementation_plan.md` H7)
- **Ý tưởng:** khi một lời nhắc đến giờ, pet có một biểu cảm / hoạt ảnh riêng (không dùng chung mặt vui / giật mình của click). Hiện lời nhắc chỉ có câu nói giọng pet (lượt 28) và pet nhảy lên báo (`trigger_notice`).
- **User đã chốt (2026-11-14, CHƯA CODE):**
  - Biểu tượng là **⏰ đồng hồ báo thức** (không dùng 🔔 chuông, 🎗️ ruy-băng, 📌 ghim, ☝️ ngón tay). Lý do: ⏰ là emoji quen thuộc nhất cho "đến giờ / nhắc việc", không lẫn với cảnh báo máy.
  - Đồng hồ **rung liên tục cho đến khi user click vào pet** thì mới biến mất (không rung 2 giây rồi đứng yên, không rung lại theo chu kỳ). Click = rút đồng hồ đi + pet chớp mắt cười ~1 giây.
- **Thiết kế Claude đề xuất (user đã đồng ý hướng chung):** mood mới `REMIND` (`face.py`) + prop `AlarmClockProp` (`props.py`, theo mẫu `SunglassesProp`), `_on_reminder` (`main.py`) gọi mood này thay cho `trigger_notice` (surprised).
  - Mặt: mắt tròn mở to nhìn ra phía người dùng, lông mày hơi nhướng, cười nhẹ kèm miệng hé "à này!"; lửa màu bình thường, không rung, không dùng bảng màu cảnh báo.
  - Đồng hồ: mặt tròn màu kem, viền nâu đỏ đậm như phong cách sticker, hai chuông nhỏ trên đỉnh, hai chân nhỏ dưới đáy; chuông và chân màu xanh ngọc cho nổi trên nền lửa cam. Nảy vào có độ nảy (overshoot), rung liên tục kèm vạch "kring" hai bên, kim giây nhích.
- **Còn mở:** dáng đồng hồ chi tiết (tay tròn cầm hay lơ lửng bên mặt), tốc độ / biên độ rung sao cho không gây khó chịu khi để lâu. Khi code sẽ so ảnh render với các mood khác rồi mới báo user.

### P3. T1 — chào khi quay lại máy — **đã làm** (lượt 32, xem `implementation_plan.md` H8)
- **Ý tưởng:** rời máy đủ lâu (pet đã ngủ gật) rồi quay lại → pet thức dậy và chào "Welcome back! You were away 25 minutes." (`DECISION_LOG.md` lượt 21-22).

### P4. T6 — trang phục ngày lễ
- **Ý tưởng:** Tết, Giáng sinh, Halloween, sinh nhật user → pet đeo đồ + câu chúc riêng. Ước lượng công sức ở `DECISION_LOG.md` lượt 23 (đợt đầu đề xuất: mũ tiệc, mũ Noel, bao lì xì).

---

## Nghiên cứu — tương tác với màn hình (2026-11-14)

Đã thử thật trên máy user (chỉ đọc, không di chuyển gì):
- Đọc được **tên + vị trí của 38 icon desktop** (vd `Recycle Bin` ở (17, 612)).
- Đọc được **nút trên thanh taskbar** (Start, Search, các app ghim…) kèm vị trí, mất ~85 ms.
- Đọc được **nút của cửa sổ app** (Minimize / Maximize / Close kèm vị trí), ~55 ms.

| # | Ý tưởng | Làm được? | Công sức | Rủi ro / giới hạn |
|---|---|---|---|---|
| N1 | Đứng / đi trên thanh tiêu đề cửa sổ | Dễ | Vừa | Cửa sổ bị cửa sổ khác che, phóng to toàn màn hình, màn hình ảo |
| N2 | Chơi với icon desktop | Được (đã thử) | Vừa | Chỉ thấy khi desktop không bị che; di chuyển icon có thể làm phiền |
| N3 | Đi trên taskbar, chỉ vào app | Được (đã thử) | Vừa | Taskbar ẩn tự động, taskbar dọc |
| N4 | Phản ứng với app đang dùng | Dễ | Ít | Cần danh sách app → phản ứng |
| N5 | Tương tác với nút / chữ trong app, web | Được một phần | Nhiều | Chậm, app Chrome/Electron phải bật chế độ trợ năng (tốn RAM) |
| N6 | Tiện ích trình duyệt (extension) | Được | Nhiều | Phải cài thêm extension, chỉ chạy trong trình duyệt |
| N7 | Pet "nhìn" màn hình bằng AI | Được | Ít–vừa | Gửi ảnh màn hình lên Google, tốn quota |

### N1. Đứng / đi trên cửa sổ app
- **Pet làm gì:** nhảy lên ngồi trên thanh tiêu đề của cửa sổ đang mở, đi dọc mép trên; cửa sổ bị kéo đi thì pet chao đảo hoặc rơi xuống; cửa sổ đóng hoặc thu nhỏ thì pet rơi xuống đáy màn hình.
- **Cách làm:** liệt kê cửa sổ và vị trí bằng Win32 (`EnumWindows`, `GetWindowRect`, dùng `DwmGetWindowAttribute` để lấy khung thật không gồm bóng); theo dõi cửa sổ di chuyển / đóng bằng `SetWinEventHook` (không phải hỏi liên tục, gần như không tốn CPU).
- **Khó:** pet luôn nằm trên cùng, nên nếu cửa sổ nó đứng bị cửa sổ khác che thì trông như đứng giữa không trung → chỉ chọn cửa sổ có mép trên đang thấy được (kiểm bằng `WindowFromPoint`); bỏ qua cửa sổ ẩn ở màn hình ảo khác (`DWMWA_CLOAKED`).

### N2. Chơi với icon desktop
- **Pet làm gì:** đi tới một icon và ngủ trên đó; "đá" icon trượt nhẹ rồi tự trả về chỗ cũ; đứng cạnh Thùng rác làm mặt `yuck`; đọc tên icon để nói đùa ("Chrome again?").
- **Cách làm:** icon desktop là một danh sách (`SysListView32`) của Explorer. Đọc tên + vị trí như đã thử. Muốn di chuyển icon thì dùng giao diện `IFolderView` của Windows (`SelectAndPositionItems`); phải nhớ vị trí cũ để trả lại.
- **Khó:** chỉ có nghĩa khi desktop đang hiện (không có cửa sổ che) → pet chỉ chơi với icon khi chỗ đó thấy được; nếu bật "Auto arrange" / "Align to grid" thì icon tự nhảy về lưới; tuyệt đối không tự mở hay xoá file.

### N3. Đi trên taskbar
- **Pet làm gì:** đi dọc taskbar, dừng lại "ngửi" icon app, ngồi lên icon app vừa mở; báo app nào đang nhấp nháy (có tin nhắn).
- **Cách làm:** đọc nút taskbar qua UI Automation (đã thử: 21 nút, ~85 ms). Pet đã đi dọc đáy màn hình nên chỉ cần thêm điểm dừng.

### N4. Phản ứng với app đang dùng
- **Pet làm gì:** mở game → pet cổ vũ; mở VS Code / PyCharm → pet đeo kính, nói "coding time"; xem YouTube lâu → pet ngáp; mở Zalo / Telegram → pet tò mò.
- **Cách làm:** bắt sự kiện đổi cửa sổ đang dùng (`EVENT_SYSTEM_FOREGROUND`), lấy tên chương trình + tiêu đề, tra bảng app → phản ứng (bảng nằm trong `data/`). Dễ nhất, rẻ nhất trong danh sách.
- **Lưu ý:** chỉ xử lý trên máy, không gửi tiêu đề cửa sổ lên mạng.

### N5. Tương tác với nút / chữ trong app hoặc web (UI Automation)
- **Pet làm gì:** chỉ tay vào nút; "cái này là gì?" → pet đọc chữ ở chỗ chuột trỏ hoặc đoạn đang bôi đen rồi giải thích trong chat; ngồi lên tiêu đề bài báo đang đọc.
- **Cách làm:** UI Automation của Windows cho biết cây thành phần (nút, ô nhập, đoạn chữ) kèm vị trí. Đã thử: đọc được nút của cửa sổ và taskbar.
- **Khó:** app viết bằng Chrome / Electron (Chrome, Edge, VS Code, Teams…) chỉ mở toàn bộ cây khi có chương trình hỏi; lúc đó app tốn thêm RAM/CPU (đã thấy: VS Code chỉ lộ 3 nút). Truy vấn mất hàng chục tới hàng trăm ms → phải chạy ở luồng phụ. Cách hợp lý nhất: **chỉ đọc khi user yêu cầu** (vd nút "Explain this" hay phím tắt), không quét liên tục.

### N6. Tiện ích trình duyệt (browser extension)
- **Pet làm gì:** biết chính xác trang web có gì (tiêu đề, ảnh, video); ngồi lên ảnh, đi theo khi cuộn trang, phản ứng khi video phát / dừng, tóm tắt trang.
- **Cách làm:** một extension nhỏ cho Chrome đọc trang rồi gửi cho pet qua kết nối trên máy (localhost). Chính xác hơn N5 nhiều nhưng là một dự án riêng (phải cài extension, giữ cho hai bên khớp nhau).

### N7. Pet "nhìn" màn hình bằng AI
- **Pet làm gì:** chat "nhìn màn hình giúp tôi" hoặc "lỗi này là gì?" → pet chụp màn hình, gửi Gemini (đọc được ảnh) rồi trả lời.
- **Cách làm:** Qt chụp màn hình rất dễ; gửi kèm câu hỏi trong agent hiện có.
- **Lưu ý:** ảnh màn hình có thể chứa thông tin riêng tư → chỉ chụp khi user bảo, không bao giờ tự chụp.

### Gợi ý thứ tự (Claude đề xuất, user quyết)
1. **N4** — rẻ, an toàn, pet "biết" bạn đang làm gì.
2. **N1 / N3** — pet đi lại trên cửa sổ và taskbar, thấy "sống" hẳn.
3. **N2** — vui nhưng chỉ thấy khi desktop không bị che.
4. **N7, N5 (chỉ khi user yêu cầu)** — hữu ích cho chat.
5. **N6** — để sau, công sức lớn.

---

## Không chọn (đã bàn 2026-11-14)

- Cảnh báo kèm tên app ăn RAM + pet đổ mồ hôi khi máy nặng.
- Tự ẩn khi có app toàn màn hình (trước đây gọi là "cách 3").
- Phím tắt mở chat.
- Thêm nội dung cho cửa sổ Settings.
- Pet đi trên cửa sổ khác (ý đầu, nay chi tiết hơn ở N1 để user xem lại).
- Tự khởi động cùng Windows (C3).
- Pomodoro / hẹn giờ tập trung (lượt 21: đã có ngủ gật khi rời máy).
