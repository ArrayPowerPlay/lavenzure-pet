# Implementation Plan — Lavenzure Desktop Pet

> Xem [CONTEXT.md](./CONTEXT.md) để hiểu bối cảnh/kiến trúc tổng thể. File này chỉ liệt kê việc cần làm theo giai đoạn.
> **Không bắt đầu code Phase 1 trở đi cho tới khi các câu hỏi ở mục "Open Questions" bên dưới được trả lời.**

## Quyết định đã chốt (round 2)

- **Overlay**: always-on-top + transparent thông thường (KHÔNG WorkerW), pet luôn nổi trên mọi app, chat window cũng always-on-top.
- **Màn hình**: 1 màn hình, không cần multi-monitor.
- **TTL lịch sử chat**: 10 phút không hoạt động → xóa sạch.
- **web_search**: Tavily. **weather**: Open-Meteo, vị trí trích từ prompt người dùng (LLM parse địa danh → geocode qua Open-Meteo Geocoding API).
- **Autostart**: Startup folder + `pythonw.exe` cho giai đoạn dev — xác nhận.
- **Framework**: LangGraph (thay ADK), gộp 1 process duy nhất — xác nhận.
- **LLM provider**: chuyển sang gọi **trực tiếp Google Gemini API** (không qua OpenRouter), model **`gemini-2.0-flash`**, dùng `langchain-google-genai` (`ChatGoogleGenerativeAI`), key lưu trong `GEMINI_API_KEY` — *cần bạn xác nhận lại vì đây là thay đổi so với quyết định OpenRouter trước đó (xem Q1 bên dưới)*.
- **Ngưỡng cảnh báo system_status**: pin < 30%, CPU > 90%, RAM > 90%.
- **System Tray**: icon tray cho phép bật/tắt hiển thị pet (ẩn overlay nhưng agent/background monitor vẫn chạy nền), cùng menu quản lý khác.
- **Ngôn ngữ câu thoại tự động**: tất cả bằng tiếng Anh — đã soạn sẵn 50 câu fact/joke (`data/facts_jokes.json`) và 20 câu phản ứng khi click (`data/click_reactions.json`), có thể chỉnh sửa sau.
- **Tool mới**: `random_fact_or_joke` (ambient, không phải tool LLM gọi — tự kích hoạt sau khoảng idle, lấy từ list ~50 câu), `set_timer_reminder` (tool LLM gọi được), `system_status` (vừa là tool LLM gọi được khi người dùng hỏi, vừa là background monitor tự động cảnh báo khi CPU/RAM/pin vượt ngưỡng — cảnh báo chỉ tắt khi người dùng click vào pet).

## Quyết định nhỏ còn lại (không chặn code, sẽ chốt khi tới phase liên quan)

- [x] **Q1.** Xác nhận chuyển hẳn từ OpenRouter sang gọi thẳng Google Gemini API — **đã xác nhận**.
- [x] **Q2.** Tần suất kiểm tra `system_status`: **45 giây/lần** — **đã chốt**.
- [x] **Q3.** Khoảng thời gian idle trước khi `random_fact_or_joke` tự kích hoạt: **15 phút cố định** — **đã chốt**.

> Trạng thái hiện tại: **Phase 0-9 đã có code** (xem mục "Trạng thái triển khai"). Nhân vật giờ vẽ bằng code nên không cần asset PNG. **Việc cần làm tiếp: xem mục "Kế hoạch tiếp theo" cuối file.**

---

## Phase 0 — Chốt quyết định & chuẩn bị
- [ ] Trả lời Q1-Q3 ở trên
- [ ] Chuẩn bị/tách asset layer PNG cho Lavenzure (theo `ANIMATION_TUTORIAL.md`)
- [ ] Đăng ký API key: `GEMINI_API_KEY` (Google AI Studio, bắt buộc), `TAVILY_API_KEY` (bắt buộc cho web_search)

## Phase 1 — Khởi tạo project
- [ ] Tạo virtualenv, `requirements.txt` (PySide6, langgraph, langchain-google-genai, pywin32, python-dotenv/pydantic-settings, requests/httpx, psutil cho system_status tool)
- [ ] Tạo cấu trúc thư mục theo `CONTEXT.md` mục 5
- [x] `.env.example` đã tạo (`GEMINI_API_KEY`, `TAVILY_API_KEY`)
- [x] `config.yaml` đã tạo (model, idle_timeout_minutes, system_status thresholds, ambient interval, tray...)
- [x] `data/facts_jokes.json` (50 câu, tiếng Anh) và `data/click_reactions.json` (20 câu, tiếng Anh) đã tạo sẵn

