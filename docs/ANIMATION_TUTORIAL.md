# Hướng dẫn: Cutout/Rigging Animation bằng code (không cần phần mềm vẽ hoạt ảnh)

> **Đã thay thế (2026-11-11):** nhân vật hiện được vẽ hoàn toàn bằng code trong `src/overlay/character.py`, không dùng PNG nữa. File này chỉ giữ lại để tham khảo.

> Mục tiêu: tạo chuyển động mượt cho Calcifer chỉ từ vài ảnh PNG tĩnh + code Python (PySide6), không cần biết vẽ hoạt ảnh, không cần After Effects/Spine/DragonBones.

## 1. Ý tưởng cốt lõi

Thay vì vẽ hàng chục frame cho mỗi động tác (cách làm truyền thống, cần kỹ năng vẽ), ta **cắt nhân vật thành các bộ phận rời (layer)**, xếp chồng chúng lên nhau, rồi dùng code để **di chuyển/xoay/co giãn từng bộ phận theo thời gian** (giống cách rối bóng/stop-motion cắt giấy hoạt động, hoặc cách Live2D/Spine hoạt động — nhưng ở đây ta tự lập trình phần "rig" thay vì dùng phần mềm chuyên dụng).

Ví dụ: để nháy mắt, ta không cần vẽ animation — chỉ cần 2 ảnh "mắt mở" và "mắt nhắm", code sẽ tự đổi ảnh qua lại theo timer.

Để "thở"/bồng bềnh, ta không cần vẽ gì thêm — chỉ cần code dịch chuyển layer thân lên xuống vài pixel theo hàm sin/easing.

## 2. Danh sách layer cần tách từ ảnh Calcifer

Từ ảnh fan art bạn có, dùng công cụ tách nền (xem mục 3) để tạo các file PNG **nền trong suốt (alpha channel)** sau, đặt trong `assets/calcifer/`:

| File | Mô tả | Dùng cho animation nào |
|---|---|---|
| `body_base.png` | Thân lửa chính (không có mắt/miệng/ngọn lửa đỉnh đầu) | Idle bob, walk, jump, drag stretch |
| `eye_left_open.png` / `eye_left_closed.png` | Mắt trái, 2 trạng thái | Chớp mắt (blink) |
| `eye_right_open.png` / `eye_right_closed.png` | Mắt phải, 2 trạng thái | Chớp mắt |
| `mouth_closed.png` / `mouth_open.png` | Miệng, 2 trạng thái (có thể thêm `mouth_smile.png`, `mouth_shock.png` cho phản ứng click) | Lip-flap khi "nói chuyện" trong chat, phản ứng khi click |
| `flame_top.png` | Ngọn lửa/tóc lửa phía trên đầu | Lập lòe (flicker) liên tục |
| `log.png` (tuỳ chọn) | Khúc gỗ Calcifer ôm (nếu ảnh gốc có) | Lắc nhẹ theo nhịp thở |

> Bạn không bắt buộc phải có đủ tất cả — tối thiểu cần `body_base.png` + 1 cặp mắt + 1 cặp miệng + `flame_top.png` là đã animate được khá sống động rồi. Có thể bổ sung dần.

## 3. Cách tách layer (không cần vẽ, chỉ cần "cắt/xóa nền")

Vì bạn không có kinh nghiệm phần mềm animation, đây là quy trình chỉ cần thao tác cắt/xóa nền cơ bản:

