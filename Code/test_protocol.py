from protocol import encode_message


# TEST 1: Message bình thường
message_normal = {
    "type": "chat",
    "sender": "khang",
    "receiver": "tai",
    "message": "Xin chào"
}

try:
    data = encode_message(message_normal)

    print("TEST 1: PASS")
    print("Kích thước:", len(data), "bytes")

except Exception as e:
    print("TEST 1: FAIL")
    print(e)


# TEST 2: Message lớn hơn 1 MB
message_large = {
    "type": "chat",
    "sender": "khang",
    "receiver": "tai",
    "message": "A" * (1024 * 1024 + 1)
}

try:
    encode_message(message_large)

    print("TEST 2: FAIL")
    print("Message lớn nhưng không bị chặn")

except ValueError as e:
    print("TEST 2: PASS")
    print(e)