## Phase 2 — Overlay window always-on-top, transparent
- [ ] Tạo frameless, translucent `QWidget` (`Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool`, `WA_TranslucentBackground`)
- [ ] Click-through: chỉ nhận sự kiện chuột trong vùng bounding box có pixel thực của nhân vật (alpha-based hit test qua `QRegion`/`setMask()` dựng từ alpha channel của layer đang hiển thị), phần trong suốt xung quanh cho chuột xuyên qua tới app phía dưới
- [ ] Đảm bảo window luôn giữ vị trí always-on-top kể cả khi app khác cũng set always-on-top (xử lý qua timer re-raise nếu cần)
- [ ] Chat window dùng cùng cơ chế always-on-top (không click-through, nhận input bình thường)
- [ ] **System Tray icon** (`QSystemTrayIcon`): menu tối thiểu gồm "Show/Hide Pet" (ẩn/hiện overlay, không tắt agent/background monitor), "Open Chat", "Quit"

## Phase 3 — Asset pipeline & rig
- [ ] Làm theo [ANIMATION_TUTORIAL.md](./ANIMATION_TUTORIAL.md) để tách Lavenzure thành các layer PNG (thân/lửa nền, mắt trái/phải mở+nhắm, miệng ngậm+mở, ngọn lửa đỉnh đầu)
- [ ] Import vào `assets/lavenzure/`
- [ ] Dựng "rig" đơn giản: mapping layer → offset/anchor point để ghép lại thành 1 nhân vật hoàn chỉnh trên canvas (theo hướng dẫn trong tutorial)

## Phase 4 — Hệ thống animation thuần code
- [ ] Idle: bob lên xuống nhẹ, chớp mắt ngẫu nhiên, lửa lập lòe (opacity/scale oscillation) — dùng `QPropertyAnimation`/`QEasingCurve`/`QTimer`
- [ ] Walk (đi dọc mép màn hình): di chuyển ngang theo cạnh dưới màn hình, đổi hướng ngẫu nhiên
- [ ] Float (bay lơ lửng tự do): di chuyển tự do trong vùng màn hình, easing mượt
- [ ] Jump (nhảy): animation nhảy tại chỗ hoặc nhảy đổi vị trí
- [ ] Behavior State Machine: luân phiên ngẫu nhiên giữa idle/walk/float/jump, chuyển trạng thái mượt (transition)
- [ ] Reaction animation khi click (state riêng, không lặp)
- [ ] Talking animation (miệng mở/ngậm) đồng bộ khi agent đang trả lời

## Phase 5 — Tương tác chuột
- [ ] Click trái vào nhân vật → chuyển sang reaction animation + hiện random 1 câu thoại (bong bóng thoại ngắn) từ list câu thoại có sẵn (file JSON/YAML danh sách câu thoại)
- [ ] Kéo (drag): giữ chuột trái và di chuyển → nhân vật theo cursor, thả ra → rơi/tiếp đất lại vào state idle/walk
- [ ] Right-click → mở Chat Window (xem Q1 cho việc always-on-top)

## Phase 6 — Chat Window UI
- [ ] Cửa sổ chat đơn giản: khung lịch sử tin nhắn (chỉ trong phiên hiện tại) + ô nhập text + nút gửi
- [ ] Hiển thị trạng thái "đang suy nghĩ..." khi agent đang xử lý (không block UI)
- [ ] Đóng chat window không kill agent thread đang chạy dở (queue/cancel hợp lý)

## Phase 7 — Agent brain (LangGraph + Google Gemini API)
- [ ] Cấu hình `ChatGoogleGenerativeAI` (từ `langchain-google-genai`) với `model="gemini-2.0-flash"`, `google_api_key=GEMINI_API_KEY`
- [ ] Định nghĩa LangGraph graph: node LLM (tool-calling loop) + node tool-executor
- [ ] Chạy agent trong thread/asyncio riêng (không block Qt UI thread), trả kết quả về UI qua Qt signal

## Phase 8 — Session memory với TTL
- [ ] In-memory store (list message) gắn với 1 "phiên" duy nhất (không cần multi-user/multi-session)
- [ ] Timer reset mỗi khi có tin nhắn mới; hết TTL (Q6) → xóa sạch toàn bộ lịch sử trong RAM

