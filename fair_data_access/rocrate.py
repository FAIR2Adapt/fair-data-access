"""RO-Crate integration for encrypted data with ODRL policies.

Adds encryption metadata and ODRL policy references to RO-Crate
metadata files, and provides utilities for loading encrypted inputs
in the urban_pfr FDO pipeline.
"""

import hashlib
import json
from pathlib import Path

from fair_data_access.encrypt import decrypt_file, decrypt_bytes
from fair_data_access.keys import unwrap_key, load_wrapped_key

RO_CRATE_CONTEXT = "https://w3id.org/ro/crate/1.1/context"
SCIENCELIVE_TERMS = "https://w3id.org/sciencelive/o/terms/"
# EU access-right vocabulary, understood by catalogue harvesters without ODRL
ACCESS_RESTRICTED = "http://publications.europa.eu/resource/authority/access-right/RESTRICTED"

# Terms used by encrypted FDO crates that the RO-Crate context does not define.
# Without these, JSON-LD processors drop them and the policy is invisible to
# machines reading the crate as linked data.
ACCESS_TERMS = {
    "hasPolicy": {"@id": "http://www.w3.org/ns/odrl/2/hasPolicy", "@type": "@id"},
    "accessRights": {"@id": "http://purl.org/dc/terms/accessRights", "@type": "@id"},
    "contentEncryption": {"@id": SCIENCELIVE_TERMS + "contentEncryption"},
    "keyServer": {"@id": SCIENCELIVE_TERMS + "keyServer", "@type": "@id"},
    "accessGrant": {"@id": SCIENCELIVE_TERMS + "accessGrant", "@type": "@id"},
}


def declare_access_terms(crate: dict) -> dict:
    """Declare the access-control terms in the crate's @context (idempotent)."""
    context = crate.get("@context", RO_CRATE_CONTEXT)
    if not isinstance(context, list):
        context = [context]
    local = next((c for c in context if isinstance(c, dict)), None)
    if local is None:
        local = {}
        context.append(local)
    for term, definition in ACCESS_TERMS.items():
        local.setdefault(term, definition)
    crate["@context"] = context
    return crate


def did_hash(did: str) -> str:
    """SHA-256 (hex) of a DID, as used in the key server paths."""
    return hashlib.sha256(did.encode()).hexdigest()


def add_encrypted_file_to_crate(
    crate_metadata_path: str | Path,
    encrypted_file_id: str,
    original_name: str,
    description: str,
    encoding_format: str,
    policy_nanopub_uri: str,
    key_server_url: str,
    distribution_urls: list[dict] | None = None,
    variable_measured: list[dict] | None = None,
    conditions_of_access: str | None = None,
) -> dict:
    """Add an encrypted file entry to an existing RO-Crate metadata file.

    Parameters
    ----------
    crate_metadata_path : path to ro-crate-metadata.json
    encrypted_file_id : @id for the encrypted file (e.g., 'buildings.gpkg.enc')
    original_name : human-readable name
    description : description of the dataset
    encoding_format : MIME type of the original (unencrypted) file
    policy_nanopub_uri : URI of the ODRL policy nanopublication
    key_server_url : URL of the key server (GitHub Pages base URL)
    distribution_urls : list of download locations
        [{"name": "Zenodo", "contentUrl": "https://..."}, ...]
    variable_measured : I-ADOPT variable references
        [{"@id": "https://w3id.org/np/RA-..."}, ...]
    conditions_of_access : short human-readable summary of the policy
        (schema:conditionsOfAccess); the policy nanopub stays authoritative

    Returns
    -------
    The updated RO-Crate metadata dict.
    """
    crate_path = Path(crate_metadata_path)
    crate = json.loads(crate_path.read_text())

    file_entry = {
        "@id": encrypted_file_id,
        "@type": "File",
        "name": original_name,
        "description": description,
        "encodingFormat": encoding_format,
        "contentEncryption": {
            "algorithm": "AES-256-GCM",
            "keyServer": key_server_url,
        },
        "hasPolicy": {"@id": policy_nanopub_uri},
        "accessRights": {"@id": ACCESS_RESTRICTED},
    }
    if conditions_of_access:
        file_entry["conditionsOfAccess"] = conditions_of_access

    if distribution_urls:
        file_entry["distribution"] = [
            {
                "@type": "DataDownload",
                "name": d["name"],
                "contentUrl": d["contentUrl"],
                **({"identifier": d["identifier"]} if "identifier" in d else {}),
            }
            for d in distribution_urls
        ]

    if variable_measured:
        file_entry["variableMeasured"] = variable_measured

    # Add to @graph
    graph = crate.get("@graph", [])
    # Remove existing entry with same @id if present
    graph = [e for e in graph if e.get("@id") != encrypted_file_id]
    graph.append(file_entry)

    # Also add to the root dataset's hasPart
    for entry in graph:
        if entry.get("@id") == "./":
            has_part = entry.get("hasPart", [])
            if {"@id": encrypted_file_id} not in has_part:
                has_part.append({"@id": encrypted_file_id})
            entry["hasPart"] = has_part
            break

    crate["@graph"] = graph
    declare_access_terms(crate)
    crate_path.write_text(json.dumps(crate, indent=2))
    return crate


