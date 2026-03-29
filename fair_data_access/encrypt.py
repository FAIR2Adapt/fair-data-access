"""Encrypt and decrypt data files using AES-256-GCM.

Encrypted file format:
  [12 bytes nonce][ciphertext + 16 bytes GCM tag]

The symmetric key is generated once per dataset and stored separately
(e.g., as a GitHub Secret). It is never included in the encrypted file.
"""

import os
import secrets
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_key() -> bytes:
    """Generate a new AES-256 symmetric key."""
    return AESGCM.generate_key(bit_length=256)


def encrypt_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    key: bytes | None = None,
) -> tuple[Path, bytes]:
    """Encrypt a file with AES-256-GCM.

    Parameters
    ----------
    input_path : path to the plaintext file
    output_path : path for the encrypted file (default: input_path + '.enc')
    key : AES-256 key. If None, a new key is generated.

    Returns
    -------
    (output_path, key) so the caller can store the key securely.
    """
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.with_suffix(input_path.suffix + ".enc")
    else:
        output_path = Path(output_path)

    if key is None:
        key = generate_key()

    plaintext = input_path.read_bytes()
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)

    output_path.write_bytes(nonce + ciphertext)
    return output_path, key


def decrypt_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    key: bytes = ...,
) -> Path:
    """Decrypt an AES-256-GCM encrypted file.

    Parameters
    ----------
    input_path : path to the encrypted file
    output_path : path for the decrypted file (default: strips '.enc' suffix)
    key : the AES-256 symmetric key
    """
    input_path = Path(input_path)
    if output_path is None:
        if input_path.suffix == ".enc":
            output_path = input_path.with_suffix("")
        else:
            output_path = input_path.with_suffix(input_path.suffix + ".dec")
    else:
        output_path = Path(output_path)

    data = input_path.read_bytes()
    nonce = data[:12]
    ciphertext = data[12:]

    plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    output_path.write_bytes(plaintext)
    return output_path


def decrypt_bytes(data: bytes, key: bytes) -> bytes:
    """Decrypt AES-256-GCM encrypted bytes in memory.

    Useful for streaming from S3 without writing to disk.
    """
    nonce = data[:12]
    ciphertext = data[12:]
    return AESGCM(key).decrypt(nonce, ciphertext, None)
