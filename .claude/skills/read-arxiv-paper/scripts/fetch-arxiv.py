#!/usr/bin/env python3
"""fetch-arxiv.py - Download and extract arXiv paper source (cross-platform)

Usage: python fetch-arxiv.py <arxiv-url-or-id>
Example: python fetch-arxiv.py 2601.07372
         python fetch-arxiv.py https://arxiv.org/abs/2601.07372
"""

import sys
import re
import tarfile
import gzip
import shutil
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

def get_cache_dir():
    """Get cross-platform cache directory."""
    import os
    if custom := os.environ.get('ARXIV_CACHE'):
        return Path(custom)

    # Use platform-appropriate cache location
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Caches'
    else:
        base = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache'))

    return base / 'arxiv-papers'

def extract_id(input_str):
    """Extract arxiv ID from URL or direct ID."""
    # Remove URL components
    match = re.search(r'arxiv\.org/(?:abs|pdf|src)/(.+?)(?:\.pdf)?$', input_str)
    if match:
        arxiv_id = match.group(1)
    else:
        arxiv_id = input_str

    # Remove version suffix (v1, v2, etc.)
    arxiv_id = re.sub(r'v\d+$', '', arxiv_id)
    return arxiv_id.strip()

def validate_id(arxiv_id):
    """Validate arxiv ID format."""
    # Modern format: YYMM.NNNNN
    if re.match(r'^\d{4}\.\d{4,5}$', arxiv_id):
        return True
    # Old format: category/NNNNNNN
    if re.match(r'^[a-z-]+/\d+$', arxiv_id):
        return True
    return False

def download_source(arxiv_id, dest_path):
    """Download arxiv source tarball."""
    url = f'https://arxiv.org/src/{arxiv_id}'
    request = Request(url, headers={'User-Agent': 'arxiv-fetcher/1.0'})

    try:
        with urlopen(request, timeout=30) as response:
            dest_path.write_bytes(response.read())
        return True
    except HTTPError as e:
        print(f"Error: HTTP {e.code} - Check if arxiv ID exists")
        return False
    except URLError as e:
        print(f"Error: Network error - {e.reason}")
        return False

def extract_source(tarball_path, extract_dir):
    """Extract tarball, handling various formats."""
    extract_dir.mkdir(parents=True, exist_ok=True)

    # Check file type by reading magic bytes
    with open(tarball_path, 'rb') as f:
        header = f.read(4)

    # Gzipped content
    if header[:2] == b'\x1f\x8b':
        try:
            with tarfile.open(tarball_path, 'r:gz') as tar:
                tar.extractall(extract_dir)
            return True
        except tarfile.TarError:
            # Might be gzipped single file, not tarball
            try:
                with gzip.open(tarball_path, 'rb') as gz:
                    content = gz.read()
                (extract_dir / 'paper.tex').write_bytes(content)
                return True
            except Exception:
                pass

    # Plain tar
    if header[:4] in (b'usta', b'\x00\x00\x00\x00'):
        try:
            with tarfile.open(tarball_path, 'r:') as tar:
                tar.extractall(extract_dir)
            return True
        except tarfile.TarError:
            pass

    # Might be a plain .tex file
    try:
        content = tarball_path.read_text(encoding='utf-8')
        if '\\documentclass' in content or '\\begin{document}' in content:
            (extract_dir / 'paper.tex').write_bytes(tarball_path.read_bytes())
            return True
    except Exception:
        pass

    print("Error: Could not extract archive - unknown format")
    return False

def find_entrypoint(extract_dir):
    """Find the main .tex file."""
    # Common names
    for name in ['main.tex', 'paper.tex', 'manuscript.tex', 'article.tex']:
        if (extract_dir / name).exists():
            return name

    # Search for \documentclass
    tex_files = list(extract_dir.glob('*.tex'))
    for tex_file in tex_files:
        try:
            content = tex_file.read_text(encoding='utf-8', errors='ignore')
            if '\\documentclass' in content:
                return tex_file.name
        except Exception:
            continue

    # Single .tex file
    if len(tex_files) == 1:
        return tex_files[0].name

    return None

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    arxiv_id = extract_id(sys.argv[1])

    if not validate_id(arxiv_id):
        print(f"Error: Invalid arxiv ID format: {arxiv_id}")
        print("Expected: YYMM.NNNNN (e.g., 2601.07372)")
        sys.exit(1)

    cache_dir = get_cache_dir()
    paper_dir = cache_dir / arxiv_id
    extract_dir = paper_dir / 'extracted'
    tarball = paper_dir / 'source.tar.gz'

    print(f"arXiv ID: {arxiv_id}")
    print(f"Cache: {paper_dir}")

    # Check if already cached
    if extract_dir.exists() and any(extract_dir.iterdir()):
        print(f"Already cached at {extract_dir}")
        entrypoint = find_entrypoint(extract_dir)
        if entrypoint:
            print(f"Entry point: {entrypoint}")
        else:
            print("Available .tex files:")
            for f in extract_dir.glob('**/*.tex'):
                print(f"  {f.relative_to(extract_dir)}")
        sys.exit(0)

    # Create directories
    paper_dir.mkdir(parents=True, exist_ok=True)

    # Download
    print(f"Downloading from https://arxiv.org/src/{arxiv_id} ...")
    if not download_source(arxiv_id, tarball):
        if tarball.exists():
            tarball.unlink()
        sys.exit(1)

    # Extract
    if not extract_source(tarball, extract_dir):
        sys.exit(1)

    print(f"Extracted to {extract_dir}")

    # Find entry point
    print()
    entrypoint = find_entrypoint(extract_dir)
    if entrypoint:
        print(f"Entry point: {entrypoint}")
    else:
        print("No obvious entry point. Available .tex files:")
        for f in extract_dir.glob('**/*.tex'):
            print(f"  {f.relative_to(extract_dir)}")

if __name__ == '__main__':
    main()
