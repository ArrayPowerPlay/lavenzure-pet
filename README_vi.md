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

- **Sống trên màn hình**: luôn nằm trên cùng, trong suốt, chuột xuyên qua mọi chỗ trừ ngọn lửa. Nó đứng yên, đi dạo, cưỡi củi bay, nhảy, ngủ gật sau 10 phút bạn không đụng máy, và dịu lại vào ban đêm.
- **Biểu cảm**: ngọn lửa vẽ bằng shader GPU cùng khuôn mặt có "diễn xuất" thật (mắt nhìn theo con trỏ chuột; vui, ngạc nhiên, sợ, giận, chill, buồn ngủ…).
- **Chat với AI agent** (Google Gemini hoặc OpenAI, bạn chọn) có sẵn công cụ **thời tiết**, **tìm kiếm web**, **tình trạng máy** (CPU / RAM / pin) và **nhắc việc** ("nhắc tôi lúc 11:00 làm…").
- **Quan tâm bạn**: cảnh báo khi pin, CPU hoặc RAM ở mức nguy hiểm; cứ 5 phút lại nói một câu quan tâm, một sự thật thú vị hoặc một câu đùa.
- **Tiếng Anh hoặc tiếng Việt** cho mọi câu nó nói (trong Settings).
- **Riêng tư**: cuộc trò chuyện chỉ nằm trong RAM, khóa API được cất trong Windows Credential Manager.

## Tải về và chạy (Windows 10/11)

1. Tải `Lavenzure-<phiên bản>-win-x64.zip` ở trang [Releases](../../releases) rồi giải nén vào thư mục bất kỳ.
2. Bấm đúp `Lavenzure.exe`. Pet hiện ra và có thêm một biểu tượng ở khay hệ thống.
3. Chuột phải biểu tượng khay → **Settings**, chọn **Chat AI** rồi dán khóa API của nó. Khóa được kiểm tra trước, rồi mới lưu, và dùng được ngay.
   - **Gemini**: lấy khóa miễn phí ở [Google AI Studio](https://aistudio.google.com/apikey).
   - **OpenAI**: lấy khóa ở [OpenAI platform](https://platform.openai.com/api-keys).
   - **Tavily** (tùy chọn, để tìm kiếm web): [tavily.com](https://tavily.com).
4. Tùy chọn: bật **Start with Windows** trong Settings.

Chưa có khóa thì pet vẫn chạy bình thường; chỉ phần chat cần khóa.

> **Windows có thể cảnh báo** ("Windows protected your PC") vì app chưa được ký số. Bấm **More info → Run anyway**. Mỗi bản phát hành đều kèm mã SHA-256 của file zip để bạn kiểm tra file tải về (`Get-FileHash Lavenzure-<phiên bản>-win-x64.zip`).

## Cách dùng

| Thao tác | Kết quả |
|---|---|
| Click chuột trái | Một phản ứng ngẫu nhiên (cũng tắt cảnh báo / nhắc việc đang chờ) |
| Nhấn giữ và kéo | Bế pet sang chỗ khác |
| Chuột phải | `Chat`, `Idle` (ngủ) / `Wander` (đi lại), `Hide Pet` (ẩn) |
| Biểu tượng khay | `Settings` (ngôn ngữ, Chat AI và khóa, chạy cùng Windows, tốc độ khung hình), `Show Pet`, `Quit App` |

File log ở `%LOCALAPPDATA%\Lavenzure\logs\lavenzure.log`.

## Chạy từ mã nguồn

Cần Python 3.13 trên Windows.

```powershell
py -3.13 -m venv .venv-win
.venv-win\Scripts\python.exe -m pip install -r requirements.txt
.venv-win\Scripts\python.exe src\main.py
```

Khi phát triển có thể để khóa trong file `.env` thay vì Settings (`copy .env.example .env`); khóa trong `.env` hoặc biến môi trường sẽ đè lên khóa đã lưu.

```powershell
.venv-win\Scripts\python.exe -m pip install -r requirements-dev.txt   # pytest, ruff, pyinstaller
.venv-win\Scripts\python.exe -m pytest                                 # chạy test (không cần màn hình)
.venv-win\Scripts\python.exe -m ruff check .                           # kiểm tra lint
.venv-win\Scripts\python.exe scripts\build.py                          # tạo dist\Lavenzure-<phiên bản>-win-x64.zip
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
