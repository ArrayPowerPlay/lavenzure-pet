# Calcifer Desktop Pet

**Tiếng Việt** · [English](./README.md)

Một "thú cưng" ngọn lửa sống trên màn hình Windows, lấy cảm hứng từ Calcifer (fan-art tự vẽ bằng code). Ngọn lửa đi lại, bay, nhảy quanh màn hình, phản ứng khi bạn click/kéo, và mở bong bóng chat (chuột phải → `Chat`) để trò chuyện với một AI agent biết gọi công cụ: xem thời tiết, tìm kiếm web, xem tình trạng máy.

> **Chỉ dùng cá nhân.** Calcifer là nhân vật có bản quyền của Studio Ghibli. Dự án này là fan-art phi thương mại, không dùng bất kỳ hình ảnh/âm thanh gốc nào của phim, và không được phát hành công khai hay thương mại.

## Tính năng

- **Nhân vật vẽ hoàn toàn bằng code** (không cần ảnh): thân lửa 3 lớp đỏ/cam/vàng viền nâu đậm, có quầng sáng và tàn lửa bay. Mặc định vẽ thân lửa bằng GPU shader; tự chuyển sang cách vẽ dự phòng nếu máy không hỗ trợ OpenGL 3.3.
- **Khuôn mặt và dáng người có cảm xúc**: chớp mắt, đảo mắt nhìn theo chuột, mí mắt, lông mày, miệng nói; vui (hai kiểu mặt), ngạc nhiên, hoảng hốt, tức giận, chill (rán trứng bằng chảo trên đầu), ghê (`yuck`), suy nghĩ, cảnh báo. Mỗi biểu cảm còn đổi cả hình dáng ngọn lửa.
- **Tự di chuyển**: đứng yên, đi dọc đáy màn hình, cưỡi khúc củi bay lượn, nhảy — chọn ngẫu nhiên.
- **Ngủ**: chọn `Idle` thì pet nằm ngủ (thở chậm, bay chữ "z"); sau 10 phút không đụng chuột/bàn phím pet tự ngủ gật, dùng máy lại thì tỉnh.
- **Ban đêm**: từ 20h đến 5h sáng lửa dịu và trầm màu hơn, pet cử động chậm hơn.
- **Luôn nổi trên cùng, trong suốt, click xuyên qua**: chỉ phần có hình nhân vật mới nhận chuột, vùng xung quanh vẫn bấm được vào app bên dưới.
- **Tương tác chuột**: click trái → một hoạt ảnh ngẫu nhiên (không lặp lại hai lần liền); giữ và kéo → mang nhân vật đi; chuột phải → menu nhỏ `Chat` và `Idle` / `Wander`.
- **Bong bóng thoại đi theo pet** khi nó di chuyển.
- **Chat với AI agent** (LangGraph + Google Gemini `gemini-flash-latest`), trả lời theo ngôn ngữ bạn gõ, tự chọn cảm xúc cho mỗi câu trả lời (pet làm mặt đó vài giây), có 3 công cụ:
  - `weather` — thời tiết theo địa danh (Open-Meteo, không cần key)
  - `web_search` — tìm kiếm web (Tavily)
  - `system_status` — CPU / RAM / pin hiện tại
  - (hẹn giờ nhắc việc tạm tắt)
- **Bong bóng chat** tông màu lửa, gắn cạnh pet (pet đứng yên khi bong bóng mở), hiển thị Markdown, Esc để đóng, tự đóng sau 30 giây không chat (không tính lúc đang gõ hoặc AI đang trả lời).
- **Báo lỗi dễ hiểu**: thiếu/sai key, hết quota, mất mạng… đều được pet giải thích trong chat thay vì im lặng hay crash.
- **Theo dõi máy nền**: tự cảnh báo khi pin < 30%, CPU > 90% hoặc RAM > 90%; cảnh báo giữ nguyên đến khi bạn click vào pet.
- **Câu nói ngẫu nhiên**: sau 15 phút không tương tác, pet tự nói một fact/câu đùa (tiếng Anh).
- **Lịch sử chat chỉ nằm trong RAM**, tự xóa sau 15 phút không chat — không lưu gì xuống ổ đĩa.
- **Icon ở khay hệ thống** (vẽ chính hình pet): `Hide Pet` / `Show Pet`, `Settings` (tạm để trống), `Quit App`.
- **Chỉ chạy 1 bản**: mở app lần nữa sẽ chỉ mở bong bóng chat của con pet đang chạy.

