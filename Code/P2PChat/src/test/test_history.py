from storage.message_history import MessageHistory

def test_append_message():

    history = MessageHistory()

    peer_id = "peer_chat"

    history.clear_history(peer_id)

    history.append_message(
        peer_id,
        {
            "message_id": "1",
            "peer_id": peer_id,
            "direction": "sent",
            "content": "Hello",
            "timestamp": 123
        }
    )

    messages = history.load_history(
        peer_id
    )

    assert len(messages) == 1
    
def test_message_count():

    history = MessageHistory()

    peer_id = "peer_count"

    history.clear_history(peer_id)

    history.append_message(
        peer_id,
        {
            "message_id": "1",
            "content": "A"
        }
    )

    history.append_message(
        peer_id,
        {
            "message_id": "2",
            "content": "B"
        }
    )

    assert (
        history.get_message_count(peer_id)
        == 2
    )
    
def test_clear_history():

    history = MessageHistory()

    peer_id = "peer_clear"

    history.append_message(
        peer_id,
        {
            "message_id": "1"
        }
    )

    history.clear_history(peer_id)

    assert (
        history.get_message_count(peer_id)
        == 0
    )
    
