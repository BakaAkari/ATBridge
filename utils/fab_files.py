"""Local Fab ZIP discovery and metadata selection, independent of Blender."""
import json
import os
import zipfile
import hashlib
import re
from pathlib import Path


def describe_zip(path, preview_directory=None):
    """Read bounded metadata only; full import still validates and resolves payloads."""
    try:
        from .zip_safety import validate_zip
        with zipfile.ZipFile(path) as archive:
            validate_zip(archive)
            data = read_asset_metadata(archive)
            models = data.get('models', [])
            names = [n.lower() for n in archive.namelist()]
            # The metadata always lists the FBX/ZTL sources; the archive shows what was downloaded.
            shipped = sorted({ext.upper() for ext in ('fbx', 'obj', 'gltf') if any(n.endswith('.' + ext) for n in names)})
            if not shipped and any(n.endswith(('.abc', '.usd', '.usdz', '.blend')) for n in names):
                raise ValueError('模型格式不支持，请下载 FBX、OBJ 或 glTF 资产包')
            title = next((data.get(k) for k in ('name', 'displayName', 'title')
                          if isinstance(data.get(k), str) and data[k].strip()), '')
            if not title:
                title = re.sub(re.escape(data['id']), '', Path(path).stem, flags=re.I)
                title = re.sub(r'(?i)(?:_|\s)(?:low|medium|high|raw|\d+k)(?=_|\s|$)', '', title)
                title = re.sub(r'[_\s]+', ' ', title).strip() or data['id']
            resolutions = sorted(set(re.findall(r'(?i)(?:_|/)(\d{1,2}K)(?:_|\.)', ' '.join(archive.namelist()))),
                                 key=lambda r: int(r[:-1]))
            kind = _KIND_LABELS.get(_asset_kind(data), '资产')
            detail = kind + (' · ' + ' / '.join(shipped) if shipped else '')
            if resolutions:
                detail += ' · ' + '/'.join(resolutions).upper()
            preview, preview_label = '', '资产包未包含模型缩略图'
            if preview_directory:
                previews = data.get('previews', {})
                declarations = previews.get('images', []) if isinstance(previews, dict) else []
                if not isinstance(declarations, list):
                    declarations = []
                uris = [x['uri'] for x in declarations
                        if isinstance(x, dict) and isinstance(x.get('uri'), str)]
                # Metadata URIs are matched only against validated archive members.
                # Never fetch a URL or substitute a material map for a model preview.
                entries = {x.filename: x for x in archive.infolist()}
                candidates = [entries[uri] for uri in uris if uri in entries
                              and entries[uri].file_size <= 8 * 1024 ** 2
                              and uri.lower().endswith(('.jpg', '.jpeg', '.png'))]
                if candidates:
                    entry = candidates[0]
                    stat = Path(path).stat()
                    key = hashlib.sha256(('%s|%s|%s' % (Path(path).resolve(), stat.st_size, stat.st_mtime_ns)).encode()).hexdigest()
                    target = Path(preview_directory) / (key + Path(entry.filename).suffix.lower())
                    try:
                        target.write_bytes(archive.read(entry))
                        preview, preview_label = str(target), '模型缩略图' if models else '材质效果预览'
                    except (OSError, RuntimeError, zipfile.BadZipFile):
                        preview_label = '缩略图读取失败，仍可导入资产'
                elif uris:
                    preview_label = '元数据包含预览引用，但包内缺少可用缩略图'
            return {'title': title, 'detail': detail, 'error': '', 'asset_id': data['id'],
                    'preview': preview, 'preview_label': preview_label}
    except Exception as error:
        return {'title': Path(path).stem, 'detail': '无法识别', 'error': str(error), 'asset_id': ''}


_KIND_LABELS = {'3d': '3D 资产', '3dplant': '植物', 'surface': '表面材质', 'decal': '贴花',
                'atlas': '图集', 'imperfection': '瑕疵贴图', 'brush': '笔刷'}
_ASSET_TYPES = {'3d asset': '3d', '3d plant': '3dplant', 'surface': 'surface', 'decal': 'decal',
                'atlas': 'atlas', 'imperfection': 'imperfection', 'brush': 'brush'}


def _asset_kind(data):
    """Same rule as core.fab_package.asset_kind (kept here so this module has no Blender-side imports)."""
    sem = data.get('semanticTags') if isinstance(data.get('semanticTags'), dict) else {}
    declared = str(sem.get('asset_type', '')).strip().lower()
    if declared in _ASSET_TYPES:
        return _ASSET_TYPES[declared]
    cats = [str(c).lower() for c in data.get('categories', []) if isinstance(c, str)]
    for key, kind in (('3dplant', '3dplant'), ('brush', 'brush'), ('decals', 'decal'), ('imperfections', 'imperfection')):
        if key in cats:
            return kind
    return cats[0] if cats and cats[0] in _KIND_LABELS else '3d'


def downloads_directory():
    if os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
                value, _ = winreg.QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')
            return Path(os.path.expandvars(value))
        except OSError:
            pass
    return Path.home() / 'Downloads'


def recent_zip_files(directory, limit=20):
    """Scan the selected folder and our download subfolders, never the whole disk."""
    root = Path(directory).expanduser().resolve()
    if not root.is_dir():
        raise ValueError('下载目录不存在，请重新选择')
    files = []
    for pattern in ('*', 'ATBridge/*/*'):
        for path in root.glob(pattern):
            if path.suffix.lower() != '.zip' or not path.is_file():
                continue
            resolved = path.resolve()
            if root not in resolved.parents:
                continue
            try:
                stat = resolved.stat()
                if stat.st_size:
                    files.append((resolved, stat.st_mtime_ns, stat.st_size))
            except OSError:
                continue
    return sorted(files, key=lambda item: (-item[1], str(item[0])))[:limit]


def read_asset_metadata(archive):
    """Select asset metadata by its schema, independent of the ZIP's filename."""
    candidates = []
    metadata_bytes = 0
    for entry in archive.infolist():
        if not entry.filename.lower().endswith('.json') or entry.file_size > 8 * 1024 ** 2:
            continue
        metadata_bytes += entry.file_size
        if metadata_bytes > 32 * 1024 ** 2:
            raise ValueError('ZIP 中的 JSON 元数据过大，无法安全识别资产')
        try:
            data = json.loads(archive.read(entry).decode('utf-8-sig'))
        except (ValueError, UnicodeError):
            continue
        if (isinstance(data, dict) and isinstance(data.get('id'), str) and data['id'].strip()
                and isinstance(data.get('maps', []), list)
                and isinstance(data.get('models', []), list)
                and all(isinstance(item, dict) and ('uri' not in item or isinstance(item['uri'], str))
                        for key in ('maps', 'models') for item in data.get(key, []))
                and any(isinstance(item.get('uri'), str) and item['uri'].strip()
                        for key in ('maps', 'models') for item in data.get(key, []))):
            candidates.append(data)
    if not candidates:
        raise ValueError('ZIP 中没有可识别的 Megascans 资产元数据；目前不支持任意 Fab ZIP')
    if len(candidates) != 1:
        raise ValueError('ZIP 包含多个资产的元数据，请选择单个资产的 ZIP')
    return candidates[0]
