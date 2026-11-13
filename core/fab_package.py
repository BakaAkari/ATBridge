"""
Fab / Megascans package analysis, independent of Blender.

Given the asset metadata JSON and the list of extracted files, decide what the package is
(3D asset, 3D plant, surface, decal, atlas, imperfection, brush), which format it ships
(FBX / OBJ / glTF / textures only), which texture file serves each map, and which model
files make up each plant variant and LOD. Real Fab packages are the reference:

  3D asset     Name_id_Low.fbx (+ .ztl ignored), Name_id_Low_1K_<Map>.jpg
  3D plant     Name_id_Low_id_VarA_LOD0.fbx ... VarN_LOD2, maps incl. Opacity, Translucency
  surface      Name_id_1K_<Map>.jpg (no model), sometimes Fuzz / Transmission
  decal        BaseColor + Opacity (categories say "atlas", asset_type says "decal")
  atlas        Albedo (not BaseColor) + Opacity + Translucency, physicalSize like 0.41x0.41
  imperfection Gloss / Roughness / Mask, every resolution 1K..8K in one ZIP
  brush        <id>_<res>_Brush.jpg, every resolution in one ZIP
  glTF         *.gltf + .bin, UE-packed textures (B, N, ORM, B-O); *_nonUE.gltf when present
"""
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

KINDS = ('3d', '3dplant', 'surface', 'decal', 'atlas', 'imperfection', 'brush')
_ASSET_TYPE = {
    '3d asset': '3d', '3d plant': '3dplant', 'surface': 'surface', 'decal': 'decal',
    'atlas': 'atlas', 'imperfection': 'imperfection', 'brush': 'brush',
}
# File-name map tokens -> canonical map type used by the material builder.
MAP_TOKENS = {
    'basecolor': 'albedo', 'albedo': 'albedo', 'diffuse': 'albedo', 'ao': 'ao',
    'roughness': 'roughness', 'gloss': 'gloss', 'metalness': 'metalness', 'metallic': 'metalness',
    'normal': 'normal', 'bump': 'bump', 'displacement': 'displacement', 'opacity': 'opacity',
    'translucency': 'translucency', 'transmission': 'transmission', 'fuzz': 'fuzz',
    'specular': 'specular', 'cavity': 'cavity', 'mask': 'mask', 'brush': 'brush',
}
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.exr', '.tif', '.tiff')
_MAP_RE = re.compile(r'_(\d{1,2})K_([A-Za-z]+)(?:_LOD\d+)?$', re.I)
_VAR_RE = re.compile(r'_Var([A-Z0-9]+)_LOD(\d+)$', re.I)
_LOD_RE = re.compile(r'_LOD(\d+)$', re.I)


@dataclass
class Variant:
    name: str
    lods: Dict[int, str] = field(default_factory=dict)   # lod level -> model path


@dataclass
class FabPackage:
    asset_id: str
    name: str
    kind: str
    package_format: str                                    # 'fbx' | 'obj' | 'gltf' | 'textures' | 'unsupported'
    textures: Dict[str, str] = field(default_factory=dict)  # map type -> file path
    resolution: Optional[int] = None                        # K of the chosen texture set
    models: List[str] = field(default_factory=list)         # 3D asset model files (FBX/OBJ)
    variants: List[Variant] = field(default_factory=list)   # plants
    gltf: Optional[str] = None
    physical_size: Optional[tuple] = None                   # metres (x, y): physicalSize or scanArea
    displacement_height: Optional[float] = None             # metres of relief the displacement map spans
    tileable: bool = False

    @property
    def is_texture_only(self) -> bool:
        return self.package_format == 'textures'


def asset_kind(meta: dict) -> str:
    sem = meta.get('semanticTags') if isinstance(meta.get('semanticTags'), dict) else {}
    declared = str(sem.get('asset_type', '')).strip().lower()
    if declared in _ASSET_TYPE:
        return _ASSET_TYPE[declared]
    cats = [str(c).lower() for c in meta.get('categories', []) if isinstance(c, str)]
    if '3dplant' in cats:
        return '3dplant'
    if 'brush' in cats:
        return 'brush'
    if 'decals' in cats or 'decal' in cats:
        return 'decal'
    if 'imperfections' in cats:
        return 'imperfection'
    if cats and cats[0] in KINDS:
        return cats[0]
    return '3d'


