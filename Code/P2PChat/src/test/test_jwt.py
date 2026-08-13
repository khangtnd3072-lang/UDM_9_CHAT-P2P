from security.jwt_handler import JWTHandler
from security.rsa_utils import RSAUtils


def test_jwt_round_trip():

    private_key, public_key = (
        RSAUtils.generate_key_pair()
    )

    private_pem = (
        RSAUtils.serialize_private_key(
            private_key
        )
    )

    public_pem = (
        RSAUtils.serialize_public_key(
            public_key
        )
    )

    token = (
        JWTHandler.create_identity_token(
            peer_id="peer1",
            username="Tai",
            fingerprint="ABC",
            private_key_pem=private_pem
        )
    )

    payload = (
        JWTHandler.verify_identity_token(
            token,
            public_pem
        )
    )

    assert payload is not None
    assert payload["peer_id"] == "peer1"
    
def test_invalid_signature():

    private1, public1 = (
        RSAUtils.generate_key_pair()
    )

    private2, public2 = (
        RSAUtils.generate_key_pair()
    )

    token = (
        JWTHandler.create_identity_token(
            peer_id="peer1",
            username="Tai",
            fingerprint="ABC",
            private_key_pem=
            RSAUtils.serialize_private_key(
                private1
            )
        )
    )

    payload = (
        JWTHandler.verify_identity_token(
            token,
            RSAUtils.serialize_public_key(
                public2
            )
        )
    )

    assert payload is None
    
