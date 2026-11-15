<p align="center">
  <img src="docs/images/hero.png" alt="Ngọn lửa cười toe, mắt nhìn lên" width="260">
</p>

<h1 align="center">Lavenzure Desktop Pet</h1>

<p align="center">
  <em>Một con quỷ lửa bé xíu dọn đến sống trên màn hình của bạn, và chẳng bao giờ chịu ngồi yên.</em><br>
  <b>Tiếng Việt</b> · <a href="./README.md">English</a>
</p>

---

Lavenzure là một linh hồn lửa nhỏ bằng bàn tay, sống nổi trên mọi cửa sổ của bạn. Nó đi dạo, nhún nhảy, ngủ gật khi bạn rời máy và phản ứng khi bạn click hay nhấc nó lên. Chuột phải để chat: một AI trả lời theo ngôn ngữ bạn gõ, xem thời tiết, tìm kiếm web, nhắc việc, và mỗi câu trả lời lại đi kèm một nét mặt hợp cảnh.

<p align="center">
  <img src="docs/images/expressions.png" alt="Các biểu cảm: bình thường, vui, ngạc nhiên, sợ, giận, chill với chảo rán, ghê, ngủ, cưỡi khúc củi">
</p>

**Nhân vật này không dùng một file ảnh nào.** Ngọn lửa, từng cái chớp mắt, từng nụ cười đều được vẽ bằng code, trực tiếp, và không bao giờ lặp lại cùng một khung hình.

## Tính năng

- **Sống trên màn hình**: Luôn nằm trên cùng, trong suốt, chuột xuyên qua mọi chỗ trừ ngọn lửa. Nó đứng yên, đi dạo, cưỡi củi bay, nhảy, ngủ gật sau 10 phút bạn không đụng máy, và dịu lại vào ban đêm.
- **Biểu cảm**: Ngọn lửa vẽ bằng shader GPU cùng khuôn mặt có "diễn xuất" thật (mắt nhìn theo con trỏ chuột; vui, ngạc nhiên, sợ, giận, chill, buồn ngủ…).
- **Chat với AI agent** (Google Gemini hoặc OpenAI, bạn chọn) có sẵn công cụ **thời tiết**, **tìm kiếm web**, **tình trạng máy** (CPU / RAM / pin) và **nhắc việc** ("nhắc tôi lúc 11:00 làm…").
- **Quan tâm bạn**: Cảnh báo khi pin, CPU hoặc RAM ở mức nguy hiểm; cứ 5 phút lại nói một câu quan tâm, một sự thật thú vị hoặc một câu đùa.
- **Tiếng Anh hoặc tiếng Việt** cho mọi câu nó nói (trong Settings).
- **Nhiều trang phục** (Settings → Outfit): Bạn chọn bộ đồ cho pet. Phiên bản hiện tại có **trang phục Giáng sinh** (khăn len, khúc gỗ phủ tuyết và lời chúc mừng) bên cạnh diện mạo thường, và sẽ có thêm các trang phục khác.
- **Riêng tư**: Cuộc trò chuyện chỉ nằm trong RAM, khóa API được cất trong Windows Credential Manager.

## Tải về và chạy (Windows 10/11)