1. **Công cụ đề xuất** (miễn phí, không cần cài đặt):
   - [Photopea](https://www.photopea.com/) — giống Photoshop chạy trên trình duyệt, có công cụ Magic Wand/Eraser để xóa nền và tách vùng.
   - [remove.bg](https://www.remove.bg/) — xóa nền tự động bằng AI, chỉ cần upload ảnh, tải về PNG nền trong suốt (dùng để tách nhanh toàn bộ nhân vật khỏi nền trắng/be trước, sau đó mới cắt tiếp từng bộ phận trong Photopea).
   - GIMP (cài đặt) nếu bạn muốn công cụ mạnh hơn, cũng miễn phí.

2. **Quy trình từng bước (dùng Photopea)**:
   - Mở ảnh Calcifer trong Photopea.
   - Dùng công cụ **Magic Wand** (đũa thần) hoặc **Lasso** để chọn từng bộ phận (mắt, miệng, ngọn lửa...).
   - `Ctrl+J` để copy vùng chọn ra layer riêng.
   - Ẩn/xóa layer nền, chỉ giữ lại layer bộ phận đó.
   - `File > Export As > PNG` (đảm bảo tick giữ transparency) → lưu đúng tên file theo bảng ở mục 2.
   - Lặp lại cho từng bộ phận. Với mắt/miệng, bạn cần **vẽ đè hoặc chỉnh sửa nhẹ** phần thân bên dưới (dùng Clone Stamp/vá) để khi ẩn mắt/miệng đi, `body_base.png` vẫn liền mạch không bị lỗ hổng.
   - Với trạng thái thứ 2 (mắt nhắm, miệng mở...): nếu ảnh gốc không có sẵn, cách đơn giản nhất là **dùng biến đổi hình học** trên chính layer đó (ví dụ ép dẹt layer mắt theo chiều dọc ~90% để giả lập mắt nhắm, hoặc kéo giãn miệng để giả lập miệng mở) — không cần vẽ lại từ đầu.

3. **Quy ước đặt tên & kích thước**: tất cả layer nên xuất cùng kích thước canvas (ví dụ 512x512px) và cùng hệ toạ độ gốc, để khi ghép lại trong code, các layer tự động thẳng hàng mà không cần tính offset thủ công phức tạp.

## 4. Ghép layer & animate bằng code (PySide6)

### 4.1. Cấu trúc widget

Dùng 1 `QWidget` overlay trong suốt làm canvas, bên trong đặt các `QLabel` (mỗi label 1 layer PNG), xếp chồng theo `z-order` bằng thứ tự `raise_()`/`stackUnder()`, định vị bằng `move(x, y)` tuyệt đối trong widget cha.

```python
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QPoint

class CalciferSprite(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.body = self._make_layer("assets/calcifer/body_base.png", QPoint(0, 0))
        self.eye_l = self._make_layer("assets/calcifer/eye_left_open.png", QPoint(40, 60))
        self.eye_r = self._make_layer("assets/calcifer/eye_right_open.png", QPoint(90, 60))
        self.mouth = self._make_layer("assets/calcifer/mouth_closed.png", QPoint(60, 100))
        self.flame = self._make_layer("assets/calcifer/flame_top.png", QPoint(20, -20))

        # thứ tự chồng lớp: flame dưới cùng (phía sau đầu), rồi body, rồi mắt/miệng trên cùng
        self.flame.lower()
        self.body.stackUnder(self.eye_l)

    def _make_layer(self, path: str, pos: QPoint) -> QLabel:
        label = QLabel(self)
        label.setPixmap(QPixmap(path))
        label.move(pos)
        label.setAttribute(Qt.WA_TranslucentBackground)
        label.show()
        return label
```

### 4.2. Chớp mắt (frame-swap đơn giản)

```python
import random
from PySide6.QtCore import QTimer

def schedule_next_blink(sprite: CalciferSprite):
    delay_ms = random.randint(2000, 6000)  # chớp mắt ngẫu nhiên mỗi 2-6 giây
    QTimer.singleShot(delay_ms, lambda: do_blink(sprite))

def do_blink(sprite: CalciferSprite):
    sprite.eye_l.setPixmap(QPixmap("assets/calcifer/eye_left_closed.png"))
    sprite.eye_r.setPixmap(QPixmap("assets/calcifer/eye_right_closed.png"))
    QTimer.singleShot(150, lambda: (
        sprite.eye_l.setPixmap(QPixmap("assets/calcifer/eye_left_open.png")),
        sprite.eye_r.setPixmap(QPixmap("assets/calcifer/eye_right_open.png")),
        schedule_next_blink(sprite),
    ))
```

### 4.3. Idle bob (bồng bềnh lên xuống) bằng QPropertyAnimation

```python
from PySide6.QtCore import QPropertyAnimation, QEasingCurve

def start_idle_bob(sprite: CalciferSprite):
    anim = QPropertyAnimation(sprite, b"pos")
    anim.setDuration(1200)
    anim.setStartValue(sprite.pos())
    anim.setKeyValueAt(0.5, sprite.pos() + QPoint(0, -8))  # nhích lên 8px
    anim.setEndValue(sprite.pos())
    anim.setEasingCurve(QEasingCurve.InOutSine)
    anim.setLoopCount(-1)  # lặp vô hạn
    anim.start()
    sprite._idle_anim = anim  # giữ reference để không bị garbage-collected
```

### 4.4. Lửa lập lòe (flicker) bằng scale/opacity dao động

```python
from PySide6.QtWidgets import QGraphicsOpacityEffect

def start_flame_flicker(sprite: CalciferSprite):
    effect = QGraphicsOpacityEffect(sprite.flame)
    sprite.flame.setGraphicsEffect(effect)
    anim = QPropertyAnimation(effect, b"opacity")
    anim.setDuration(400)
    anim.setStartValue(0.85)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.InOutQuad)
    anim.setLoopCount(-1)
    anim.start()
    sprite._flame_anim = anim
```

### 4.5. Nói chuyện (lip-flap) khi agent đang trả lời

```python
def start_talking(sprite: CalciferSprite):
    sprite._talk_timer = QTimer()
    state = {"open": False}
    def toggle():
        state["open"] = not state["open"]
        path = "mouth_open.png" if state["open"] else "mouth_closed.png"
        sprite.mouth.setPixmap(QPixmap(f"assets/calcifer/{path}"))
    sprite._talk_timer.timeout.connect(toggle)
    sprite._talk_timer.start(180)  # đổi miệng mỗi 180ms trong lúc "nói"

def stop_talking(sprite: CalciferSprite):
    sprite._talk_timer.stop()
    sprite.mouth.setPixmap(QPixmap("assets/calcifer/mouth_closed.png"))
```

### 4.6. Squash & stretch khi nhảy/kéo thả (hiệu ứng "cao su")

```python
def squash_stretch(sprite: CalciferSprite, stretch: bool):
    # stretch=True: kéo dài theo chiều đứng lúc bật nhảy lên
    # stretch=False: dẹt theo chiều ngang lúc chạm đất (squash)
    sy = 1.15 if stretch else 0.85
    sx = 0.9 if stretch else 1.15
    sprite.body.resize(int(sprite.body.width() * sx), int(sprite.body.height() * sy))
```

> Ghi chú: cách đơn giản này resize trực tiếp `QLabel`. Nếu muốn mượt hơn (scale mượt dần thay vì đổi tức thì), có thể bọc `body` trong `QGraphicsView`/`QGraphicsPixmapItem` và animate thuộc tính `scale` bằng `QPropertyAnimation` tương tự mục 4.3.

### 4.7. Di chuyển (walk / float / jump)

- **Walk** (đi dọc mép màn hình): animate thuộc tính `pos` theo trục X, giữ nguyên Y = mép dưới màn hình, tốc độ đều (easing `Linear`), đổi hướng ngẫu nhiên sau vài giây.
- **Float** (bay lơ lửng tự do): animate `pos` tới 1 điểm ngẫu nhiên trong màn hình, easing `InOutQuad` để mượt, lặp lại chọn điểm mới khi tới đích.
- **Jump** (nhảy): kết hợp animate `pos` theo trục Y dạng parabol (chia nhiều `setKeyValueAt` mô phỏng quỹ đạo rơi) + gọi `squash_stretch()` ở đầu (nhảy lên) và cuối (chạm đất).

Tất cả đều dùng chung 1 kỹ thuật: `QPropertyAnimation` trên `pos`/`geometry` + `QEasingCurve` — không cần vẽ frame nào thêm.

## 5. Behavior State Machine — cách phối các animation trên

```python
import random
from enum import Enum, auto

class PetState(Enum):
    IDLE = auto()
    WALK = auto()
    FLOAT = auto()
    JUMP = auto()
    DRAGGED = auto()
    REACT = auto()
    ALERT = auto()  # system_status cảnh báo

def pick_next_state() -> PetState:
    return random.choices(
        [PetState.IDLE, PetState.WALK, PetState.FLOAT, PetState.JUMP],
        weights=[0.4, 0.25, 0.25, 0.1],
    )[0]
```

Vòng lặp chính: mỗi khi 1 animation di chuyển kết thúc (idle/walk/float/jump), gọi `pick_next_state()` để chọn trạng thái tiếp theo, trừ khi đang bị `DRAGGED`/`REACT`/`ALERT` (các trạng thái này được kích hoạt bởi sự kiện chuột hoặc background monitor, có độ ưu tiên cao hơn vòng lặp ngẫu nhiên).

## 6. Vì sao cách này đủ dùng mà không cần Live2D/Spine/DragonBones

- Không cần học giao diện phần mềm rig chuyên dụng.
- Toàn bộ chuyển động là **code Python thuần** — dễ debug, dễ chỉnh tốc độ/độ mượt bằng cách sửa số (duration, easing curve) thay vì phải mở lại phần mềm vẽ.
- Đủ mượt cho một desktop pet cá nhân vì mắt người khó nhận ra sự khác biệt giữa "cutout rig" và animation frame-by-thật sự khi chuyển động đủ nhanh (>15-20 lần cập nhật/giây, Qt animation mặc định làm được).
- Nếu sau này muốn nâng cấp: hoàn toàn có thể thay `assets/calcifer/*.png` bằng bộ layer chi tiết hơn mà không cần đổi code animation logic.

## 7. Việc bạn cần làm

- [ ] Chuẩn bị (tách) các file PNG theo bảng ở mục 2, đặt đúng tên vào `assets/calcifer/`.
- [ ] Nếu thiếu bộ layer thứ 2 (mắt nhắm, miệng mở...), có thể để tôi hỗ trợ tạo bằng biến đổi hình học từ layer gốc trong code (không cần vẽ thêm) — báo tôi biết khi tới Phase 3.