def load_encrypted_input(
    crate_entry: dict,
    private_key_pem: bytes,
    key_dir: str | Path | None = None,
    s3_endpoint: str | None = None,
    requester_did: str | None = None,
    dataset: str | None = None,
    key_url: str | None = None,
) -> bytes:
    """Load and decrypt an encrypted input file referenced in an RO-Crate.

    The wrapped key is taken from, in order: ``key_url``; ``key_dir``; or the
    crate's key server, at ``{keyServer}/keys/{sha256(requester_did)}/{dataset}.key``
    (the path the access-request workflow publishes to).

    Parameters
    ----------
    crate_entry : the @graph entry for the encrypted file
    private_key_pem : the requester's DID private key (PEM)
    key_dir : directory containing wrapped key files (from GitHub Pages)
    s3_endpoint : S3 endpoint URL (for Pangeo@EOSC access)
    requester_did : the requester's DID (needed to find the key on the key server)
    dataset : dataset name in the policy registry, e.g. "hamburg-buildings"
    key_url : explicit URL of the wrapped key (e.g. from the access-grant comment)

    Returns
    -------
    Decrypted file contents as bytes.
    """
    file_id = crate_entry["@id"]
    encryption = crate_entry.get("contentEncryption", {})

    if not encryption:
        raise ValueError(f"No contentEncryption metadata for {file_id}")

    # Get the wrapped key
    if key_url is None and not key_dir:
        if not (requester_did and dataset):
            raise ValueError(
                "To fetch the wrapped key from the key server, pass requester_did "
                "and dataset (or key_url, or key_dir)"
            )
        key_server = encryption["keyServer"].rstrip("/")
        key_url = f"{key_server}/keys/{did_hash(requester_did)}/{dataset}.key"

    if key_url:
        import httpx
        response = httpx.get(key_url, follow_redirects=True)
        response.raise_for_status()
        wrapped = response.content
    else:
        wrapped = load_wrapped_key(Path(key_dir) / file_id.replace(".enc", ".key"))

    symmetric_key = unwrap_key(wrapped, private_key_pem)

    # Fetch the encrypted data
    distributions = crate_entry.get("distribution", [])
    s3_dist = next((d for d in distributions if d.get("contentUrl", "").startswith("s3://")), None)
    http_dist = next((d for d in distributions if d.get("contentUrl", "").startswith("http")), None)

    if s3_dist and s3_endpoint:
        import s3fs
        s3 = s3fs.S3FileSystem(
            endpoint_url=s3_endpoint,
            anon=True,
        )
        s3_path = s3_dist["contentUrl"].replace("s3://", "")
        encrypted_data = s3.cat(s3_path)
    elif http_dist:
        import httpx
        response = httpx.get(http_dist["contentUrl"], follow_redirects=True)
        response.raise_for_status()
        encrypted_data = response.content
    else:
        # Try local file
        encrypted_data = Path(file_id).read_bytes()

    return decrypt_bytes(encrypted_data, symmetric_key)
