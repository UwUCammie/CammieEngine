#!/usr/bin/env python3
"""Generate an isolated Nightmare Vision raw Assets family fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import secrets
import struct
import zlib


ROOT = Path(__file__).resolve().parents[1]
TMP = (ROOT / "tmp").resolve()


def rgba_png(rows: tuple[tuple[tuple[int, int, int, int], ...], ...]) -> bytes:
    height = len(rows)
    width = len(rows[0])
    if width < 1 or height < 1 or any(len(row) != width for row in rows):
        raise ValueError("PNG fixture rows must have the same non-zero width")

    def chunk(kind: bytes, payload: bytes) -> bytes:
        value = kind + payload
        return struct.pack(">I", len(payload)) + value + struct.pack(">I", zlib.crc32(value) & 0xFFFFFFFF)

    scanlines = bytearray()
    for row in rows:
        scanlines.append(0)
        for red, green, blue, alpha in row:
            scanlines.extend((red, green, blue, alpha))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(scanlines)))
            + chunk(b"IEND", b""))


def write(path: Path, data: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8", newline="\n")
    else:
        path.write_bytes(data)


def color(red: int, green: int, blue: int) -> tuple[int, int, int, int]:
    return (red, green, blue, 255)


def png_for(red: int, green: int, blue: int) -> tuple[bytes, str]:
    data = rgba_png(((color(red, green, blue), color(255 - red, 255 - green, 255 - blue)),
                     (color((red + 37) % 256, (green + 71) % 256, (blue + 113) % 256),
                      color((red + 91) % 256, (green + 29) % 256, (blue + 53) % 256))))
    return data, f"FF{red:02X}{green:02X}{blue:02X}"


def project_xml(
    library: str,
    assets: list[tuple[str, str, str, str]],
    *,
    source_prefix: str = "assets",
    include_app_identity: bool = True,
) -> str:
    groups: dict[tuple[str, str], list[tuple[str, str, str, str]]] = {}
    for source, target, asset_id, kind in assets:
        source_parts = source.split("/", 1)
        if len(source_parts) != 2:
            raise ValueError(f"Asset source must have a top-level directory: {source}")
        source_directory, source_leaf = source_parts
        target_parts = target.rsplit("/", 1)
        if len(target_parts) != 2 or not target_parts[0] or not target_parts[1]:
            raise ValueError(f"Asset target must have a directory and basename: {target}")
        target_directory, target_leaf = target_parts
        group_path = "/".join(part for part in (source_prefix, source_directory) if part)
        groups.setdefault((group_path, target_directory), []).append((source_leaf, target_leaf, asset_id, kind))

    declarations = "\n".join(
        f'  <assets path="{group_path}" rename="{target_directory}" library="{library}">\n'
        + "\n".join(
            f'    <asset path="{source}" rename="{target}" id="{asset_id}" type="{kind}" embed="false" />'
            for source, target, asset_id, kind in entries
        )
        + "\n  </assets>"
        for (group_path, target_directory), entries in groups.items()
    )
    app_identity = '  <app packageName="com.nmvTeam.nightmareEngine" />\n' if include_app_identity else ""
    return f'''<project>
{app_identity}  <library name="{library}" preload="true" embed="false" />
{declarations}
</project>
'''


def create(output: Path) -> dict:
    requested = output.expanduser().absolute()
    if requested.exists():
        raise FileExistsError(f"Refusing to overwrite fixture output: {requested}")
    parent = requested.parent.resolve()
    if parent != TMP and TMP not in parent.parents:
        raise ValueError(f"Fixture output must be below {TMP}")

    token = secrets.token_hex(6)
    library = f"codex_nv_assets_{token}"
    source = requested / "source"
    core = source
    write(core / "NightmareVision.exe", b"MZ\x00com.nmvTeam.nightmareEngine\x00")
    (core / "assets" / "data").mkdir(parents=True, exist_ok=True)
    (core / "assets" / "songs").mkdir(parents=True, exist_ok=True)

    core_pixels, core_pixel = png_for(226, 38, 61)
    shadow_pixels, shadow_pixel = png_for(164, 51, 208)
    write(core / "assets" / "images" / "core-only.png", core_pixels)
    write(core / "assets" / "images" / "shared-image.png", core_pixels)
    write(core / "assets" / "images" / "type-shadow.png", shadow_pixels)
    write(core / "assets" / "text" / "core-text.txt", "core text from retained Project\n")
    core_assets = [
        ("images/core-only.png", "assets/images/core-only.png", "core-only", "image"),
        ("images/shared-image.png", "assets/images/shared-image.png", "shared-image", "image"),
        ("images/type-shadow.png", "assets/images/type-shadow.png", "type-shadow", "image"),
        ("text/core-text.txt", "assets/text/core-text.txt", "core-text", "text"),
    ]
    write(core / "Project.xml", project_xml(library, core_assets))

    owners = []
    package_colors = {"alpha": (34, 188, 68), "beta": (48, 83, 224)}
    for directory, (red, green, blue) in package_colors.items():
        package = source / "content" / directory
        package_assets = package / "assets"
        shared_png, shared_pixel = png_for(red, green, blue)
        only_png, only_pixel = png_for((red + 43) % 256, (green + 67) % 256, (blue + 97) % 256)
        write(package / "meta.json", json.dumps({"name": directory, "description": "generated owner fixture"}, indent=2) + "\n")
        write(package_assets / "images" / "shared-image.png", shared_png)
        write(package_assets / "images" / f"{directory}-only.png", only_png)
        write(package_assets / "images" / "type-shadow.txt", f"{directory} text shadows the core image\n")
        write(package_assets / "images" / "unmapped.png", png_for(8, 9, 10)[0])
        write(package_assets / "shared" / "package-text.txt", f"{directory} package text\n")
        mappings = [
            ("images/shared-image.png", "assets/images/shared-image.png", "shared-image", "image"),
            (f"images/{directory}-only.png", f"assets/images/{directory}-only.png", f"{directory}-only", "image"),
            ("images/type-shadow.txt", "assets/images/type-shadow.txt", "type-shadow", "text"),
            ("shared/package-text.txt", "assets/text/package-text.txt", f"{directory}-text", "text"),
        ]
        write(package_assets / "Project.xml", project_xml(
            library, mappings, source_prefix="", include_app_identity=False))
        owners.append({
            "directory": directory,
            "sharedPixel": shared_pixel,
            "onlyPixel": only_pixel,
            "sharedSha256": hashlib.sha256(shared_png).hexdigest(),
            "corePixel": core_pixel,
            "shadowCorePixel": shadow_pixel,
            "expectedPackageText": f"{directory} package text\n",
            "expectedCoreText": "core text from retained Project\n",
        })

    request = {
        "kind": "nightmare-vision-raw-assets",
        "sourceRoot": str(source.resolve()).replace("\\", "/"),
        "library": library,
        "buildTarget": "windows",
        "owners": owners,
        "corePixel": core_pixel,
        "shadowCorePixel": shadow_pixel,
        "coreSharedSha256": hashlib.sha256(core_pixels).hexdigest(),
        "generated": True,
    }
    write(requested / "request.json", json.dumps(request, ensure_ascii=False, indent=2) + "\n")
    return {"fixtureRoot": str(requested.resolve()), "request": str((requested / "request.json").resolve()),
            "sourceRoot": request["sourceRoot"], "library": library,
            "owners": [owner["directory"] for owner in owners]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=TMP / f"nv-assets-fixture-{secrets.token_hex(6)}")
    arguments = parser.parse_args()
    print(json.dumps(create(arguments.output), indent=2))


if __name__ == "__main__":
    main()
