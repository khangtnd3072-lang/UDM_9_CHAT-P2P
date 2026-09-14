from storage.contact_book import ContactBook


def test_add_contact():

    book = ContactBook()

    peer_id = "peer_test"

    book.remove_contact(peer_id)

    book.add_contact(
        peer_id=peer_id,
        alias="Tai",
        trust_state="TRUSTED",
        fingerprint="ABC123"
    )

    contact = book.get_contact(peer_id)

    assert contact is not None
    assert contact["alias"] == "Tai"
    
def test_remove_contact():

    book = ContactBook()

    peer_id = "peer_remove"

    book.add_contact(
        peer_id,
        "Tai",
        "TRUSTED",
        "ABC"
    )

    book.remove_contact(peer_id)

    assert book.get_contact(peer_id) is None
    
def test_update_contact():

    book = ContactBook()

    peer_id = "peer_update"

    book.add_contact(
        peer_id,
        "Old Name",
        "TRUSTED",
        "ABC"
    )

    book.update_contact(
        peer_id,
        alias="New Name"
    )

    contact = book.get_contact(peer_id)

    assert contact is not None
    assert contact["alias"] == "New Name"
    
def test_contact_persistence():

    peer_id = "peer_persist"

    book1 = ContactBook()

    book1.add_contact(
        peer_id,
        "Tai",
        "TRUSTED",
        "ABC"
    )

    book2 = ContactBook()

    contact = book2.get_contact(
        peer_id
    )

    assert contact is not None
    

def test_remove_missing_contact():

    book = ContactBook()

    book.remove_contact(
        "not_found"
    )

    assert True
    
def test_get_missing_contact():

    book = ContactBook()

    contact = book.get_contact(
        "missing"
    )

    assert contact is None
    
from storage.message_history import (
    MessageHistory
)


def test_load_empty_history():

    history = MessageHistory()

    records = history.load_history(
        "unknown_peer"
    )

    assert records == []
    
