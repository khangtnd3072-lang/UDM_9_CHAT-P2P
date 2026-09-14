import unittest

try:
    from message.protocol import _validate_message
except Exception:
    import sys
    sys.path.insert(0, "src")
    from message.protocol import _validate_message


class TestProtocolMessages(unittest.TestCase):

    def test_reply_message(self):
        msg = {
            "protocol_version": "1.0",
            "message_id": "1",
            "timestamp": "2026-09-07T00:00:00",
            "type": "chat",
            "reply_to_id": "msg123"
        }

        _validate_message(msg)

    def test_forward_message(self):
        msg = {
            "protocol_version": "1.0",
            "message_id": "2",
            "timestamp": "2026-09-07T00:00:00",
            "type": "chat",
            "forward_from": "Alice"
        }

        _validate_message(msg)

    def test_avatar_field(self):
        msg = {
            "protocol_version": "1.0",
            "message_id": "3",
            "timestamp": "2026-09-07T00:00:00",
            "type": "chat",
            "avatar": "avatar.png"
        }

        _validate_message(msg)

    def test_emoji_field(self):
        msg = {
            "protocol_version": "1.0",
            "message_id": "4",
            "timestamp": "2026-09-07T00:00:00",
            "type": "chat",
            "emoji": "😂"
        }

        _validate_message(msg)
    def test_reply(self):
        message = {
            "type": "reply",
            "content": "Hello"
        }

        self.assertEqual(message["type"], "reply")
        self.assertEqual(message["content"], "Hello")

    def test_forward(self):
        message = {
            "type": "forward",
            "content": "Hello"
        }

        self.assertEqual(message["type"], "forward")    
        self.assertEqual(message["content"], "Hello")


if __name__ == "__main__":
    unittest.main()
    