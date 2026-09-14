from identity.identity_manager import IdentityManager


def test_peer_id_exists():

    identity = IdentityManager()

    identity.load_identity()

    assert identity.get_peer_id() != ""


def test_fingerprint_exists():

    identity = IdentityManager()

    identity.load_identity()

    assert identity.get_fingerprint() != ""


def test_public_key_exists():

    identity = IdentityManager()

    identity.load_identity()

    assert identity.get_public_key() is not None


def test_private_key_exists():

    identity = IdentityManager()

    identity.load_identity()

    assert identity.get_private_key() is not None
    
def test_peer_id_stable():

    identity1 = IdentityManager()
    identity1.load_identity()

    peer_id_1 = identity1.get_peer_id()

    identity2 = IdentityManager()
    identity2.load_identity()

    peer_id_2 = identity2.get_peer_id()

    assert peer_id_1 == peer_id_2

def test_fingerprint_stable():

    identity1 = IdentityManager()
    identity1.load_identity()

    fp1 = identity1.get_fingerprint()

    identity2 = IdentityManager()
    identity2.load_identity()

    fp2 = identity2.get_fingerprint()

    assert fp1 == fp2
    
def test_identity_load_and_save():

    manager = IdentityManager()

    manager.load_identity()

    peer_id = manager.get_peer_id()

    manager.save_identity()

    manager.load_identity()

    assert (
        manager.get_peer_id()
        ==
        peer_id
    )

def test_public_key_pem_exists():

    manager = IdentityManager()

    manager.load_identity()

    assert (
        manager.get_public_key_pem()
        != ""
    )
    
def test_load_identity_twice():

    manager = IdentityManager()

    manager.load_identity()

    first_peer_id = (
        manager.get_peer_id()
    )

    manager.load_identity()

    second_peer_id = (
        manager.get_peer_id()
    )

    assert (
        first_peer_id
        ==
        second_peer_id
    )
    
