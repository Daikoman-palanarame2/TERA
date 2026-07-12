#!/usr/bin/env python3
"""Download and verify local semantic cache assets with strict checksum pinning."""

import os
import sys
import json
import hashlib
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path

# Pinned metadata from Xenova/all-MiniLM-L6-v2
ASSETS = {
    "minilm.onnx": {
        "url": "https://huggingface.co/Xenova/all-MiniLM-L6-v2/resolve/main/onnx/model.onnx",
        "sha256": "759c3cd2b7fe7e93933ad23c4c9181b7396442a2ed746ec7c1d46192c469c46e",
        "expected_size": 90387606,
    },
    "tokenizer.json": {
        "url": "https://huggingface.co/Xenova/all-MiniLM-L6-v2/resolve/main/tokenizer.json",
        "sha256": "da0e79933b9ed51798a3ae27893d3c5fa4a201126cef75586296df9b4d2c62a0",
        "expected_size": 711661,
    }
}

def verify_checksum(filepath: Path, expected_sha256: str, expected_size: int) -> bool:
    if not filepath.exists():
        return False
    if filepath.stat().st_size != expected_size:
        return False
    
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
            
    return sha256_hash.hexdigest() == expected_sha256

def download_file(url: str, dest_path: Path, expected_sha256: str, expected_size: int) -> None:
    print(f"Downloading {url} ...")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Use temporary file in the target directory to allow atomic rename
    fd, temp_file_path_str = tempfile.mkstemp(dir=str(dest_path.parent), suffix=".tmp")
    temp_file_path = Path(temp_file_path_str)
    
    try:
        with os.fdopen(fd, "wb") as temp_file:
            with urllib.request.urlopen(url) as response:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    temp_file.write(chunk)
                    downloaded += len(chunk)
                    
        # Check size and hash
        if not verify_checksum(temp_file_path, expected_sha256, expected_size):
            raise ValueError(f"Download checksum/size mismatch for {url}")
            
        # Atomic replace
        os.replace(temp_file_path, dest_path)
        print(f"Successfully downloaded and verified {dest_path.name}")
    except Exception as e:
        if temp_file_path.exists():
            temp_file_path.unlink()
        raise RuntimeError(f"Failed to download {dest_path.name}: {e}") from e

def main() -> int:
    target_dir = Path(__file__).resolve().parents[1] / "models"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Download/verify assets
    for filename, meta in ASSETS.items():
        dest = target_dir / filename
        if verify_checksum(dest, meta["sha256"], meta["expected_size"]):
            print(f"{filename} is already present and verified.")
            continue
        try:
            download_file(meta["url"], dest, meta["sha256"], meta["expected_size"])
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
            
    # 2. Write provenance metadata
    provenance = {
        "download_timestamp": datetime.utcnow().isoformat() + "Z",
        "license": "Apache 2.0 (for Xenova/all-MiniLM-L6-v2)",
        "source_repo": "https://huggingface.co/Xenova/all-MiniLM-L6-v2",
        "assets": ASSETS
    }
    with open(target_dir / "provenance.json", "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)
        
    print("All cache assets successfully prepared.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
