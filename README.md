# UDM_9_CHAT-P2P

Ứng dụng chat P2P (peer-to-peer) không cần server, có mã hóa và giao diện GUI.

---

## Thông tin nhóm

| Thành phần | Thông tin |
|------------|-----------|
| Lớp | 012012301302 |
| Nhóm | Net3_Group_10 — UDM09 |
| Ngôn ngữ | python |
| Mô hình | Peer-to-Peer |
| Nền tảng | Windows |
| Repo | 012012301302_Net3_Group_10_UDM09 |

## Thành viên

| MSSV | HỌ VÀ TÊN  |
|------------|-----------|
| 054206000426 | Huỳnh Văn Tại |
| 089206018408 | Ngô Đặng Minh Khôi |
| 082206013072 | Trần Ngô Duy Khang |
| 089206018080 | Ngủ Hoàng Khang |
| 040206012006 | Nguyễn Thanh Khánh |
| 051206012692 | Lương Quốc Khánh |

---

## Yêu cầu

- Python 3.10+ được khuyến nghị (một số annotation sử dụng cú pháp mới `|` và `dict[str, ...]`).
- Thư viện phụ thuộc: cài bằng `pip install -r requirements.txt` (hoặc `pip install cryptography`).

## Cài đặt

1. Tạo môi trường ảo (khuyến nghị):

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

2. Cài dependencies:

```bash
pip install -r requirements.txt
```

## Chạy ứng dụng (ví dụ local)

- Chạy server (plaintext):

```bash
python Code/P2PChat/src/node.py --mode server --host 127.0.0.1 --port 5000
```

- Chạy server (secure mode - bật handshake + mã hóa giữa client và server):

```bash
python Code/P2PChat/src/node.py --mode server --host 127.0.0.1 --port 5000 --secure
```

- Chạy client (plaintext):

```bash
python Code/P2PChat/src/node.py --mode client --host 127.0.0.1 --port 5000
```

- Chạy client (secure):

```bash
python Code/P2PChat/src/node.py --mode client --host 127.0.0.1 --port 5000 --secure
```

Trong chế độ `--secure`, client và server sẽ thực hiện handshake RSA để trao session key (Fernet) và mọi message sau đó sẽ được mã hóa.

## Chạy test

Có test đơn giản cho framing và handshake:

```bash
python -m unittest Code/common/test_protocol_handshake.py
```

## Ghi chú bảo mật & vận hành

- Handshake hiện trao session key bằng RSA nhưng KHÔNG có xác thực public-key (không có chữ ký/CA): điều này có thể cho phép MITM trên mạng không tin cậy. Để an toàn hơn, nên bổ sung xác thực fingerprint hoặc chữ ký.
- Không commit private key vào repo. Nếu muốn persistent key, dùng tùy chọn `--keyfile` (chưa có) hoặc lưu file và thêm vào `.gitignore`.
- decode_message có thể ném EOFError/socket.timeout — khi tích hợp vào GUI/daemon cần xử lý ngoại lệ để shutdown/cleanup.
- Kiến trúc hiện repo có module `node.py` dạng relay server; nếu mục tiêu là P2P trực tiếp, cần viết demo peer-to-peer để handshake trực tiếp giữa peers.

---

Nếu bạn muốn mình cập nhật thêm phần hướng dẫn (ví dụ: lưu key, fingerprint verification, tạo script demo P2P), mình sẽ làm tiếp trên branch `add/handshake-scaffold` hoặc mở PR để review.
