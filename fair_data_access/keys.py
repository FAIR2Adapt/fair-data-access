"""Key wrapping and unwrapping using DID public/private keys.

The symmetric data encryption key is wrapped (encrypted) with the
recipient's public key from their DID document. Only the holder of
the corresponding private key can unwrap it.
"""

import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ec, padding, utils
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import secrets


def generate_did_keypair() -> tuple[bytes, bytes]:
    """Generate an EC P-256 keypair for use with DIDs.

    Returns
    -------
    (private_key_pem, public_key_pem)
    """
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def wrap_key(symmetric_key: bytes, recipient_public_key_pem: bytes) -> bytes:
    """Wrap a symmetric key for a recipient using ECDH + HKDF + AES key wrap.

    Uses ECIES-like scheme:
    1. Generate ephemeral EC keypair
    2. ECDH shared secret with recipient's public key
    3. Derive wrapping key via HKDF
    4. AES-GCM encrypt the symmetric key

    Returns
    -------
    JSON bytes containing ephemeral public key + wrapped key.
    """
    recipient_pubkey = serialization.load_pem_public_key(recipient_public_key_pem)

    ephemeral_private = ec.generate_private_key(ec.SECP256R1())
    shared_secret = ephemeral_private.exchange(ec.ECDH(), recipient_pubkey)

    wrapping_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"fair-data-access-key-wrap",
    ).derive(shared_secret)

    nonce = secrets.token_bytes(12)
    wrapped = AESGCM(wrapping_key).encrypt(nonce, symmetric_key, None)

    ephemeral_public_pem = ephemeral_private.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    envelope = {
        "ephemeral_public_key": base64.b64encode(ephemeral_public_pem).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "wrapped_key": base64.b64encode(wrapped).decode(),
        "algorithm": "ECDH-ES+HKDF-SHA256+AES-256-GCM",
    }
    return json.dumps(envelope).encode()


def unwrap_key(wrapped_envelope: bytes, recipient_private_key_pem: bytes) -> bytes:
    """Unwrap a symmetric key using the recipient's private key.

    Parameters
    ----------
    wrapped_envelope : JSON envelope from wrap_key()
    recipient_private_key_pem : recipient's EC private key in PEM format

    Returns
    -------
    The original symmetric key (AES-256, 32 bytes).
    """
    envelope = json.loads(wrapped_envelope)

    recipient_private = serialization.load_pem_private_key(
        recipient_private_key_pem, password=None
    )
    ephemeral_public_pem = base64.b64decode(envelope["ephemeral_public_key"])
    ephemeral_pubkey = serialization.load_pem_public_key(ephemeral_public_pem)

    shared_secret = recipient_private.exchange(ec.ECDH(), ephemeral_pubkey)

    wrapping_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"fair-data-access-key-wrap",
    ).derive(shared_secret)

    nonce = base64.b64decode(envelope["nonce"])
    wrapped = base64.b64decode(envelope["wrapped_key"])

    return AESGCM(wrapping_key).decrypt(nonce, wrapped, None)


def save_wrapped_key(wrapped_envelope: bytes, output_path: str | Path) -> Path:
    """Save a wrapped key envelope to a file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(wrapped_envelope)
    return output_path


def load_wrapped_key(path: str | Path) -> bytes:
    """Load a wrapped key envelope from a file."""
    return Path(path).read_bytes()
