from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif", ".bmp"}

_C2PA_MARKERS = [
    b"c2pa",
    b"C2PA",
    b"jumb",
    b"JUMBF",
    b"application/c2pa",
    b"urn:c2pa",
]

_XMP_MARKERS = [
    b"ns.adobe.com/xap",
    b"<x:xmpmeta",
]

_AI_HINT_MARKERS = [
    b"DALL-E",
    b"DALL\xc2\xb7E",
    b"OpenAI",
    b"openai",
    b"Midjourney",
    b"Stable Diffusion",
    b"trainedAlgorithmicMedia",
    b"compositeWithTrainedAlgorithmicMedia",
    b"digitalSourceType",
]


@dataclass
class ScanReport:
    path: Path
    format: str | None
    size: tuple[int, int]
    mode: str
    exif_tag_count: int
    has_icc: bool
    has_xmp: bool
    has_c2pa: bool
    ai_hints: list[str] = field(default_factory=list)
    is_animated: bool = False

    @property
    def is_clean(self) -> bool:
        return (
            self.exif_tag_count == 0
            and not self.has_icc
            and not self.has_xmp
            and not self.has_c2pa
        )


@dataclass
class CleanResult:
    source: Path
    output: Path
    before: ScanReport
    skipped: bool = False
    reason: str | None = None


def find_images(paths: list[Path], recursive: bool = False) -> list[Path]:
    result: list[Path] = []
    for p in paths:
        if p.is_file():
            if p.suffix.lower() in SUPPORTED_EXTENSIONS:
                result.append(p)
        elif p.is_dir():
            pattern = "**/*" if recursive else "*"
            for child in sorted(p.glob(pattern)):
                if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS:
                    result.append(child)
    return result


def _search_markers(raw: bytes, markers: list[bytes]) -> list[str]:
    found = []
    for marker in markers:
        if re.search(re.escape(marker), raw, re.IGNORECASE):
            found.append(marker.decode("utf-8", errors="replace"))
    return found


def scan_file(path: Path) -> ScanReport:
    with Image.open(path) as img:
        exif = img.getexif()
        exif_tag_count = len(exif) if exif else 0
        has_icc = "icc_profile" in img.info
        is_animated = getattr(img, "n_frames", 1) > 1
        fmt = img.format
        size = img.size
        mode = img.mode

    raw = path.read_bytes()
    has_xmp = bool(_search_markers(raw, _XMP_MARKERS))
    has_c2pa = bool(_search_markers(raw, _C2PA_MARKERS))
    ai_hints = _search_markers(raw, _AI_HINT_MARKERS)

    return ScanReport(
        path=path,
        format=fmt,
        size=size,
        mode=mode,
        exif_tag_count=exif_tag_count,
        has_icc=has_icc,
        has_xmp=has_xmp,
        has_c2pa=has_c2pa,
        ai_hints=ai_hints,
        is_animated=is_animated,
    )


def clean_file(
    path: Path,
    output_path: Path,
    quality: int = 95,
    keep_icc: bool = False,
) -> CleanResult:
    before = scan_file(path)

    with Image.open(path) as img:
        if before.is_animated:
            return CleanResult(
                source=path,
                output=output_path,
                before=before,
                skipped=True,
                reason="animated/multi-frame file skipped (only the first frame is supported)",
            )

        img.load()
        clean_img = Image.new(img.mode, img.size)
        clean_img.putdata(list(img.getdata()))
        if img.mode == "P" and img.palette is not None:
            clean_img.putpalette(img.getpalette())

    save_kwargs: dict = {}
    fmt = (output_path.suffix.lower().lstrip(".") or "png").upper()
    if fmt in ("JPG",):
        fmt = "JPEG"
    if fmt == "JPEG":
        save_kwargs["quality"] = quality
        save_kwargs["optimize"] = True
        if clean_img.mode not in ("RGB", "L"):
            clean_img = clean_img.convert("RGB")
    if keep_icc and before.has_icc:
        with Image.open(path) as original:
            icc = original.info.get("icc_profile")
        if icc:
            save_kwargs["icc_profile"] = icc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    clean_img.save(output_path, format=fmt, **save_kwargs)

    return CleanResult(source=path, output=output_path, before=before)
