#!/usr/bin/env python3
"""Create isolated, generated Project roots for the owner-library smoke probe."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import secrets
import struct
import wave
import zlib


ROOT = Path(__file__).resolve().parents[1]
TMP = (ROOT / "tmp").resolve()


def png_rgba(pixels: tuple[tuple[tuple[int, int, int, int], ...], ...]) -> bytes:
    height = len(pixels)
    width = len(pixels[0])
    if not width or any(len(row) != width for row in pixels):
        raise ValueError("PNG fixture rows must have the same non-zero width")

    def chunk(kind: bytes, data: bytes) -> bytes:
        payload = kind + data
        return struct.pack(">I", len(data)) + payload + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF)

    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for red, green, blue, alpha in row:
            raw.extend((red, green, blue, alpha))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw)))
            + chunk(b"IEND", b""))


def write(path: Path, data: bytes | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8", newline="\n")
    else:
        path.write_bytes(data)


def project_xml(warm: str, lazy: str) -> str:
    return f'''<project>
  <library name="{warm}" preload="true" embed="false" />
  <library name="{lazy}" preload="false" embed="false" />
  <assets path="assets/payload" rename="assets/warm" library="{warm}">
    <asset path="warm.txt" rename="warm.txt" id="shared-text" type="text" embed="false" />
    <asset path="pixels.png" rename="pixels.png" id="shared-image" type="image" embed="false" />
  </assets>
  <assets path="assets/payload" rename="assets/lazy" library="{lazy}">
    <asset path="lazy.txt" rename="lazy.txt" id="lazy-text" type="text" embed="false" />
  </assets>
</project>
'''


def cpp_project(library: str, stream_type: str) -> str:
    return f'''<project>
  <library name="{library}" preload="false" embed="false" />
  <assets path="assets/runtime" rename="assets/runtime" library="{library}">
    <asset path="sound.wav" rename="sound.wav" id="shared-sound" type="sound" embed="false" />
    <asset path="music.wav" rename="music.wav" id="shared-music" type="music" embed="false" />
    <asset path="stream.ogg" rename="stream.ogg" id="stream-music" type="{stream_type}" embed="false" />
    <asset path="font.otf" rename="font.otf" id="shared-font" type="font" embed="false" />
  </assets>
</project>
'''


def unknown_project(library: str) -> str:
    return f'''<project>
  <library name="{library}" preload="true" embed="false" />
  <assets path="assets/payload" rename="assets/unknown" library="{library}">
    <asset path="warm.txt" rename="warm.txt" id="unknown-text" type="text" embed="false" />
  </assets>
</project>
'''


def psych_marker(root: Path) -> None:
    write(root / "source" / "psychlua" / "OwnerLibraryMarker.hx",
          "class OwnerLibraryMarker {}\n")
    # ImportRootScanner requires at least two recognized content roots before
    # it scores engine markers. Empty data/songs folders make this a real
    # zero-song Psych source root without changing Project-mapped assets.
    for relative in ("assets/data", "assets/songs"):
        (root / relative).mkdir(parents=True, exist_ok=True)


def pcm_wav(owner_name: str, asset_kind: str) -> bytes:
    owner_offset = 0 if owner_name == "alpha" else 7000
    kind_offset = 0 if asset_kind == "sound" else 3000
    samples = [owner_offset + kind_offset + ((index * 613) % 5000) - 2500
               for index in range(32)]
    output = __import__("io").BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(8000)
        stream.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
    return output.getvalue()


def create(output: Path) -> dict:
    requested = output.expanduser().absolute()
    resolved_parent = requested.parent.resolve()
    if requested.exists():
        raise FileExistsError(f"Refusing to overwrite fixture output: {requested}")
    if resolved_parent != TMP and TMP not in resolved_parent.parents:
        raise ValueError(f"Fixture output must be below {TMP}")

    token = secrets.token_hex(6)
    warm = f"codex_owner_warm_{token}"
    lazy = f"codex_owner_lazy_{token}"
    unknown_library = f"codex_owner_unknown_{token}"
    cpp_library = f"codex_owner_cpp_{token}"
    source = requested / "source"
    cpp_source = requested / "cpp-source"
    unknown = requested / "unknown-source"

    owners = []
    owner_colors = {
        "alpha": ((0, 0, 0, 0), (17, 34, 51, 127),
                  (68, 85, 102, 127), (119, 136, 153, 127)),
        "beta": ((0, 0, 0, 0), (34, 51, 68, 127),
                 (85, 102, 119, 127), (136, 153, 170, 127)),
    }
    for owner_name in ("alpha", "beta"):
        root = source / owner_name
        write(root / "Project.xml", project_xml(warm, lazy))
        psych_marker(root)
        write(root / "assets" / "payload" / "warm.txt", f"{owner_name} warm original\n")
        write(root / "assets" / "payload" / "lazy.txt", f"{owner_name} lazy original\n")
        c0, c1, c2, c3 = owner_colors[owner_name]
        write(root / "assets" / "payload" / "pixels.png",
              png_rgba(((c0, c1), (c2, c3))))
        owners.append({
            "rootRelative": owner_name,
            "warmText": f"{owner_name} warm original\n",
            "lazyText": f"{owner_name} lazy original\n",
            "topRight": (0x7F << 24) | (c1[0] << 16) | (c1[1] << 8) | c1[2],
            "bottomLeft": (0x7F << 24) | (c2[0] << 16) | (c2[1] << 8) | c2[2],
            "bottomRight": (0x7F << 24) | (c3[0] << 16) | (c3[1] << 8) | c3[2],
        })

    cpp_owners = []
    font_sources = {
        "alpha": ROOT / "assets" / "fonts" / "funkin.otf",
        "beta": ROOT / "assets" / "fonts" / "pixel.otf",
    }
    stream_sources = {
        "alpha": ROOT / "assets" / "music" / "gameOverEnd-pixel-pico.ogg",
        "beta": ROOT / "assets" / "music" / "gameOverEnd-pico.ogg",
    }
    for owner_name in ("alpha", "beta"):
        root = cpp_source / owner_name
        stream_type = "music" if owner_name == "alpha" else "sound"
        write(root / "Project.xml", cpp_project(cpp_library, stream_type))
        psych_marker(root)
        sound_bytes = pcm_wav(owner_name, "sound")
        music_bytes = pcm_wav(owner_name, "music")
        font_bytes = font_sources[owner_name].read_bytes()
        stream_bytes = stream_sources[owner_name].read_bytes()
        write(root / "assets" / "runtime" / "sound.wav", sound_bytes)
        write(root / "assets" / "runtime" / "music.wav", music_bytes)
        write(root / "assets" / "runtime" / "stream.ogg", stream_bytes)
        write(root / "assets" / "runtime" / "font.otf", font_bytes)
        cpp_owners.append({
            "rootRelative": owner_name,
            "fontSource": font_sources[owner_name].relative_to(ROOT).as_posix(),
            "streamSource": stream_sources[owner_name].relative_to(ROOT).as_posix(),
            "soundSha256": hashlib.sha256(sound_bytes).hexdigest(),
            "musicSha256": hashlib.sha256(music_bytes).hexdigest(),
            "streamSha256": hashlib.sha256(stream_bytes).hexdigest(),
            "fontSha256": hashlib.sha256(font_bytes).hexdigest(),
        })

    unknown_root = unknown
    write(unknown_root / "Project.xml", unknown_project(unknown_library))
    psych_marker(unknown_root)
    write(unknown_root / "assets" / "payload" / "warm.txt", "unknown target text\n")

    request = {
        "kind": "psych-owner-library-typed-media",
        "sourceRoot": str(source.resolve()).replace("\\", "/"),
        "cppSourceRoot": str(cpp_source.resolve()).replace("\\", "/"),
        "unknownSourceRoot": str(unknown.resolve()).replace("\\", "/"),
        "warmLibrary": warm,
        "lazyLibrary": lazy,
        "unknownLibrary": unknown_library,
        "textId": "shared-text",
        "imageId": "shared-image",
        "lazyTextId": "lazy-text",
        "unknownTextId": "unknown-text",
        "owners": owners,
        "cppLibrary": cpp_library,
        "cppSoundId": "shared-sound",
        "cppMusicId": "shared-music",
        "cppStreamMusicId": "stream-music",
        "cppFontId": "shared-font",
        "cppOwners": cpp_owners,
    }
    write(requested / "request.json", json.dumps(request, ensure_ascii=False, indent=2) + "\n")
    return {"fixtureRoot": str(requested.resolve()), "request": str((requested / "request.json").resolve()),
            "sourceRoot": request["sourceRoot"], "unknownSourceRoot": request["unknownSourceRoot"],
            "cppSourceRoot": request["cppSourceRoot"],
            "warmLibrary": warm, "lazyLibrary": lazy, "unknownLibrary": unknown_library}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=TMP / f"owner-library-fixture-{secrets.token_hex(6)}")
    args = parser.parse_args()
    print(json.dumps(create(args.output), indent=2))


if __name__ == "__main__":
    main()