## Phase 9 — Tools
- [ ] `weather`: Open-Meteo Geocoding API (tên địa điểm từ prompt → lat/lon) + Open-Meteo Forecast API
- [ ] `web_search`: Tavily API (cần `TAVILY_API_KEY`)
- [ ] `set_timer_reminder`: LLM tool nhận `duration` + `message`, đăng ký vào background monitor, khi hết giờ → hiện bong bóng nhắc nhở
- [ ] `system_status` (dual-mode):
  - On-demand: LLM tool trả lời khi người dùng hỏi (CPU/RAM/pin hiện tại qua `psutil`)
  - Proactive: background monitor polling định kỳ (mặc định 45s, Q2), khi **pin < 30%** hoặc **CPU/RAM > 90%** → trigger animation cảnh báo + bong bóng thông báo (tiếng Anh) trên đầu pet, **giữ nguyên tới khi người dùng click vào pet** mới tắt cả animation và bong bóng
- [ ] `random_fact_or_joke` (ambient, không phải LLM tool): timer trong background monitor, sau khoảng idle (mặc định 15-30 phút ngẫu nhiên, Q3) → random 1 câu tiếng Anh từ `data/facts_jokes.json` (50 câu, đã tạo sẵn), hiện bong bóng thoại tự tắt sau vài giây
- [x] `data/click_reactions.json` (20 câu tiếng Anh) và `data/facts_jokes.json` (50 câu tiếng Anh) đã tạo sẵn — có thể chỉnh sửa nội dung sau

## Phase 10 — Autostart
- [ ] Script tạo shortcut trong `shell:startup` chạy `pythonw.exe main.py` (đã xác nhận)
- [ ] (Sau này) Chuyển sang Task Scheduler khi đóng gói `.exe` bằng PyInstaller

## Phase 11 — Đóng gói (để sau, chưa ưu tiên v1)
- [ ] PyInstaller build thành `.exe` portable
- [ ] Cập nhật autostart dùng Task Scheduler thay vì Startup folder

## Phase 12 — Polish & testing
- [ ] Hoàn thiện menu System Tray (thoát app, tạm dừng animation, mở config, show/hide pet đã làm ở Phase 2)
- [ ] Xử lý lỗi API (Gemini timeout/lỗi mạng/hết quota) → Lavenzure phản hồi lỗi thân thiện thay vì crash
- [ ] Kiểm tra hiệu năng (CPU usage khi animation + background monitor chạy liên tục 24/7)

---

## Ghi chú
- Mỗi phase chỉ bắt đầu khi phase trước đã xong và các Open Question liên quan đã được trả lời.
- Cập nhật checklist này (đánh dấu `[x]`) khi hoàn thành từng việc, và cập nhật `CONTEXT.md` khi có quyết định/thay đổi thiết kế mới.

## Trạng thái triển khai (cập nhật 2026-08-13)

Đã có code cho: virtualenv + `requirements.txt` cài đặt thành công, `config.py`/`config.yaml`/`.env.example`, overlay window always-on-top + click-through mask + placeholder sprite (`overlay_window.py`), animation helpers (`animation.py`), behavior state machine idle/walk/float/jump/drag/react/alert (`behavior.py`), speech bubble (`speech_bubble.py`), chat window (`chat_window.py`), LangGraph agent với Gemini 2.0 Flash + 4 tools (`agent/graph.py`, `agent/tools/*`), TTL session memory (`agent/memory.py`), background monitor cho system_status/reminder/idle-joke (`monitor/background_monitor.py`), autostart script (`autostart/install_startup.py`), và `main.py` kết nối toàn bộ. Đã smoke-test build + chạy ứng dụng thành công (Qt offscreen mode).