1. Tải `Lavenzure-<phiên bản>-win-x64.zip` ở trang [Releases](../../releases) rồi giải nén vào thư mục bất kỳ.
2. Bấm đúp `Lavenzure.exe`. Pet hiện ra và có thêm một biểu tượng ở khay hệ thống.
3. Chuột phải biểu tượng khay → **Settings**, chọn **Chat AI** rồi dán khóa API của nó. Khóa được kiểm tra trước, rồi mới lưu, và dùng được ngay.
   - **Gemini**: Lấy khóa miễn phí ở [Google AI Studio](https://aistudio.google.com/apikey).
   - **OpenAI**: Lấy khóa ở [OpenAI platform](https://platform.openai.com/api-keys).
   - **Tavily** (tùy chọn, để tìm kiếm web): [tavily.com](https://tavily.com).
4. Tùy chọn: Bật **Start with Windows** trong Settings.

Chưa có khóa thì pet vẫn chạy bình thường; chỉ phần chat cần khóa.

> **Windows có thể cảnh báo** ("Windows protected your PC") vì app chưa được ký số. Bấm **More info → Run anyway**. Mỗi bản phát hành đều kèm mã SHA-256 của file zip để bạn kiểm tra file tải về (`Get-FileHash Lavenzure-<phiên bản>-win-x64.zip`).

## Hướng dẫn sử dụng

### 1. Làm quen với pet

| Thao tác | Kết quả |
|---|---|
| Click chuột trái | Pet phản ứng lại. Cũng tắt cảnh báo hoặc nhắc việc đang chờ |
| Nhấn giữ và kéo | Bế pet sang chỗ khác |
| Chuột phải | Mở menu của pet |

Cứ để yên, pet sẽ tự đi lại. Mắt pet nhìn theo con trỏ chuột.

### 2. Menu của pet (chuột phải vào pet)

| Mục | Tác dụng |
|---|---|
| **Chat** | Mở bong bóng chat |
| **Idle** / **Wander** | Cho pet đi ngủ, hoặc đánh thức pet để đi lại tiếp |
| **Hide Pet** | Ẩn pet (pet vẫn làm việc ngầm) |

### 3. Biểu tượng ở khay hệ thống (góc phải dưới thanh taskbar)

Pet có một biểu tượng nhỏ ở khay hệ thống. Trên Windows 11 biểu tượng có thể nằm sau mũi tên **^**. Bấm chuột phải vào biểu tượng:

| Mục | Tác dụng |
|---|---|
| **Show Pet** | Gọi pet đang bị ẩn ra lại |
| **Settings** | Mở cửa sổ Settings |
| **Quit App** | Tắt Lavenzure |

### 4. Chat

Chuột phải vào pet → **Chat**, gõ tin nhắn rồi nhấn **Enter**. Bạn viết bằng ngôn ngữ nào, pet trả lời bằng ngôn ngữ đó. Nhấn **Esc** hoặc **x** để đóng bong bóng.

Ngoài trò chuyện, pet còn xem được thời tiết, tìm kiếm web (cần khóa Tavily), cho bạn biết tình trạng máy và đặt nhắc việc. Cứ nhờ là được. Chat cần API key (xem Settings → Chat AI); mọi thứ khác chạy được mà không cần khóa.

### 5. Nhắc việc

Nói với pet trong chat, ví dụ **"Nhắc mình lúc 21:00 nộp báo cáo"** hoặc **"Nhắc mình sau 30 phút đứng dậy vận động"**. Mở tab **Reminders** của bong bóng chat để xem hoặc xóa những việc đang chờ. Đến giờ, pet sẽ chạy ra nhắc bạn; click chuột trái vào pet để tắt.

### 6. Cảnh báo và trò chuyện vặt

Nếu pin, CPU hoặc RAM ở mức nguy hiểm, pet sẽ cảnh báo cho đến khi bạn click chuột trái vào pet. Thỉnh thoảng pet cũng tự nói chuyện với bạn.

### 7. Settings (biểu tượng khay → Settings)

| Mục | Tác dụng |
|---|---|
| **Language** | Chọn English hoặc Tiếng Việt cho những gì pet nói |
| **Outfit** | Chọn trang phục của pet (Normal hoặc Giáng sinh) |
| **Chat AI** | Chọn Gemini hoặc OpenAI, dán API key rồi bấm **Save**. Khóa Tavily (tùy chọn) bật tìm kiếm web |
| **Startup** | Cho pet chạy cùng Windows |
| **Performance** | Chọn 30 hoặc 60 fps (30 nhẹ máy hơn) |

### 8. Xử lý sự cố

- **Pet biến mất**: Pet đang bị ẩn. Dùng biểu tượng khay → **Show Pet**.
- **Chat báo lỗi**: Kiểm tra API key trong Settings → Chat AI và kết nối mạng.
- **Việc khác**: Xem file log ở `%LOCALAPPDATA%\Lavenzure\logs\lavenzure.log`.

## Chạy từ mã nguồn

Cần [uv](https://docs.astral.sh/uv/) trên Windows (uv cũng tự cài Python 3.13 cho bạn).

```powershell
uv sync                    # tạo .venv với đúng phiên bản thư viện ghi trong uv.lock
uv run python src\main.py
```

Khi phát triển có thể để khóa trong file `.env` thay vì Settings (`copy .env.example .env`); khóa trong `.env` hoặc biến môi trường sẽ đè lên khóa đã lưu.

```powershell
uv run pytest                           # chạy test (không cần màn hình)
uv run ruff check .                     # kiểm tra lint
uv run python scripts\build.py          # tạo dist\Lavenzure-<phiên bản>-win-x64.zip
uv add <gói>                            # thêm thư viện (cập nhật pyproject.toml và uv.lock)
```

Những thứ hay chỉnh nằm trong [`config.yaml`](./config.yaml) (cỡ nhân vật, tốc độ khung hình, kiểu vẽ lửa, ngưỡng cảnh báo, model AI, tần suất pet nói). Lựa chọn của bạn trong cửa sổ Settings được lưu ở `%LOCALAPPDATA%\Lavenzure\settings.json`.

Bản phát hành được tạo khi đẩy một tag như `v0.1.0` (xem `.github/workflows/release.yml`); số phiên bản luôn lấy từ git tag.

## Cấu trúc dự án

```
src/
├── main.py            # điểm vào; nối mọi thành phần bằng tín hiệu Qt
├── overlay/           # cửa sổ pet, nhân vật, khuôn mặt, các kiểu vẽ lửa, hành vi, bong bóng thoại
├── chat/              # bong bóng chat
├── agent/             # LangGraph agent (Gemini / OpenAI), công cụ, kiểm tra khóa, bộ nhớ phiên
├── monitor/           # cảnh báo hệ thống, nhắc việc, câu tự nói, thời gian rảnh / ban đêm
├── ui/                # menu, biểu tượng khay, cửa sổ Settings
└── api_keys.py, version.py, paths.py, autostart/ ...
tests/  data/  assets/  scripts/  docs/
```

Các tài liệu thiết kế trong [`docs/`](./docs) (quyết định, kế hoạch, checklist kiểm thử) viết bằng tiếng Việt; [`CLAUDE.md`](./CLAUDE.md) và [skill `pet-animation`](./.claude/skills/pet-animation/SKILL.md) hướng dẫn các AI coding agent làm việc trong repo này.

## Giấy phép

Miễn phí và phi thương mại, phát hành theo [giấy phép MIT](./LICENSE). Lavenzure lấy cảm hứng từ Calcifer, nhân vật của Studio Ghibli; đây là sản phẩm hâm mộ không chính thức, không dùng tài nguyên gốc của phim và không liên kết với Studio Ghibli.
