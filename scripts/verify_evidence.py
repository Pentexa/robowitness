"""Independent evidence package integrity verification script."""
import hashlib
import json
import sys
from pathlib import Path

def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().lower()

def verify_package(package_dir: Path) -> bool:
    if not package_dir.is_dir():
        print(f"[ERROR] Directory does not exist: {package_dir}")
        return False

    hashes_file = package_dir / "hashes.json"
    if not hashes_file.exists():
        print(f"[ERROR] Missing hashes.json in {package_dir}")
        return False

    with open(hashes_file, "r", encoding="utf-8") as f:
        expected_hashes = json.load(f)

    all_ok = True
    for rel_path_str, expected_hash in expected_hashes.items():
        target_file = package_dir / rel_path_str
        if not target_file.exists():
            print(f"[FAIL] Missing member file: {rel_path_str}")
            all_ok = False
            continue

        actual_hash = compute_sha256(target_file)
        if actual_hash != expected_hash.lower():
            print(f"[FAIL] Checksum mismatch for {rel_path_str}: expected {expected_hash}, got {actual_hash}")
            all_ok = False
        else:
            print(f"[OK] {rel_path_str} matches checksum.")

    return all_ok

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_evidence.py <path_to_verification_artifact_dir>")
        sys.exit(1)

    target_dir = Path(sys.argv[1])
    success = verify_package(target_dir)
    sys.exit(0 if success else 1)