Còn thiếu / cần làm tiếp:
- [ ] Thêm `GEMINI_API_KEY` và `TAVILY_API_KEY` thật vào file `.env` (copy từ `.env.example`)
- [ ] Chạy thử trên màn hình Windows thật (không phải offscreen) để kiểm tra click-through/always-on-top/mask thực tế
- [x] Nhân vật thật: thay placeholder bằng nhân vật vẽ bằng code (`src/overlay/character.py`) — không cần PNG (2026-11-11). Xem thử: `.venv-win/Scripts/python.exe src/character_preview.py`
- [x] Vẽ lại đồ họa theo ảnh mẫu fan-art (sticker phẳng, dáng giọt nước, viền liền, lưỡi lửa chạy dọc sườn lên đỉnh + bùng lửa ngẫu nhiên) — chờ user duyệt (2026-11-12)
- [x] Animation lửa kiểu mô phỏng lưỡi lửa + metaball (`src/overlay/fire_field.py`, cần `numpy`), kích thước 0.75, giữ glow, không thêm viền sticker (2026-11-12)
- [x] Làm lại mặt (`face.py`: nằm gọn trên thân vàng, biểu cảm lò xo + lấy đà, mí mắt, quay đầu) + "thời tiết lửa" + 3 bộ vẽ thân lửa để so sánh: `metaball`, `shader` (GPU), `baked` (mô phỏng chất lỏng, tạo lại bằng `src/bake_flame.py`) — chọn bằng `character.flame_renderer` (2026-11-12)
- [x] User so sánh 3 bộ vẽ và **chốt `shader`** làm mặc định (2026-11-12)
- [x] Chuyển động mượt: vị trí cửa sổ sub-pixel (`exactPos`) + vòng frame chung đồng hồ animation Qt; mặt sống động hơn (saccade, chớp mắt, biểu cảm lò xo, miệng nói theo nhiễu) (2026-11-12)
- [ ] Chờ user xem thử trên desktop thật và góp ý
- [ ] Animation nâng cao theo ảnh mẫu: tay, ôm/gặm củi, nằm trên củi, chảo + trứng ốp la/thịt xông khói, trứng vỡ
- [ ] Chạy `src/autostart/install_startup.py` để tạo shortcut Startup (Phase 10)
- [ ] Phase 11 (PyInstaller) và Phase 12 (polish/testing hiệu năng) vẫn chưa làm

---

## Kế hoạch tiếp theo (lập 2026-11-12)

> Checklist Phase 0-12 phía trên được viết từ trước khi code nên nhiều ô `[ ]` đã lỗi thời (code cho Phase 0-9 đã có). **Từ giờ dùng danh sách dưới đây làm việc cần làm chính.**
>
> **Tiến độ (2026-11-12):** user đồng ý A, B, D → đã làm xong A1-A6, B1-B5, D1-D4 (còn A7: user thử trên desktop thật). F để sau. C1, C2 (mới), E1, E2 (bỏ "gọi pet") và toàn bộ giai đoạn G đã duyệt, chờ làm; C3 để sau; hẹn giờ tạm tắt. Chi tiết từng quyết định: [DECISION_LOG.md](./DECISION_LOG.md).

> **Thứ tự làm (chốt 2026-11-12, lượt 7):** G4 → G3 → G1 + G2 → E1 → E2 → C1 + menu khay → `chill` + chảo. Cửa sổ Settings tạm để trống.
>
> **Tiến độ (2026-11-12, cuối phiên):** đã làm xong G4, G3, G1, G2, E1, E2, C1, C2 (menu khay) và `chill` + chảo; chờ user duyệt. Còn lại: E3 (tay thật…), nội dung Settings, C3, F.