## Yêu cầu

- Windows 10/11, 1 màn hình.
- Python 3.13 (bản Windows).
- Card đồ họa hỗ trợ OpenGL 3.3 (không bắt buộc — thiếu thì dùng cách vẽ dự phòng).
- API key:
  - `GEMINI_API_KEY` — lấy tại [Google AI Studio](https://aistudio.google.com/apikey) (bắt buộc cho chat; thiếu key thì pet vẫn chạy, chỉ chat không dùng được).
  - `TAVILY_API_KEY` — lấy tại [tavily.com](https://tavily.com) (cho công cụ tìm kiếm web).

## Cài đặt

Mở PowerShell trong thư mục dự án:

```powershell
py -3.13 -m venv .venv-win
.venv-win\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env      # rồi mở .env và điền 2 API key
```

## Chạy

```powershell
.venv-win\Scripts\python.exe src\main.py
```

Tự khởi động cùng Windows (tạo shortcut trong thư mục Startup, chạy bằng `pythonw.exe` nên không hiện cửa sổ console):

```powershell
.venv-win\Scripts\python.exe src\autostart\install_startup.py
```

Muốn bỏ tự khởi động: xóa `Calcifer.lnk` trong `shell:startup` (gõ `shell:startup` vào hộp thoại Run).

Có lỗi gì thì xem file log: `%LOCALAPPDATA%\Calcifer\logs\calcifer.log`.

## Cách dùng

| Thao tác | Kết quả |
|---|---|
| Click trái vào pet | Một hoạt ảnh ngẫu nhiên; nếu đang cảnh báo thì chỉ tắt cảnh báo |
| Giữ chuột trái và kéo | Mang pet đi chỗ khác |
| Chuột phải vào pet | Menu: `Chat` (mở bong bóng chat), `Idle` (đi ngủ) / `Wander` (đi lại tiếp) |
| Esc trong bong bóng chat | Đóng chat (lịch sử vẫn giữ trong 15 phút) |
| Icon ở khay hệ thống | Ẩn/hiện pet, Settings, thoát app |

## Cấu hình

Các cài đặt không bí mật nằm trong [`config.yaml`](./config.yaml):

| Khóa | Ý nghĩa |
|---|---|
| `llm.model`, `llm.temperature` | Model Gemini dùng cho chat (mặc định `gemini-flash-latest`) |
| `llm.timeout_seconds`, `llm.max_retries` | Chờ bao lâu / thử lại mấy lần trước khi báo lỗi |
| `character.scale` | Kích thước nhân vật (0.75 = 150×177 px) |
| `character.fps` | Số khung hình/giây; giảm xuống 30 để tiết kiệm CPU |
| `character.flame_renderer` | Cách vẽ thân lửa: `shader` (mặc định, GPU) / `metaball` / `baked` |
| `behavior.state_weights` | Tỉ lệ chọn đứng yên / đi / bay / nhảy |
| `system_status.*` | Chu kỳ kiểm tra máy và ngưỡng cảnh báo |
| `ambient.random_fact_or_joke.idle_minutes` | Bao lâu không tương tác thì pet tự nói |
| `chat.reply_bubble_max_chars` | Câu trả lời ngắn hơn số ký tự này hiện cả trong bong bóng (0 = tắt) |
| `memory.idle_timeout_minutes` | Bao lâu không chat thì xóa lịch sử |

Câu thoại khi click và kho fact/joke nằm trong `data/click_reactions.json` và `data/facts_jokes.json` (luôn viết bằng tiếng Anh).

## Phát triển

Repo dùng 2 môi trường ảo (đều không đưa lên git):

- `.venv-win` — Python Windows, dùng để chạy app thật. Từ WSL vẫn gọi được: cửa sổ sẽ mở trên desktop Windows.
- `.venv` — Python Linux (tùy chọn), chỉ để xem nhanh animation qua WSLg; không dùng để đánh giá độ trong suốt / click xuyên qua.

```bash
.venv-win/Scripts/python.exe -m pip install -r requirements-dev.txt  # cài thêm pytest + ruff
.venv-win/Scripts/python.exe -m pytest                            # chạy test (không cần màn hình)
.venv-win/Scripts/python.exe -m ruff check .                      # kiểm tra code
.venv-win/Scripts/python.exe src/character_preview.py [renderer]  # thử mọi biểu cảm/chuyển động, so sánh cách vẽ lửa
.venv-win/Scripts/python.exe src/bake_flame.py                    # tạo lại dữ liệu lửa cho renderer `baked`
QT_QPA_PLATFORM=offscreen WSLENV=QT_QPA_PLATFORM .venv-win/Scripts/python.exe src/main.py  # chạy thử không cần màn hình
```

Ghi chú:

- `src/` là thư mục gốc khi import (`import config`, `from overlay.x import ...`).
- Khi gọi Python Windows từ WSL, biến môi trường chỉ được chuyển sang nếu khai báo trong `WSLENV` (như ví dụ trên).
- Giữ nguyên kiểu xuống dòng (CRLF hoặc LF) sẵn có của từng file khi sửa.
- Chưa có bản đóng gói `.exe` (để giai đoạn sau).

## Cấu trúc thư mục

```
src/
├── main.py                 # điểm khởi động, nối mọi thành phần bằng Qt signal
├── config.py               # đọc config.yaml + .env
├── app_logging.py          # ghi log ra file
├── single_instance.py      # chỉ cho chạy 1 bản
├── character_preview.py    # cửa sổ xem thử nhân vật
├── bake_flame.py           # mô phỏng lửa offline cho renderer `baked`
├── overlay/                # cửa sổ pet, nhân vật, khuôn mặt, 3 cách vẽ lửa, hành vi, bong bóng thoại
├── chat/                   # bong bóng chat
├── agent/                  # LangGraph agent, công cụ, bộ nhớ phiên, xử lý lỗi
├── monitor/                # theo dõi máy, hẹn giờ nhắc, câu nói ngẫu nhiên, thời gian rảnh / ban đêm
├── ui/                     # menu theo phong cách pet, icon khay, cửa sổ Settings
└── autostart/              # tạo shortcut khởi động cùng Windows
tests/                      # test tự động (pytest)
docs/                       # tài liệu thiết kế (tiếng Việt)
data/                       # câu thoại click + kho fact/joke
assets/flame/               # dữ liệu lửa đã tính sẵn cho renderer `baked`
```

## Tài liệu thiết kế

- [`docs/CONTEXT.md`](./docs/CONTEXT.md) — mục tiêu, kiến trúc, các quyết định kỹ thuật đã chốt, lịch sử thay đổi.
- [`docs/implementation_plan.md`](./docs/implementation_plan.md) — tiến độ và **kế hoạch các bước tiếp theo**.
- [`docs/DECISION_LOG.md`](./docs/DECISION_LOG.md) — nhật ký các quyết định đã chốt (và những việc còn bàn).
- [`CLAUDE.md`](./CLAUDE.md) — hướng dẫn cho AI coding agent làm việc trong repo.
- [`docs/ANIMATION_TUTORIAL.md`](./docs/ANIMATION_TUTORIAL.md) — hướng làm bằng ảnh PNG cũ, đã bỏ, chỉ giữ để tham khảo.

## Trạng thái hiện tại (2026-11-12)

- Nhân vật, chuyển động, click/kéo, khay hệ thống, theo dõi máy, chat với 4 công cụ: đã chạy (chat đã chuyển sang `gemini-flash-latest` sau khi Google ngừng `gemini-2.0-flash`).
- Mới: bong bóng chat, bộ hoạt ảnh khi click, menu chuột phải, biểu cảm mới do AI chọn cảm xúc, bay trên khúc củi, ngủ / ngủ gật, dáng vẻ ban đêm, icon khay vẽ từ nhân vật.
- Có 85 test tự động và kiểm tra code bằng ruff.
- Còn lại: dùng thử lâu dài trên desktop thật; nội dung Settings và tay thật (E3) (đang chờ quyết định); đóng gói `.exe` (để sau).
