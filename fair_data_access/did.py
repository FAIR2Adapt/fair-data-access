"""DID (Decentralized Identifier) resolution and verification.

Supports did:web and did:key methods. The did:web method resolves
by fetching a DID document from a well-known URL.
"""

import json

import httpx


def resolve_did(did: str) -> dict:
    """Resolve a DID to its DID document.

    Supported methods:
    - did:web:example.com → https://example.com/.well-known/did.json
    - did:web:example.com:path:to → https://example.com/path/to/did.json
    """
    if did.startswith("did:web:"):
        return _resolve_did_web(did)
    else:
        raise ValueError(f"Unsupported DID method: {did}")


def _resolve_did_web(did: str) -> dict:
    """Resolve a did:web identifier."""
    # did:web:example.com → https://example.com/.well-known/did.json
    # did:web:example.com:path:to → https://example.com/path/to/did.json
    parts = did.split(":")[2:]  # remove 'did' and 'web'
    domain = parts[0].replace("%3A", ":")  # handle port encoding

    if len(parts) == 1:
        url = f"https://{domain}/.well-known/did.json"
    else:
        path = "/".join(parts[1:])
        url = f"https://{domain}/{path}/did.json"

    response = httpx.get(url, follow_redirects=True)
    response.raise_for_status()
    return response.json()


def get_public_key_pem(did_document: dict) -> bytes:
    """Extract the first public key from a DID document as PEM bytes."""
    verification_methods = did_document.get("verificationMethod", [])
    if not verification_methods:
        raise ValueError("No verification methods found in DID document")

    method = verification_methods[0]

    if "publicKeyPem" in method:
        return method["publicKeyPem"].encode()
    elif "publicKeyJwk" in method:
        return _jwk_to_pem(method["publicKeyJwk"])
    elif "publicKeyMultibase" in method:
        raise NotImplementedError("publicKeyMultibase not yet supported")
    else:
        raise ValueError(f"No supported key format in verification method: {method}")


def _jwk_to_pem(jwk: dict) -> bytes:
    """Convert a JWK public key to PEM format."""
    import base64
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization

    if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
        raise ValueError(f"Only EC P-256 keys supported, got kty={jwk.get('kty')} crv={jwk.get('crv')}")

    x = base64.urlsafe_b64decode(jwk["x"] + "==")
    y = base64.urlsafe_b64decode(jwk["y"] + "==")

    public_numbers = ec.EllipticCurvePublicNumbers(
        x=int.from_bytes(x, "big"),
        y=int.from_bytes(y, "big"),
        curve=ec.SECP256R1(),
    )
    public_key = public_numbers.public_key()
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def create_did_document(
    did: str,
    public_key_pem: bytes,
    service_endpoints: list[dict] | None = None,
) -> dict:
    """Create a minimal DID document for did:web.

    This can be served as did.json at the appropriate URL.
    """
    from cryptography.hazmat.primitives import serialization
    import base64

    public_key = serialization.load_pem_public_key(public_key_pem)
    numbers = public_key.public_numbers()

    x_bytes = numbers.x.to_bytes(32, "big")
    y_bytes = numbers.y.to_bytes(32, "big")

    doc = {
        "@context": [
            "https://www.w3.org/ns/did/v1",
            "https://w3id.org/security/suites/jws-2020/v1",
        ],
        "id": did,
        "verificationMethod": [{
            "id": f"{did}#key-1",
            "type": "JsonWebKey2020",
            "controller": did,
            "publicKeyJwk": {
                "kty": "EC",
                "crv": "P-256",
                "x": base64.urlsafe_b64encode(x_bytes).rstrip(b"=").decode(),
                "y": base64.urlsafe_b64encode(y_bytes).rstrip(b"=").decode(),
            },
        }],
        "authentication": [f"{did}#key-1"],
        "assertionMethod": [f"{did}#key-1"],
    }

    if service_endpoints:
        doc["service"] = service_endpoints

    return doc