### Giai đoạn A — Cho app dùng được hằng ngày (ưu tiên cao nhất)
- [x] **A1. Đổi model Gemini — chat đang hỏng hoàn toàn.** → *Đã đổi sang `gemini-flash-latest` (user chọn), gọi qua endpoint `v1beta`, đọc đúng câu trả lời dạng nhiều khối; đã thử cả 4 tool với key thật.* `gemini-2.0-flash` đã bị Google ngừng: gọi API trả 404 "no longer available" (kiểm tra 2026-11-12). Ứng viên: `gemini-flash-latest` (bí danh luôn trỏ bản Flash mới nhất, đã gọi thử OK) hoặc chốt một bản cố định như `gemini-3.8-flash` (ổn định hơn, nhưng sẽ lại bị ngừng sau này). Cần kiểm tra cả tool-calling qua `langchain-google-genai` (có thể phải nâng cấp thư viện). *Cần user chọn.*
- [x] **A2. Báo lỗi rõ ràng thay vì một câu chung chung.** Hiện mọi lỗi agent đều thành "my flame flickered out" và lý do bị nuốt mất. Phân loại: sai/thiếu key, hết quota, mất mạng, model không còn → câu báo lỗi tiếng Anh phù hợp; ghi chi tiết vào file log.
- [x] **A3. Ghi log ra file** (`logging` + file xoay vòng, vd. `%LOCALAPPDATA%\Lavenzure\lavenzure.log`). Khi chạy bằng `pythonw.exe` (autostart) không có console nên hiện tại lỗi biến mất hoàn toàn.
- [x] **A4. Không crash khi thiếu `GEMINI_API_KEY`.** `agent/graph.py` tạo client ngay lúc import → app không mở được. Chuyển sang tạo khi chat lần đầu; thiếu key thì pet vẫn chạy, chat báo cần key.
- [x] **A5. Công cụ chịu lỗi mạng.** `weather`/`web_search` hiện ném exception khi mất mạng/API lỗi → hỏng cả lượt chat. Bắt lỗi và trả về câu mô tả lỗi cho LLM.
- [x] **A6. Chỉ cho chạy 1 bản** (`QLocalServer`/`QLocalSocket` hoặc named mutex). Tránh 2 con pet khi vừa autostart vừa chạy tay; lần chạy thứ 2 có thể chỉ mở cửa sổ chat của bản đang chạy.
- [ ] **A7. Thử trên desktop thật** theo checklist: click xuyên vùng trong suốt, luôn nổi trên app khác (kể cả app fullscreen/always-on-top khác), kéo-thả, cảnh báo, hẹn giờ, CPU khi chạy vài giờ. → *Đang làm (2026-11-12, lượt 13):* checklist ở [TEST_CHECKLIST.md](./TEST_CHECKLIST.md); phần máy tự kiểm (`src/desktop_check.py`: luôn nổi, click xuyên góc trong suốt, thân lửa nhận click, nằm trên taskbar) đã PASS; phần cần người thử đang chờ user.
- [ ] **A8. Hiệu năng (Phase 12 cũ)** → *Đang làm (lượt 13):* có công cụ đo `src/perf_check.py` + dòng `frame stats` trong log. Đo lần đầu: CPU ~3.7% cả máy, GPU ~12%, RAM 657 MB, ~10 ms/khung. Đã sửa: giới hạn OpenBLAS 1 luồng (RAM lúc mở 657 → ~173 MB) và đọc ảnh lửa từ GPU không chờ (PBO, ~6 ms → ~1 ms/khung, hình giống hệt). Đo 60 phút (2026-11-13): CPU 3-4%, GPU 12-13%, RAM ~220 MB không rò rỉ. *Lượt 14:* bớt tính toán thừa mỗi khung (~8,5 → ~7,2 ms, hình không đổi); thêm 2 chế độ bật/tắt trong Settings: **tốc độ khung hình tự đổi** (60/30/15 fps) và **lửa nhẹ** (độ phân giải lửa 1,5). *Lượt 15:* user chốt lửa nhẹ (bật mặc định); thêm lựa chọn giới hạn **60 / 45 / 30 fps** cho mọi hoạt ảnh để thử. Còn: user chọn fps mặc định, đo lại 60 phút. Tạm dừng khi có app toàn màn hình và lửa 30 fps: user để lại.

### Giai đoạn B — Chat và bong bóng thoại
- [x] **B1. Bong bóng thoại đi theo pet.** Hiện bong bóng đặt vị trí 1 lần rồi đứng yên; pet đi chỗ khác thì bong bóng bị bỏ lại (rõ nhất với cảnh báo dính lâu).
- [x] **B2. Sửa hiển thị chat:** tin nhắn đang được chèn thẳng dạng HTML nên chữ có `<`, `>`, `&` hiển thị sai — cần escape; hiển thị markdown cơ bản (đậm, danh sách, link) cho câu trả lời của Gemini; tự cuộn xuống cuối.
- [x] **B3. Giao diện chat hợp với nhân vật:** màu ấm theo tông lửa, mở cạnh pet thay vì giữa màn hình, phím Esc để đóng, hiển thị "Lavenzure is thinking…".
- [x] **B4. Câu trả lời ngắn hiện luôn trong bong bóng trên đầu pet** (tùy chọn trong `config.yaml`), để không cần mở cửa sổ chat cũng thấy.
- [x] **B5. Hẹn giờ nhắc việc chắc chắn hơn:** tool `set_timer_reminder` đang gọi thẳng vào monitor từ thread của agent → chuyển qua Qt signal cho an toàn; khi nhắc thì pet đổi biểu cảm/nhảy lên cho dễ thấy; kiểm tra số phút âm/quá lớn. (Vẫn chỉ lưu trong RAM theo thiết kế.)

