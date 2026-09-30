"""Apply the pinned hxcpp large-allocation ownership guard used by run.sh."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMMIX_SOURCE = ROOT / ".haxelib/hxcpp/4,3,2/src/hx/gc/Immix.cpp"
SOURCE_SHA256 = "ec9fa2f4ae1e5fce971853ec5ac0e0ddb66cbd3e3d11e814f06bcfbe2058fd96"
PATCHED_SHA256 = "ecbd7484a8d96ed5632e9475bc673b2efce5d9896764d48eb328a521bce7c947"

OLD_SITE = (
    b"   void FreeLarge(void *inLarge)\n"
    b"   {\n"
    b"      ((unsigned char *)inLarge)[HX_ENDIAN_MARK_ID_BYTE] = 0;\n"
    b"      // AllocLarge will not lock this list unless it decides there is a suitable\n"
    b"      //  value, so we can't doa realloc without potentially crashing it.\n"
    b"      if (largeObjectRecycle.hasExtraCapacity(1))\n"
    b"      {\n"
    b"         unsigned int *blob = ((unsigned int *)inLarge) - 2;\n"
    b"         unsigned int size = *blob;\n"
    b"         mLargeListLock.Lock();\n"
    b"         mLargeAllocated -= size;\n"
    b"         // Could somehow keep it in the list, but mark as recycled?\n"
    b"         mLargeList.qerase_val(blob);\n"
    b"         // We could maybe free anyhow?\n"
    b"         if (!largeObjectRecycle.hasExtraCapacity(1))\n"
    b"         {\n"
    b"            mLargeListLock.Unlock();\n"
    b"            HxFree(blob);\n"
    b"            return;\n"
    b"         }\n"
    b"         largeObjectRecycle.push(blob);\n"
    b"         mLargeListLock.Unlock();\n"
    b"      }\n"
    b"   }\n"
    b"\n"
)
NEW_SITE = (
    b"   void FreeLarge(void *inLarge)\n"
    b"   {\n"
    b"      // AllocLarge will not lock this list unless it decides there is a suitable\n"
    b"      //  value, so we can't doa realloc without potentially crashing it.\n"
    b"      if (largeObjectRecycle.hasExtraCapacity(1))\n"
    b"      {\n"
    b"         unsigned int *blob = ((unsigned int *)inLarge) - 2;\n"
    b"         mLargeListLock.Lock();\n"
    b"         // Only a live-list owner may transfer this allocation to the recycler.\n"
    b"         if (!mLargeList.qerase_val(blob))\n"
    b"         {\n"
    b"            mLargeListLock.Unlock();\n"
    b"            return;\n"
    b"         }\n"
    b"         ((unsigned char *)inLarge)[HX_ENDIAN_MARK_ID_BYTE] = 0;\n"
    b"         unsigned int size = *blob;\n"
    b"         mLargeAllocated -= size;\n"
    b"         // We could maybe free anyhow?\n"
    b"         if (!largeObjectRecycle.hasExtraCapacity(1))\n"
    b"         {\n"
    b"            mLargeListLock.Unlock();\n"
    b"            HxFree(blob);\n"
    b"            return;\n"
    b"         }\n"
    b"         largeObjectRecycle.push(blob);\n"
    b"         mLargeListLock.Unlock();\n"
    b"      }\n"
    b"      else\n"
    b"      {\n"
    b"         ((unsigned char *)inLarge)[HX_ENDIAN_MARK_ID_BYTE] = 0;\n"
    b"      }\n"
    b"   }\n"
    b"\n"
)


def sha256(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def patch_source(source: bytes) -> bytes:
    """Patch exactly the pinned source, accept our exact output on reruns."""
    actual_hash = sha256(source)
    if actual_hash == PATCHED_SHA256:
        return source
    if actual_hash != SOURCE_SHA256:
        raise ValueError(
            "hxcpp Immix.cpp differs from the pinned 4.3.2 source; refusing patch "
            f"(sha256 {actual_hash})"
        )
    if source.count(OLD_SITE) != 1:
        raise ValueError("pinned hxcpp FreeLarge ownership site was not unique")
    patched = source.replace(OLD_SITE, NEW_SITE, 1)
    patched_hash = sha256(patched)
    if patched_hash != PATCHED_SHA256:
        raise ValueError(
            "hxcpp FreeLarge patch output did not match its pinned hash "
            f"(sha256 {patched_hash})"
        )
    return patched


def patch_file(path: Path = IMMIX_SOURCE) -> bool:
    """Patch one hxcpp source file; return whether bytes were changed."""
    original = path.read_bytes()
    patched = patch_source(original)
    if patched == original:
        return False
    path.write_bytes(patched)
    return True


def main() -> int:
    try:
        changed = patch_file()
    except (OSError, ValueError) as error:
        print(f"!! hxcpp large-allocation ownership patch failed: {error}")
        return 1
    if changed:
        print(">> patched hxcpp FreeLarge ownership guard")
    else:
        print(">> hxcpp FreeLarge ownership guard already present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
