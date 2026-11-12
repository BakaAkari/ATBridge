"""Read only the managed Fab product-image cache; no network or local rendering."""
import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid
from urllib.parse import urlsplit


def preview_cache_directory():
    base = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.cache'))
    return base / 'ATBridge' / 'Cache' / 'Fab'


def cached_product_image(asset_id, directory=None):
    if not isinstance(asset_id, str) or not asset_id or len(asset_id) > 256:
        return {}
    root = Path(directory) if directory is not None else preview_cache_directory()
    key = hashlib.sha256(asset_id.encode('utf-8')).hexdigest()
    record = root / 'assets' / (key + '.json')
    try:
        directories = (*root.parents, root, root / 'assets', root / 'images')
        if any(p.is_symlink() for p in directories) or record.is_symlink():
            return {}
        if hasattr(Path, 'is_junction') and any(p.is_junction() for p in directories):
            return {}
        if record.stat().st_size > 16384:
            return {}
        data = json.loads(record.read_text(encoding='utf-8-sig'))
        if not isinstance(data, dict) or data.get('schema') != 1 or data.get('asset_id') != asset_id:
            return {}
        filename = data.get('image', '')
        if not isinstance(filename, str) or not re.fullmatch(r'[a-f0-9]{64}\.png', filename):
            return {}
        listing_url = data.get('listing_url', '')
        if not isinstance(listing_url, str):
            return {}
        listing = urlsplit(listing_url)
        if (listing.scheme != 'https' or listing.hostname not in ('www.fab.com', 'fab.com')
                or listing.username is not None or listing.password is not None or listing.port not in (None, 443)
                or not re.fullmatch(r'/listings/[0-9a-fA-F-]{36}', listing.path)):
            return {}
        uuid.UUID(listing.path.rsplit('/', 1)[1])
        image = (root / 'images' / filename).resolve()
        if image.parent != (root / 'images').resolve():
            return {}
        stat = image.stat()
        if not 0 < stat.st_size <= 8 * 1024 ** 2 or time.time() - stat.st_mtime > 90 * 86400:
            return {}
        title = data.get('title', '')
        return {'preview': str(image), 'preview_label': 'Fab 商品图',
                'preview_token': '%s|%s|%s' % (filename, stat.st_mtime_ns, record.stat().st_mtime_ns),
                'listing_url': data['listing_url'],
                'title': title[:300] if isinstance(title, str) else ''}
    except (OSError, ValueError, TypeError):
        return {}