### Giai đoạn C — Khay hệ thống và tiện ích (Phase 12 cũ)
- [x] **C1. Icon khay hệ thống đúng hình nhân vật** — hiện chụp cửa sổ pet trước khi nó hiện lên nên có thể ra icon trống; nên vẽ icon riêng từ `FlameCharacter`.
- [x] **C2. Menu khay hệ thống 3 mục:** `Hide/Show Pet`, `Settings` (mở cửa sổ chỉnh cấu hình nhỏ — nội dung chốt sau), `Quit App`. Bỏ `Open Chat`.
- [ ] **C3. Chạy `install_startup.py`** để tạo autostart (Phase 10) — *để sau*.

### Giai đoạn D — Chất lượng code
- [x] **D1. Test tự động (pytest)** (85 test, chạy: `.venv-win/Scripts/python.exe -m pytest`) cho phần không cần màn hình: `config.get`, bộ nhớ TTL, logic monitor (ngưỡng cảnh báo, hẹn giờ, câu idle), các tool (giả lập HTTP), `Expression`/lò xo của `face.py`.
- [x] **D2. Linter/formatter** (`ruff`) với cấu hình giữ CRLF.
- [x] **D3. Bổ sung docstring còn thiếu** (`main.py`, `chat_window.py`, `background_monitor.py`, `memory.py`, … nhiều class/hàm chưa có — trái quy ước của repo).
- [x] **D4. Dọn tài liệu cũ:** sơ đồ kiến trúc trong `CONTEXT.md` vẫn ghi OpenRouter và "PNG cutout"; §4 (câu hỏi mở đã giải quyết), §5 (`.env.example` ghi `OPENROUTER_API_KEY`) lỗi thời; xóa `assets/lavenzure/PLACEHOLDER.txt`; cập nhật `CLAUDE.md` (repo giờ ở `D:\workspace\pet`).

### Giai đoạn E — Nhân vật sống động hơn
- [x] **E1. Biểu cảm theo nội dung chat:** agent trả kèm "mood" để pet đổi mặt khi trả lời: `happy`, `scared`, `angry`, `chill`, `surprised`, `thinking`, `yuck` (thêm ở lượt 12), `other` (= không đổi biểu cảm). Thêm tư thế bay trên khúc củi. Ảnh mẫu: `docs/references/calcipher_picked.jpg`; chi tiết: DECISION_LOG lượt 6.
- [x] **E2. Hành vi theo ngữ cảnh:** ngủ gật sau 10 phút không dùng máy, ban đêm (20h–5h) lửa dịu lại. ("Gọi pet chạy lại gần chuột": tạm bỏ.)
- [ ] **E3. Animation nâng cao theo ảnh mẫu:** tay (bắt buộc làm sau cho mặt `angry`), ôm/gặm củi, nằm trên củi, chảo + trứng ốp la/thịt xông khói, trứng vỡ — *chưa quyết*.

### Giai đoạn G — Tương tác mới (chốt 2026-11-12, xem DECISION_LOG)
- [x] **G1. Chuột trái = 1 phản ứng ngẫu nhiên** từ bộ gồm mọi hoạt ảnh của pet + "nói 1 câu ngẫu nhiên" (trừ mặt cảnh báo và tư thế ngủ). Hoạt ảnh mới tự đăng ký vào bộ.
- [x] **G2. Chuột phải = menu `Chat` / `Idle`**; đang Idle thì `Idle` đổi thành `Wander`. Idle có tư thế nằm nghỉ/ngủ riêng (vẽ mới).
- [x] **G3. Bong bóng chat thay cửa sổ chat:** gắn với pet, cuộn đọc lại tin cũ; tự đóng sau 30 giây không chat (không đếm khi đang gõ hoặc AI đang trả lời); lịch sử xóa sau 15 phút không chat (đổi `memory.idle_timeout_minutes` 10 → 15).
- [x] **G4. Tạm tắt công cụ hẹn giờ** (gỡ `set_timer_reminder` khỏi danh sách tool, giữ code).

### Giai đoạn F — Đóng gói (Phase 11) — *để sau (user chốt 2026-11-12)*
- [ ] **F1. PyInstaller** ra `.exe` (chú ý: `data/`, `assets/flame/`, shader GLSL, OpenGL trong bản đóng gói).
- [ ] **F2. Autostart bằng Task Scheduler** cho bản `.exe`.

### Để sau
- Chat bằng giọng nói (voice).
