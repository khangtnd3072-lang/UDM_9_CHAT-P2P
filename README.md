# UDM_9_CHAT-P2P

Ứng dụng chat P2P (peer-to-peer) không cần server, có mã hóa và giao diện GUI.

---

## Thông tin nhóm

| Thành phần | Thông tin |
|------------|-----------|
| Lớp | 012012301302 |
| Nhóm | Net3_Group_10 — UDM09 |
| Ngôn ngữ | c++ |
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

## Mô tả
Các máy tính trong cùng mạng LAN tự tìm thấy nhau qua UDP broadcast, sau đó kết nối trực tiếp qua TCP để chat.
Không có server trung tâm — mỗi máy vừa là client vừa là server.

Tin nhắn được mã hóa end-to-end: RSA-2048 để trao đổi khóa lúc kết nối, Fernet (AES-128) để mã hóa nội dung trong
suốt phiên chat. Có thể gửi file tối đa 10MB, kiểm tra toàn vẹn bằng SHA-256.
## Chức năng

--



