# Checklist thử trên desktop thật (A7) và đo hiệu năng (Phase 12)

> Dùng file này mỗi lần muốn kiểm tra app trên máy Windows thật. Đánh `[x]` vào ô đã thử OK; ghi chú chỗ nào lỗi ngay dưới mục đó (thấy gì, lúc nào, đang làm gì).

## 0. Chuẩn bị

```powershell
.venv-win\Scripts\python.exe src\main.py
```

File log nằm ở `%LOCALAPPDATA%\Lavenzure\logs\lavenzure.log`. Cứ 10 phút pet ghi một dòng `frame stats` (số khung hình/giây và thời gian vẽ mỗi khung).

## 1. Phần máy tự kiểm (chạy khi pet đang mở)

```powershell
.venv-win\Scripts\python.exe src\desktop_check.py
```

Script chỉ đọc thông tin cửa sổ, không click hay di chuyển gì. Nó kiểm tra: cửa sổ luôn nổi trên cùng, không hiện nút trên taskbar, góc trong suốt cho click xuyên qua, phần thân lửa thì nhận click, pet nằm trong vùng màn hình phía trên taskbar.

- [ ] Tất cả các dòng đều `PASS`

## 2. Phần cần người thử

### Click xuyên và luôn nổi trên cùng
- [ ] Click vào khoảng trống sát cạnh ngọn lửa (trong vùng quầng sáng) → click rơi xuống app bên dưới, không bị pet "ăn" mất
- [ ] Mở trình duyệt / VS Code toàn màn hình (phóng to cửa sổ, không phải F11) → pet vẫn nổi trên
- [ ] Bấm F11 (toàn màn hình thật) trong trình duyệt, và mở video YouTube toàn màn hình → ghi lại pet còn nổi hay bị che
- [ ] Mở một app cũng "luôn nổi trên cùng" (vd. Task Manager → Options → Always on top), click vào nó → ghi lại pet có bị nó che không, và có tự nổi lại không
- [ ] Click vào taskbar / mở Start menu khi pet đang đi sát đáy → pet có bị che không

### Chuột
- [ ] Click trái → một hoạt ảnh ngẫu nhiên, hai lần liên tiếp không trùng nhau
- [ ] Giữ chuột trái và kéo → pet đi theo chuột, mặt giật mình; thả ra → rơi xuống và tiếp đất mượt
- [ ] Kéo pet ra sát mép trái/phải/trên của màn hình rồi thả → pet không bị kẹt ngoài màn hình
- [ ] Chuột phải → menu `Chat` / `Idle`; chọn `Idle` → pet nằm ngủ; mở lại menu thấy `Wander`

### Chat
- [ ] Chuột phải → `Chat` → gõ câu hỏi → pet làm mặt "đang nghĩ", rồi trả lời kèm biểu cảm vài giây
- [ ] Hỏi thời tiết, nhờ tìm web, hỏi CPU/RAM → cả 3 công cụ trả lời được
- [ ] Tắt Wi-Fi rồi chat → pet báo lỗi mất mạng dễ hiểu, không treo, không crash
- [ ] Để bong bóng chat yên 30 giây → tự đóng
- [ ] Mở chat lần nữa trong vòng 15 phút → lịch sử còn; sau 15 phút không chat → đã bị xóa

### Cảnh báo và hành vi theo thời gian
- [ ] (Laptop) rút sạc đến khi pin < 30% → pet hiện cảnh báo; cảnh báo giữ nguyên tới khi click vào pet
- [ ] Không đụng chuột/bàn phím 10 phút → pet ngáp rồi ngủ gật; động vào chuột → pet tỉnh
- [ ] Sau 20h → lửa dịu, đỏ trầm hơn
- [ ] Để yên 15 phút → pet tự nói một câu fact/đùa

### Khay hệ thống và khởi động
- [ ] Icon khay đúng hình pet; `Hide Pet` → pet ẩn, `Show Pet` → hiện lại đúng chỗ
- [ ] Chạy `src\main.py` lần thứ hai → không ra con pet thứ hai, chỉ mở bong bóng chat của con đang chạy
- [ ] `Quit App` → thoát hẳn (Task Manager không còn `python.exe` của pet)

