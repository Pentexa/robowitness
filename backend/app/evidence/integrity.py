"""SHA-256 evidence sealing and independent verification."""
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple

def compute_file_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().lower()

def seal_package_hashes(package_dir: Path) -> Path:
    """Generate SHA-256 hashes for all member files and seal into hashes.json."""
    hashes: Dict[str, str] = {}
    for path in package_dir.glob("*"):
        if path.is_file() and path.name != "hashes.json":
            hashes[path.name] = compute_file_sha256(path)

    hashes_file = package_dir / "hashes.json"
    with open(hashes_file, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2, sort_keys=True)
    return hashes_file

def verify_package_integrity(package_dir: Path, required_files: List[str]) -> Tuple[bool, List[str]]:
    """Check that all required files exist and strictly match hashes.json."""
    hashes_file = package_dir / "hashes.json"
    if not hashes_file.exists():
        return False, ["MISSING_HASHES_JSON"]

    with open(hashes_file, "r", encoding="utf-8") as f:
        stored_hashes = json.load(f)

    errors = []
    # Check required files
    for req in required_files:
        p = package_dir / req
        if not p.exists():
            errors.append(f"MISSING_MEMBER_{req.upper()}")

    # Check checksums
    for filename, expected_hash in stored_hashes.items():
        p = package_dir / filename
        if not p.exists():
            continue
        actual_hash = compute_file_sha256(p)
        if actual_hash != expected_hash.lower():
            errors.append(f"TAMPERED_{filename}")

    return (len(errors) == 0), errors
