"""Validate downloaded archives before extracting into a private cache."""
from pathlib import Path, PurePosixPath
import stat

MAX_ARCHIVE = 1024 ** 3
MAX_EXPANDED = 4 * 1024 ** 3


def validate_zip(archive):
    entries = archive.infolist()
    if len(entries) > 10000 or sum(x.file_size for x in entries) > MAX_EXPANDED:
        raise ValueError('ZIP exceeds prototype extraction limits')
    names = set()
    for entry in entries:
        name = entry.filename
        path = PurePosixPath(name)
        if (not name or '\\' in name or ':' in name or path.is_absolute()
                or '..' in path.parts or stat.S_ISLNK(entry.external_attr >> 16)):
            raise ValueError('Unsafe ZIP entry')
        normalized = str(path).casefold()
        if normalized in names:
            raise ValueError('Duplicate ZIP entry')
        names.add(normalized)
    return entries


def extract_checked(archive, destination):
    entries = validate_zip(archive)
    root = Path(destination).resolve()
    for entry in entries:
        target = root.joinpath(*PurePosixPath(entry.filename).parts).resolve()
        if root not in target.parents and root != target:
            raise ValueError('ZIP destination escapes cache')
    archive.extractall(str(root))