### Chạy lâu
- [ ] Để pet chạy cả ngày làm việc bình thường → không crash, không chậm dần, máy không nóng/ồn quạt hơn bình thường
- [ ] Sau đó xem file log: không có dòng `ERROR` / `CRITICAL` lạ; các dòng `frame stats` vẫn quanh mức fps đã chọn (mặc định 30)

## 3. Đo hiệu năng (Phase 12)

Thoát pet đang chạy (khay hệ thống → `Quit App`) rồi chạy:

```powershell
.venv-win\Scripts\python.exe src\perf_check.py --minutes 60
```

Script tự mở pet, mỗi 10 giây đo CPU, RAM, handle, GDI/USER object và mức dùng GPU, ghi vào file CSV trong thư mục log, cuối cùng in bản tóm tắt rồi đóng pet. Muốn đo con pet đang chạy sẵn (vd. sau cả ngày dùng): `--pid <số process>`.

Mục tiêu (đề xuất, chỉnh nếu muốn):

| Chỉ số | Mục tiêu | Ý nghĩa nếu vượt |
|---|---|---|
| CPU trung bình (% cả máy, như Task Manager) | dưới 2% | quạt kêu, tốn pin |
| GPU 3D | dưới 10% | tốn pin trên laptop |
| RAM (private) | dưới 250 MB | chiếm bộ nhớ |
| RAM / handle tăng sau phút đầu | gần 0 mỗi giờ | rò rỉ bộ nhớ: chạy lâu sẽ phình dần |
| `frame stats` | ~30 fps (mức mặc định), work avg dưới 8 ms | hoạt ảnh bị giật |

### Số khung hình/giây (lượt 16)

Khay → `Settings` → mục **Performance** → **Frame rate**. Mặc định 30 fps (user chốt); chọn 45 / 60 có hiệu lực ngay, dòng `Drawing: … fps` cho biết pet đang vẽ bao nhiêu khung/giây.

- [ ] Mở app lần đầu (chưa chọn gì trong Settings) → dòng `Drawing` hiện ~30 fps.
- [ ] Chọn 45 / 60 → dòng `Drawing` hiện ~45 / ~60; thoát rồi mở lại app → vẫn giữ mức đã chọn.
- [ ] (Tùy chọn) Thoát pet rồi chạy `perf_check.py --minutes 60` để đo lại ở 30 fps.

### Kết quả đo

| Ngày | Phiên bản | Thời gian | CPU tb / max | GPU tb | RAM | RAM tăng/giờ | Frame (fps, ms) | Ghi chú |
|---|---|---|---|---|---|---|---|---|
| 2026-11-12 | trước tối ưu | 1.5 phút | 3.7% / 4.7% | 11.9% | 657 → 690 MB | — (quá ngắn) | 57-61 fps, 9.9 ms | OpenBLAS chiếm ~490 MB; đọc ảnh lửa từ GPU chiếm ~6 ms/khung |
| 2026-11-13 | sau tối ưu (đọc ảnh lửa bất đồng bộ, OpenBLAS 1 luồng) | 60 phút (pet chạy ~21 phút, sau đó màn hình tắt nên pet tự ngừng vẽ) | 3.0–4.1% | 12–13% | 207 → 223 MB rồi đứng yên | ~0 | 61–62 fps, 6.6–7.0 ms (max ~70 ms) | không rò rỉ RAM/handle/GDI; CPU và GPU vẫn trên mục tiêu |
| 2026-11-13 | lượt 14, từng chế độ (pet chủ yếu đứng yên) | 4 × 60 giây | tắt cả hai 3.2% · adaptive 2.0% · lite 2.9% · cả hai 1.7% | 12% (tắt cả hai) | — | — | 61 fps · ~31-34 fps khi adaptive | đo nhanh bằng script, chưa phải 60 phút; GPU từng chế độ chưa đo được (user đang dùng máy) |