def asset_name(meta: dict, fallback: str) -> str:
    sem = meta.get('semanticTags') if isinstance(meta.get('semanticTags'), dict) else {}
    for value in (meta.get('name'), sem.get('name'), meta.get('displayName'), meta.get('title')):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def _physical_size(meta: dict) -> Optional[tuple]:
    # physicalSize ("0.41x0.41") is set for atlases; texture sets give scanArea ("4x2 m").
    for size in (meta.get('physicalSize'), _meta_value(meta, 'scanArea')):
        if isinstance(size, str):
            m = re.match(r'^\s*([\d.]+)\s*x\s*([\d.]+)\s*m?\s*$', size)
            if m:
                x, y = float(m.group(1)), float(m.group(2))
                if 0 < x < 1000 and 0 < y < 1000:
                    return x, y
    return None


def _metres(value) -> Optional[float]:
    m = re.match(r'^\s*([\d.]+)\s*m\s*$', value) if isinstance(value, str) else None
    return float(m.group(1)) if m else None


def _meta_value(meta: dict, key: str):
    for item in meta.get('meta', []):
        if isinstance(item, dict) and item.get('key') == key:
            return item.get('value')
    return None


def analyse(meta: dict, files: List[str]) -> FabPackage:
    """meta: asset JSON; files: absolute paths of every extracted file."""
    asset_id = meta['id']
    kind = asset_kind(meta)
    # 3D assets report a placeholder "1x1"; real sizes only matter for texture-only packages.
    pkg = FabPackage(asset_id=asset_id, name=asset_name(meta, asset_id), kind=kind, package_format='textures',
                     physical_size=_physical_size(meta) if kind not in ('3d', '3dplant') else None,
                     displacement_height=_metres(_meta_value(meta, 'height')),
                     tileable=str(_meta_value(meta, 'tileable')).lower() == 'true')

    lower = [(f, os.path.basename(f)) for f in files]
    gltfs = [f for f, b in lower if b.lower().endswith('.gltf')]
    fbx = [f for f, b in lower if b.lower().endswith('.fbx')]
    obj = [f for f, b in lower if b.lower().endswith('.obj')]
    if gltfs:
        # Prefer the engine-neutral glTF when the package also ships a UE-flavoured one.
        neutral = [f for f in gltfs if 'nonue' in os.path.basename(f).lower()]
        pkg.package_format, pkg.gltf = 'gltf', sorted(neutral or gltfs, key=len)[0]
    elif fbx or obj:
        pkg.package_format = 'fbx' if fbx else 'obj'
        models = fbx or obj
        variants: Dict[str, Variant] = {}
        plain = []
        for path in models:
            stem = os.path.splitext(os.path.basename(path))[0]
            m = _VAR_RE.search(stem)
            if m:
                var = variants.setdefault(m.group(1).upper(), Variant(name='Var' + m.group(1).upper()))
                var.lods[int(m.group(2))] = path
            else:
                plain.append(path)
        if variants:
            pkg.variants = [variants[k] for k in sorted(variants)]
        if plain:
            # Single-model assets; if several LODs ship, keep the most detailed one.
            def lod_of(p):
                m = _LOD_RE.search(os.path.splitext(os.path.basename(p))[0])
                return int(m.group(1)) if m else -1
            best = min(lod_of(p) for p in plain)
            pkg.models = sorted(p for p in plain if lod_of(p) == best)

    if pkg.package_format == 'textures' and kind in ('3d', '3dplant'):
        # A model asset without an importable model (e.g. only ABC/USD shipped) must not
        # silently degrade into a texture import.
        pkg.package_format = 'unsupported'
    _pick_textures(pkg, lower)
    return pkg


MAX_DEFAULT_K = 4   # packages that ship every resolution (imperfections, brushes) default to 4K


def _pick_textures(pkg: FabPackage, files) -> None:
    """One file per map type: the package's own resolution, or at most 4K when it ships several."""
    found: Dict[str, Dict[int, str]] = {}
    # Deterministic order (os.walk order is not); generic maps win over LOD-specific ones.
    files = sorted(files, key=lambda f: (bool(re.search(r'_LOD\d+$', os.path.splitext(f[1])[0], re.I)), f[1].lower()))
    for path, base in files:
        stem, ext = os.path.splitext(base)
        if ext.lower() not in IMAGE_EXTS:
            continue
        m = _MAP_RE.search(stem)
        if not m:
            continue
        token = m.group(2).lower()
        map_type = MAP_TOKENS.get(token)
        if not map_type or 'billboard' in stem.lower():
            continue
        res = int(m.group(1))
        found.setdefault(map_type, {}).setdefault(res, path)
    if not found:
        return
    resolutions = sorted({r for by_res in found.values() for r in by_res})
    capped = [r for r in resolutions if r <= MAX_DEFAULT_K]
    pkg.resolution = capped[-1] if len(resolutions) > 1 and capped else resolutions[-1]
    for map_type, by_res in found.items():
        best = max((r for r in by_res if r <= pkg.resolution), default=min(by_res))
        pkg.textures[map_type] = by_res[best]
