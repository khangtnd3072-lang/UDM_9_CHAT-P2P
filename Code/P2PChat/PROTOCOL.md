# P2P Chat Protocol

## 1. Packet Format

Dữ liệu được truyền qua TCP theo cấu trúc:

[4-byte Length Prefix][JSON Payload]

- Length Prefix: 4 bytes, Big Endian.
- JSON Payload: dữ liệu message được mã hóa UTF-8.

## 2. Message Format

Message chat có cấu trúc:

{
  "type": "chat",
  "sender": "khang",
  "receiver": "an",
  "message": "Xin chào",
  "protocol_version": "1.0",
  "message_id": "UUID",
  "timestamp": "2026-08-21T15:28:15.408995+00:00"
}

## 3. Message Fields

| Field | Type | Description |
|---|---|---|
| type | string | Loại message |
| sender | string | Tên người gửi |
| receiver | string | Tên người nhận |
| message | string | Nội dung tin nhắn |
| protocol_version | string | Phiên bản protocol |
| message_id | string | ID duy nhất của message |
| timestamp | string | Thời gian tạo message theo UTC |

## 4. Message ID

`message_id` được tự động tạo bằng UUID cho mỗi message.

Ví dụ:

1f444759-1e84-47ed-9b53-b24ee1f03657

## 5. Timestamp

`timestamp` được tạo theo ISO 8601 và sử dụng UTC.

Ví dụ:

2026-08-21T15:28:15.408995+00:00

## 6. Message Types

Protocol hiện hỗ trợ:

- chat
- text
- system
- ack

Trong ứng dụng hiện tại, `node.py` sử dụng message type `chat`.

## 7. Packet Size Limit

Kích thước JSON payload tối đa:

131072 bytes (128 KiB)

Nếu vượt quá giới hạn, `encode_message()` và `decode_message()` sẽ báo lỗi.

## 8. Error Handling

Protocol xử lý các lỗi:

- Socket đóng trước khi nhận đủ dữ liệu.
- Payload có kích thước không hợp lệ.
- Payload vượt quá giới hạn.
- UTF-8 không hợp lệ.
- JSON không hợp lệ.
- Thiếu trường bắt buộc.
- Message type không được hỗ trợ.

## 9. Encode Flow

Message Dictionary
        |
        v
Add Metadata
        |
        v
Validate
        |
        v
JSON + UTF-8
        |
        v
4-byte Length Prefix
        |
        v
TCP Socket

## 10. Decode Flow

TCP Socket
        |
        v
Read 4-byte Length
        |
        v
Validate Length
        |
        v
Read JSON Payload
        |
        v
UTF-8 Decode
        |
        v
JSON Decode
        |
        v
Validate Message
        |
        v
Message Dictionary

## 11. Testing

Đã kiểm tra thành công:

- Encode message thông thường.
- Decode message qua TCP socket.
- Truyền Unicode tiếng Việt.
- Tự động tạo `message_id`.
- Tự động tạo `timestamp`.
- Kiểm tra message thiếu `type`.
- Kiểm tra message type không hợp lệ.
- Kiểm tra payload vượt quá 131072 bytes.

Kết quả: PASS.