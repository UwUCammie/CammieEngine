"""Read-only Auto discovery report for the mounted mixed-engine donor.

This is deliberately a bounded source-level harness.  It reuses the same
method extraction used by ``test_mixed_auto_import.py`` and runs only discovery
and V-Slice conversion; it never invokes the destination writer or mutates the
donor tree.
"""

from pathlib import Path
import argparse
from contextlib import nullcontext
import hashlib
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
try:
    from haxe_import_io_stubs import install_import_io_dependencies
except ModuleNotFoundError:
    from tools.haxe_import_io_stubs import install_import_io_dependencies


ROOT = Path(__file__).resolve().parents[1]
HAXE = ROOT / ".tools/haxe/haxe"
NEKO = ROOT / ".tools/neko/neko"
HAXELIB = ROOT / ".tools/haxe/haxelib"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
HXCPP_PACKAGE_VERSION = "4.3.2"
HXCPP_PACKAGE_DIRECTORY = "4,3,2"


def rewrite_diagnostic_filesystem_calls(source: str) -> str:
    """Route plain FileSystem probes without rewriting qualified aliases."""
    return re.sub(r"(?<![A-Za-z0-9_.])FileSystem\.isDirectory\(",
        "DiagnosticFileSystem.isDirectory(", source)


HXCPP_CAPTURE_SOURCE = Path("src/hx/gc/GcRegCapture.cpp")
HXCPP_CAPTURE_SOURCE_SHA256 = "5efb58fd1956070beb4028b1c58b817838fc5f1750e36404bca91750fcc23204"
HXCPP_IMMIX_SOURCE = Path("src/hx/gc/Immix.cpp")
HXCPP_IMMIX_SOURCE_SHA256 = "ec9fa2f4ae1e5fce971853ec5ac0e0ddb66cbd3e3d11e814f06bcfbe2058fd96"
HXCPP_IMMIX_MANAGED_SOURCE_SHA256 = "ecbd7484a8d96ed5632e9475bc673b2efce5d9896764d48eb328a521bce7c947"
HXCPP_IMMIX_CONSERVATIVE_SHA256 = "8666d05ef66f63da02ea485d208d8161cafe7a164d21840fb09a9fe62def8bcd"
HXCPP_IMMIX_MANAGED_CONSERVATIVE_SHA256 = "bd0d34501dfb509b50977aacccb8a31ba49bc9a38dcf6c154a9ed15c578d5052"
RECYCLE_DIAGNOSTIC_VERSION = "private-large-recycle-row-span-v4"
ASAN_DIAGNOSTIC_VERSION = "asan-gc-stack-copy-v4"
ASAN_FLAGS = ("-fsanitize=address", "-g", "-fno-omit-frame-pointer")
ASAN_HXCPP_BUILD_ARGS = ("-DHXCPP_VERBOSE", "-DHXCPP_DEBUG_LINK")
ASAN_RUNTIME_OPTIONS = "detect_stack_use_after_return=0:abort_on_error=1:halt_on_error=1:detect_leaks=0:symbolize=1"


def native_scan_cache_key(
    fixture_root: Path, gc_debug_level_1: bool = False, asan: bool = False,
    recycle_diagnostics: bool = False,
) -> str:
    """Key the compiled scanner to its fixture and local Haxe toolchain.

    Donor files are deliberately excluded: the cached executable reads them
    afresh on every run. The fixture sources are hashed by content, while the
    pinned compiler/stdlib/hxcpp tree is tracked by file metadata so a local
    toolchain patch invalidates the binary without reading thousands of files.
    """
    digest = hashlib.sha256(b"auto-import-native-scan-v1\0")
    for path in sorted(fixture_root.glob("*.hx")):
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    for root in (ROOT / ".tools/haxe/std", ROOT / ".haxelib/hscript/2,5,0",
                 ROOT / ".haxelib/hxcpp" / HXCPP_PACKAGE_DIRECTORY):
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            stat = path.stat()
            digest.update(str(path.relative_to(root)).encode())
            digest.update(f"\0{stat.st_size}\0{stat.st_mtime_ns}\0".encode())
    for path in (HAXE, HAXELIB, NEKO):
        stat = path.stat()
        digest.update(str(path).encode())
        digest.update(f"\0{stat.st_size}\0{stat.st_mtime_ns}\0".encode())
    if sum((gc_debug_level_1, asan, recycle_diagnostics)) > 1:
        raise ValueError("native scanner diagnostic modes are mutually exclusive")
    # Preserve the long-standing normal and GC-debug cache keys. ASan has a
    # separate identity because it changes compiler/runtime instrumentation and
    # uses a narrowly patched private hxcpp copy.
    if gc_debug_level_1:
        digest.update(b"\0HXCPP_GC_DEBUG_LEVEL=1\0")
    if asan:
        compiler = shutil.which("g++")
        if compiler is None:
            raise RuntimeError("ASan scanner mode requires g++")
        compiler_path = Path(compiler).resolve()
        stat = compiler_path.stat()
        digest.update(f"\0{ASAN_DIAGNOSTIC_VERSION}\0".encode())
        digest.update("\0".join(ASAN_FLAGS).encode())
        digest.update("\0".join(ASAN_HXCPP_BUILD_ARGS).encode())
        digest.update(f"\0{compiler_path}\0{stat.st_size}\0{stat.st_mtime_ns}\0".encode())
        digest.update(HXCPP_CAPTURE_SOURCE_SHA256.encode())
        digest.update(HXCPP_IMMIX_SOURCE_SHA256.encode())
    if recycle_diagnostics:
        digest.update(f"\0{RECYCLE_DIAGNOSTIC_VERSION}\0".encode())
        digest.update(HXCPP_IMMIX_SOURCE_SHA256.encode())
    return digest.hexdigest()


def native_scan_build_args(
    gc_debug_level_1: bool = False, asan: bool = False,
    recycle_diagnostics: bool = False,
) -> list[str]:
    """Return hxcpp flags for ordinary, GC-debug, or isolated ASan builds."""
    if sum((gc_debug_level_1, asan, recycle_diagnostics)) > 1:
        raise ValueError("native scanner diagnostic modes are mutually exclusive")
    args = ["-DHXCPP_COMPILE_THREADS=4"]
    if gc_debug_level_1:
        args.append("-DHXCPP_GC_DEBUG_LEVEL=1")
    if asan:
        args.extend(ASAN_HXCPP_BUILD_ARGS)
    if recycle_diagnostics:
        args.append("-DHXCPP_DEBUG_LINK")
    return args


def patch_gc_stack_capture_source(source: bytes) -> bytes:
    """Exempt hxcpp's intentional active-stack copy from ASan's stack bounds.

    hxcpp scans the live native stack as part of its collector. The ASan
    memcpy interceptor interprets that deliberate range copy as a stack
    overread, so this private diagnostic copy substitutes an uninstrumented
    byte copy only for the one pinned source version. The normal build keeps
    the original memcpy path.
    """
    actual_hash = hashlib.sha256(source).hexdigest()
    if actual_hash != HXCPP_CAPTURE_SOURCE_SHA256:
        raise ValueError(
            "pinned hxcpp GcRegCapture.cpp changed; refusing unreviewed ASan patch "
            f"(sha256 {actual_hash})"
        )
    function_marker = (
        b"int RegisterCapture::Capture(int *inTopOfStack,int **inBuf,int &outSize,int inMaxSize, int *inBottom)\r\n"
        b"{\r\n"
    )
    copy_site = (
        b"\tif (size>0)\r\n"
        b"\t   memcpy(inBuf,inBottom,size*sizeof(void*));\r\n"
    )
    helper = (
        b"#if defined(__SANITIZE_ADDRESS__)\r\n"
        b"// The collector deliberately scans this active native stack range.\r\n"
        b"__attribute__((no_sanitize_address, noinline))\r\n"
        b"static void hxcppCopyActiveStackWords(void *out, const void *in, size_t bytes)\r\n"
        b"{\r\n"
        b"   volatile unsigned char *dst = (volatile unsigned char *)out;\r\n"
        b"   const volatile unsigned char *src = (const volatile unsigned char *)in;\r\n"
        b"   for (size_t i = 0; i < bytes; ++i) dst[i] = src[i];\r\n"
        b"}\r\n"
        b"#endif\r\n\r\n"
    )
    replacement = (
        b"\tif (size>0)\r\n"
        b"#if defined(__SANITIZE_ADDRESS__)\r\n"
        b"\t   hxcppCopyActiveStackWords(inBuf,inBottom,size*sizeof(void*));\r\n"
        b"#else\r\n"
        b"\t   memcpy(inBuf,inBottom,size*sizeof(void*));\r\n"
        b"#endif\r\n"
    )
    if source.count(function_marker) != 1 or source.count(copy_site) != 1:
        raise ValueError("pinned hxcpp active-stack copy site was not uniquely found")
    source = source.replace(function_marker, helper + function_marker, 1)
    return source.replace(copy_site, replacement, 1)


def patch_gc_conservative_root_source(source: bytes) -> bytes:
    """Exempt only hxcpp's intentional native-stack word load from ASan.

    MarkConservative reads overlapping pointer-sized words from a native stack
    range. ASan sees the first 8-byte read across the 4-byte ``dummy`` marker
    as an overflow, even though the adjacent bytes are part of that same live
    stack. Keep every allocation and all other code instrumented. Accept the
    pristine source and the exact run.sh-managed FreeLarge patch so private
    diagnostic copies retain the production ownership guard.
    """
    actual_hash = hashlib.sha256(source).hexdigest()
    expected_output_hash = {
        HXCPP_IMMIX_SOURCE_SHA256: HXCPP_IMMIX_CONSERVATIVE_SHA256,
        HXCPP_IMMIX_MANAGED_SOURCE_SHA256: HXCPP_IMMIX_MANAGED_CONSERVATIVE_SHA256,
    }.get(actual_hash)
    if expected_output_hash is None:
        raise ValueError(
            "pinned hxcpp Immix.cpp changed; refusing unreviewed ASan patch "
            f"(sha256 {actual_hash})"
        )
    function_marker = b"void MarkConservative(int *inBottom, int *inTop,hx::MarkContext *__inCtx)\n{"
    load_site = b"      void *vptr = *(void **)ptr;"
    helper = (
        b"#if defined(__SANITIZE_ADDRESS__)\n"
        b"// Conservative GC deliberately reads overlapping pointer words on the live stack.\n"
        b"__attribute__((no_sanitize_address, noinline))\n"
        b"static void *hxcppReadConservativeRootWord(const int *ptr)\n"
        b"{\n"
        b"   return *(void * const *)ptr;\n"
        b"}\n"
        b"#endif\n\n"
    )
    replacement = (
        b"#if defined(__SANITIZE_ADDRESS__)\n"
        b"      void *vptr = hxcppReadConservativeRootWord(ptr);\n"
        b"#else\n"
        + load_site + b"\n"
        b"#endif"
    )
    if source.count(function_marker) != 1 or source.count(load_site) != 1:
        raise ValueError("pinned hxcpp conservative root load was not uniquely found")
    source = source.replace(function_marker, helper + function_marker, 1)
    patched = source.replace(load_site, replacement, 1)
    patched_hash = hashlib.sha256(patched).hexdigest()
    if patched_hash != expected_output_hash:
        raise ValueError(
            "pinned hxcpp conservative-root patch output changed; refusing "
            f"(sha256 {patched_hash})"
        )
    return patched


def patch_gc_recycler_source(source: bytes) -> bytes:
    """Instrument private hxcpp's recycler transitions and GC row-mark bounds.

    The pinned normal-core failure freed the same recycler pointer at adjacent
    indexes. This probe checks insertions, reuse, and the pre-free vector, with
    bounded allocation-free transition history and no user payload bytes.
    Row-span validation stops before a malformed header can overrun the table.
    """
    actual_hash = hashlib.sha256(source).hexdigest()
    managed_free_large = actual_hash == HXCPP_IMMIX_MANAGED_CONSERVATIVE_SHA256
    if actual_hash not in (HXCPP_IMMIX_CONSERVATIVE_SHA256,
                           HXCPP_IMMIX_MANAGED_CONSERVATIVE_SHA256):
        raise ValueError(
            "pinned hxcpp Immix.cpp conservative patch changed; refusing unreviewed recycler probe "
            f"(sha256 {actual_hash})"
        )
    include_site = b"#include <stdlib.h>\n"
    class_site = b"class GlobalAllocator\n{"
    free_site = (
        b"         mLargeAllocated -= size;\n"
        b"         // Could somehow keep it in the list, but mark as recycled?\n"
        b"         mLargeList.qerase_val(blob);\n"
    )
    managed_free_site = (
        b"         // Only a live-list owner may transfer this allocation to the recycler.\n"
        b"         if (!mLargeList.qerase_val(blob))\n"
        b"         {\n"
        b"            mLargeListLock.Unlock();\n"
        b"            return;\n"
        b"         }\n"
        b"         ((unsigned char *)inLarge)[HX_ENDIAN_MARK_ID_BYTE] = 0;\n"
        b"         unsigned int size = *blob;\n"
        b"         mLargeAllocated -= size;\n"
    )
    selected_free_site = managed_free_site if managed_free_large else free_site
    free_push_site = (
        b"         largeObjectRecycle.push(blob);\n"
        b"         mLargeListLock.Unlock();\n"
    )
    sweep_push_site = (
        b"               recycleRemaining -= size;\n"
        b"               largeObjectRecycle.push(blob);\n"
    )
    reuse_site = (
        b"               result = largeObjectRecycle[i];\n"
        b"               largeObjectRecycle.qerase(i);\n"
    )
    reuse_scan_site = b"            if ( largeObjectRecycle[i][0] == inSize )\n            {\n"
    reuse_lock_site = (
        b"                  if (  i>=largeObjectRecycle.size() || largeObjectRecycle[i][0] != inSize )\n"
        b"                     continue;\n"
    )
    pre_free_site = (
        b"      int l2 = largeObjectRecycle.size();\n"
        b"      for(int i=0;i<largeObjectRecycle.size();i++)\n"
        b"         HxFree(largeObjectRecycle[i]);\n"
        b"      largeObjectRecycle.setSize(0);\n"
    )
    trace_member_site = b"   hx::QuickVec<unsigned int *> largeObjectRecycle;\n"
    constructor_site = b"      mGenerationalRetainEstimate = 0.5;\n"
    alloc_result_site = b"      unsigned int *result = 0;\n"
    live_add_site = b"      mLargeList.push(result);\n      mLargeAllocated += inSize;\n"
    for marker in (include_site, class_site, selected_free_site, free_push_site, sweep_push_site,
                   reuse_site, reuse_scan_site, reuse_lock_site, pre_free_site,
                   trace_member_site, constructor_site, alloc_result_site, live_add_site):
        if source.count(marker) != 1:
            raise ValueError("pinned hxcpp large-recycler probe site was not uniquely found")
    source = source.replace(include_site, include_site + b"#include <execinfo.h>\n#include <pthread.h>\n#include <stdint.h>\n", 1)
    # Both retained normal-GC cores contain damage at the first allocation
    # after a block's row-mark table. Catch a bad mark span before it can write
    # there, without enabling GC-debug's different recursive marking policy.
    mark_site = b"void MarkAllocUnchecked(void *inPtr,hx::MarkContext *__inCtx)\n"
    rows_site = b"   int rows = flags & IMMIX_ALLOC_ROW_COUNT;\n   if (rows)\n   {\n"
    if source.count(mark_site) != 1 or source.count(rows_site) != 2:
        raise ValueError("pinned hxcpp row-mark probe sites were not uniquely found")
    row_probe = b'''// Private diagnostic: validate the row table before marking it.
static void hxcppCheckMarkRows(size_t ptr_i, unsigned int flags)
{
   unsigned int rows = flags & IMMIX_ALLOC_ROW_COUNT;
   unsigned int startRow = (ptr_i & IMMIX_BLOCK_OFFSET_MASK) >> IMMIX_LINE_BITS;
   if (rows && startRow + rows > IMMIX_LINES)
   {
      fprintf(stderr, "HXCPP_ROW_MARK_VIOLATION|ptr=%p|flags=%08x|start=%u|rows=%u\\n",
         (void *)(ptr_i + sizeof(int)), flags, startRow, rows);
      fflush(stderr);
      void *frames[48];
      int count = backtrace(frames, 48);
      backtrace_symbols_fd(frames, count, 2);
      abort();
   }
}
// End private row-mark diagnostic.

'''
    source = source.replace(mark_site, row_probe + mark_site, 1)
    source = source.replace(rows_site, b"   hxcppCheckMarkRows(ptr_i, flags);\n" + rows_site)
    report = (
        b"// Private diagnostic: stop at the first recycler invariant violation.\n"
        b"static void hxcppReportLargeRecycleViolation(const char *kind, unsigned int *blob, unsigned int size, int index)\n"
        b"{\n"
        b"   fprintf(stderr, \"HXCPP_RECYCLE_VIOLATION|%s|ptr=%p|size=%u|index=%d\\n\", kind, (void *)blob, size, index);\n"
        b"   fflush(stderr);\n"
        b"   void *frames[24];\n"
        b"   int count = backtrace(frames, 24);\n"
        b"   backtrace_symbols_fd(frames, count, 2);\n"
        b"   abort();\n"
        b"}\n\n"
    )
    source = source.replace(class_site, report + class_site, 1)
    trace_members = b"""   // Private diagnostic only: fixed storage, no allocator calls on transitions.
   struct RecycleEvent
   {
      unsigned long long sequence;
      const char *action;
      unsigned int *blob;
      void *storage;
      unsigned long thread;
      int index;
      int size;
   };
   RecycleEvent hxcppRecycleEvents[256];
   unsigned long long hxcppRecycleSequence;

"""
    source = source.replace(trace_member_site, trace_member_site + trace_members, 1)
    source = source.replace(constructor_site, constructor_site + b"      hxcppRecycleSequence = 0;\n", 1)
    free_method = b"   void FreeLarge(void *inLarge)\n"
    if source.count(free_method) != 1:
        raise ValueError("pinned hxcpp FreeLarge method was not uniquely found")
    recycle_helpers = (
        b"   void hxcppRecycleRecord(const char *action, unsigned int *blob, int index)\n"
        b"   {\n"
        b"      unsigned long long sequence = ++hxcppRecycleSequence;\n"
        b"      RecycleEvent &event = hxcppRecycleEvents[(sequence - 1) % 256];\n"
        b"      event.action = action;\n"
        b"      event.blob = blob;\n"
        b"      event.storage = largeObjectRecycle.mPtr;\n"
        b"      event.thread = (unsigned long)pthread_self();\n"
        b"      event.index = index;\n"
        b"      event.size = largeObjectRecycle.size();\n"
        b"      event.sequence = sequence;\n"
        b"   }\n\n"
        b"   void hxcppRecycleViolation(const char *kind, unsigned int *blob, unsigned int size, int index)\n"
        b"   {\n"
        b"      unsigned long long first = hxcppRecycleSequence > 256 ? hxcppRecycleSequence - 255 : 1;\n"
        b"      fprintf(stderr, \"HXCPP_RECYCLE_HISTORY|first=%llu|last=%llu|capacity=256|truncated=%d|sync=large-list-lock-or-collector-stop\\n\",\n"
        b"         first, hxcppRecycleSequence, hxcppRecycleSequence>256);\n"
        b"      for (unsigned long long sequence=first; sequence<=hxcppRecycleSequence; sequence++)\n"
        b"      {\n"
        b"         RecycleEvent &event = hxcppRecycleEvents[(sequence - 1) % 256];\n"
        b"         if (event.sequence==sequence && (event.blob==blob || sequence+16>hxcppRecycleSequence))\n"
        b"            fprintf(stderr, \"HXCPP_RECYCLE_EVENT|seq=%llu|action=%s|ptr=%p|index=%d|size=%d|storage=%p|thread=%lu\\n\",\n"
        b"               event.sequence, event.action, (void *)event.blob, event.index, event.size, event.storage, event.thread);\n"
        b"      }\n"
        b"      hxcppReportLargeRecycleViolation(kind, blob, size, index);\n"
        b"   }\n\n"
        b"   int hxcppRecycleIndex(unsigned int *blob)\n"
        b"   {\n"
        b"      for(int i=0;i<largeObjectRecycle.size();i++)\n"
        b"         if (largeObjectRecycle[i]==blob) return i;\n"
        b"      return -1;\n"
        b"   }\n\n"
        b"   // A mismatch proves a changed sequence; a match is probabilistic evidence only.\n"
        b"   unsigned long long hxcppRecyclePrefixFingerprint(int count)\n"
        b"   {\n"
        b"      unsigned long long hash = 1469598103934665603ULL;\n"
        b"      for (int i=0;i<count;i++)\n"
        b"         hash = (hash ^ (uintptr_t)largeObjectRecycle[i]) * 1099511628211ULL;\n"
        b"      return hash;\n"
        b"   }\n\n"
        b"   unsigned long long hxcppRecycleExpectedQeraseFingerprint(int index)\n"
        b"   {\n"
        b"      int last = largeObjectRecycle.size() - 1;\n"
        b"      unsigned long long hash = 1469598103934665603ULL;\n"
        b"      for (int i=0;i<last;i++)\n"
        b"      {\n"
        b"         unsigned int *entry = i==index ? largeObjectRecycle[last] : largeObjectRecycle[i];\n"
        b"         hash = (hash ^ (uintptr_t)entry) * 1099511628211ULL;\n"
        b"      }\n"
        b"      return hash;\n"
        b"   }\n\n"
        b"   void hxcppRecycleCheckUnique(const char *kind)\n"
        b"   {\n"
        b"      for (int i=0;i<largeObjectRecycle.size();i++)\n"
        b"         for (int j=0;j<i;j++)\n"
        b"            if (largeObjectRecycle[i]==largeObjectRecycle[j])\n"
        b"               hxcppRecycleViolation(kind, largeObjectRecycle[i], 0, i);\n"
        b"   }\n\n"
    )
    source = source.replace(free_method, recycle_helpers + free_method, 1)
    if managed_free_large:
        diagnostic_free_replacement = (
            b"         // Only a live-list owner may transfer this allocation to the recycler.\n"
            b"         if (!mLargeList.qerase_val(blob))\n"
            b"         {\n"
            b"            mLargeListLock.Unlock();\n"
            b"            hxcppRecycleViolation(\"missing-live-list\", blob, 0, -1);\n"
            b"            return;\n"
            b"         }\n"
            b"         ((unsigned char *)inLarge)[HX_ENDIAN_MARK_ID_BYTE] = 0;\n"
            b"         unsigned int size = *blob;\n"
            b"         mLargeAllocated -= size;\n"
        )
    else:
        diagnostic_free_replacement = (
            b"         // A second release must not enter the recycle vector.\n"
            b"         if (!mLargeList.qerase_val(blob))\n"
            b"            hxcppRecycleViolation(\"missing-live-list\", blob, size, -1);\n"
            b"         mLargeAllocated -= size;\n"
        )
    source = source.replace(selected_free_site, diagnostic_free_replacement, 1)
    source = source.replace(
        free_push_site,
        b"         int duplicateIndex = hxcppRecycleIndex(blob);\n"
        b"         if (duplicateIndex>=0)\n"
        b"            hxcppRecycleViolation(\"duplicate-explicit\", blob, size, duplicateIndex);\n"
        b"         int oldRecycleSize = largeObjectRecycle.size();\n"
        b"         unsigned long long oldRecyclePrefix = hxcppRecyclePrefixFingerprint(oldRecycleSize);\n"
        b"         largeObjectRecycle.push(blob);\n"
        b"         hxcppRecycleRecord(\"push-explicit\", blob, oldRecycleSize);\n"
        b"         if (largeObjectRecycle.size()!=oldRecycleSize+1 || largeObjectRecycle[oldRecycleSize]!=blob ||\n"
        b"             hxcppRecyclePrefixFingerprint(oldRecycleSize)!=oldRecyclePrefix)\n"
        b"            hxcppRecycleViolation(\"push-corruption-explicit\", blob, size, oldRecycleSize);\n"
        b"         mLargeListLock.Unlock();\n",
        1,
    )
    source = source.replace(
        sweep_push_site,
        b"               recycleRemaining -= size;\n"
        b"               int duplicateIndex = hxcppRecycleIndex(blob);\n"
        b"               if (duplicateIndex>=0)\n"
        b"                  hxcppRecycleViolation(\"duplicate-sweep\", blob, size, duplicateIndex);\n"
        b"               int oldRecycleSize = largeObjectRecycle.size();\n"
        b"               unsigned long long oldRecyclePrefix = hxcppRecyclePrefixFingerprint(oldRecycleSize);\n"
        b"               largeObjectRecycle.push(blob);\n"
        b"               hxcppRecycleRecord(\"push-sweep\", blob, oldRecycleSize);\n"
        b"               if (largeObjectRecycle.size()!=oldRecycleSize+1 || largeObjectRecycle[oldRecycleSize]!=blob ||\n"
        b"                   hxcppRecyclePrefixFingerprint(oldRecycleSize)!=oldRecyclePrefix)\n"
        b"                  hxcppRecycleViolation(\"push-corruption-sweep\", blob, size, oldRecycleSize);\n",
        1,
    )
    source = source.replace(
        reuse_scan_site,
        b"            unsigned int *observedCandidate = largeObjectRecycle[i];\n"
        b"            if ( observedCandidate[0] == inSize )\n"
        b"            {\n",
        1,
    )
    source = source.replace(
        reuse_lock_site,
        reuse_lock_site
        + b"                  if (observedCandidate != largeObjectRecycle[i])\n"
        b"                  {\n"
        b"                     hxcppRecycleRecord(\"candidate-observed\", observedCandidate, i);\n"
        b"                     hxcppRecycleRecord(\"candidate-locked\", largeObjectRecycle[i], i);\n"
        b"                  }\n",
        1,
    )
    source = source.replace(
        reuse_site,
        b"               unsigned int *candidate = largeObjectRecycle[i];\n"
        b"               if (candidate[0]!=inSize)\n"
        b"                  hxcppRecycleViolation(\"candidate-size-changed\", candidate, inSize, i);\n"
        b"               int oldRecycleSize = largeObjectRecycle.size();\n"
        b"               unsigned long long expectedAfterErase = hxcppRecycleExpectedQeraseFingerprint(i);\n"
        b"               result = candidate;\n"
        b"               largeObjectRecycle.qerase(i);\n"
        b"               hxcppRecycleRecord(\"reuse\", result, i);\n"
        b"               if (largeObjectRecycle.size()!=oldRecycleSize-1 || hxcppRecycleIndex(result)>=0 ||\n"
        b"                   hxcppRecyclePrefixFingerprint(oldRecycleSize-1)!=expectedAfterErase)\n"
        b"                  hxcppRecycleViolation(\"reuse-corruption\", result, inSize, i);\n",
        1,
    )
    source = source.replace(alloc_result_site, alloc_result_site + b"      bool reusedFromRecycle = false;\n", 1)
    source = source.replace(
        b"               hxcppRecycleRecord(\"reuse\", result, i);\n",
        b"               reusedFromRecycle = true;\n"
        b"               hxcppRecycleRecord(\"reuse\", result, i);\n",
        1,
    )
    source = source.replace(
        live_add_site,
        b"      if (reusedFromRecycle)\n"
        b"      {\n"
        b"         for (int j=0;j<mLargeList.size();j++)\n"
        b"            if (mLargeList[j]==result)\n"
        b"               hxcppRecycleViolation(\"duplicate-live-reuse\", result, inSize, j);\n"
        b"         hxcppRecycleRecord(\"live-add\", result, mLargeList.size());\n"
        b"      }\n"
        + live_add_site,
        1,
    )
    source = source.replace(
        pre_free_site,
        b"      hxcppRecycleCheckUnique(\"duplicate-before-free\");\n"
        b"      int l2 = largeObjectRecycle.size();\n"
        b"      for(int i=0;i<largeObjectRecycle.size();i++)\n"
        b"      {\n"
        b"         unsigned int *blob = largeObjectRecycle[i];\n"
        b"         hxcppRecycleRecord(\"free\", blob, i);\n"
        b"         HxFree(blob);\n"
        b"      }\n"
        b"      largeObjectRecycle.setSize(0);\n"
        b"      hxcppRecycleRecord(\"reset\", 0, -1);\n"
        b"      if (largeObjectRecycle.size()!=0)\n"
        b"         hxcppRecycleViolation(\"reset-corruption\", 0, 0, -1);\n",
        1,
    )
    return source


def prepare_private_haxelib_overlay(source_root: Path, destination_root: Path) -> Path:
    """Create a private haxelib repo with a copied and guarded hxcpp package."""
    destination_root.mkdir(parents=True, exist_ok=False)
    for package in source_root.iterdir():
        target = destination_root / package.name
        if package.name != "hxcpp":
            target.symlink_to(package.resolve(), target_is_directory=True)
            continue
        version_file = package / ".current"
        version = version_file.read_text().strip()
        if version != HXCPP_PACKAGE_VERSION or not version or "/" in version or "\\" in version:
            raise ValueError(f"unexpected active hxcpp version: {version!r}")
        version_source = package / HXCPP_PACKAGE_DIRECTORY
        if version_source.is_symlink() or not version_source.is_dir():
            raise FileNotFoundError(f"active hxcpp package is missing: {version_source}")
        for relative, name in ((HXCPP_CAPTURE_SOURCE, "active-stack"),
                               (HXCPP_IMMIX_SOURCE, "conservative-root")):
            source_file = version_source / relative
            if source_file.is_symlink() or not source_file.is_file():
                raise ValueError(f"pinned hxcpp {name} source must be a regular package file")
            try:
                source_file.resolve().relative_to(version_source.resolve())
            except ValueError as error:
                raise ValueError(f"pinned hxcpp {name} source escapes its package") from error
        target.mkdir()
        shutil.copy2(version_file, target / ".current")
        private_version = target / HXCPP_PACKAGE_DIRECTORY
        shutil.copytree(version_source, private_version, symlinks=True)
        capture = private_version / HXCPP_CAPTURE_SOURCE
        if capture.is_symlink() or not capture.is_file():
            raise ValueError("copied hxcpp active-stack source is not a private regular file")
        try:
            capture.resolve().relative_to(destination_root.resolve())
        except ValueError as error:
            raise ValueError("copied hxcpp active-stack source escapes the private overlay") from error
        capture.write_bytes(patch_gc_stack_capture_source(capture.read_bytes()))
        immix = private_version / HXCPP_IMMIX_SOURCE
        if immix.is_symlink() or not immix.is_file():
            raise ValueError("copied hxcpp conservative-root source is not a private regular file")
        try:
            immix.resolve().relative_to(destination_root.resolve())
        except ValueError as error:
            raise ValueError("copied hxcpp conservative-root source escapes the private overlay") from error
        immix.write_bytes(patch_gc_recycler_source(
            patch_gc_conservative_root_source(immix.read_bytes())
        ))
    if not (destination_root / "hxcpp" / ".current").is_file():
        raise FileNotFoundError("source haxelib repo does not contain hxcpp")
    return destination_root


def asan_cxx_wrapper_text(compiler: Path, argument_log: Path) -> str:
    """Return a local shell wrapper that records and applies sanitizer flags."""
    compiler_q = shlex.quote(str(compiler.resolve()))
    log_q = shlex.quote(str(argument_log.resolve()))
    flags_q = " ".join(shlex.quote(flag) for flag in ASAN_FLAGS)
    return "\n".join((
        "#!/bin/sh",
        f"log_dir={log_q}",
        "mkdir -p \"$log_dir\"",
        "log_file=\"$log_dir/asan-cxx-$$.tsv\"",
        "{",
        "  printf 'cwd\\t%s\\n' \"$PWD\"",
        f"  printf 'compiler\\t%s\\n' {compiler_q}",
        f"  for arg in {flags_q} \"$@\"; do printf 'arg\\t%s\\n' \"$arg\"; done",
        "} > \"$log_file\"",
        f"exec {compiler_q} {flags_q} \"$@\"",
        "",
    ))


def asan_cxx_command(wrapper: Path, root_dir_fd: int, process_id: int | None = None) -> str:
    """Return a space-free absolute /proc path to a workspace-local wrapper.

    The scanner checkout path contains spaces. hxcpp invokes compiler names
    without shell quoting, so use the diagnosing process' open repository-root
    directory descriptor to form an absolute kernel path without those spaces.
    """
    relative = wrapper.resolve().relative_to(ROOT.resolve())
    owner_pid = os.getpid() if process_id is None else process_id
    return f"/proc/{owner_pid}/fd/{root_dir_fd}/{relative.as_posix()}"


def haxelib_path_command(haxelib: Path, private_repo: bool = False) -> list[str]:
    command = [str(haxelib)]
    if private_repo:
        command.append("--global")
    command.extend(("path", "hxcpp"))
    return command


def hxcpp_build_command(haxelib: Path, args: list[str], private_repo: bool = False) -> list[str]:
    command = [str(haxelib)]
    if private_repo:
        command.append("--global")
    command.extend(("run", "hxcpp", "Build.xml", *args))
    return command


def haxelib_paths_are_private(output: str, private_repo: Path) -> bool:
    """Accept hxcpp path output only if every path is inside our overlay."""
    root = private_repo.resolve()
    paths: list[Path] = []
    for line in output.splitlines():
        value = line.strip()
        if not value or value.startswith("-D "):
            continue
        path = Path(value)
        if not path.is_absolute():
            return False
        try:
            resolved = path.resolve()
            resolved.relative_to(root)
        except (OSError, ValueError):
            return False
        paths.append(resolved)
    return bool(paths)


def asan_runtime_env(base: dict[str, str], project_tmp: Path) -> dict[str, str]:
    env = base.copy()
    env["TMPDIR"] = str(project_tmp)
    env["ASAN_OPTIONS"] = ASAN_RUNTIME_OPTIONS
    env["SDL_AUDIODRIVER"] = "dummy"
    return env


def asan_build_env(base: dict[str, str]) -> dict[str, str]:
    """Clear any inherited GC debug define so ASan uses the normal GC mode."""
    env = base.copy()
    env.pop("HXCPP_GC_DEBUG_LEVEL", None)
    env["HXCPP_VERBOSE"] = "1"
    return env


def save_process_output(result: subprocess.CompletedProcess[str], directory: Path, stem: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{stem}.stdout").write_text(result.stdout or "")
    (directory / f"{stem}.stderr").write_text(result.stderr or "")


def save_build_inputs(cpp_target: Path, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name in ("Build.xml", "Options.txt"):
        source = cpp_target / name
        if source.is_file():
            shutil.copy2(source, directory / name)


def run_bounded_native_scan(
    command: list[str], cwd: Path, env: dict[str, str], timeout: float
) -> tuple[subprocess.CompletedProcess[str], bool]:
    """Keep partial sanitizer output when a bounded scan reaches its deadline."""
    try:
        return subprocess.run(
            command, cwd=cwd, env=env, capture_output=True,
            text=True, timeout=timeout,
        ), False
    except subprocess.TimeoutExpired as error:
        def as_text(value: bytes | str | None) -> str:
            if value is None:
                return ""
            return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value

        return subprocess.CompletedProcess(
            command, 124, as_text(error.stdout), as_text(error.stderr)
        ), True


def parse_arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, default=DONOR)
    parser.add_argument("--summary", action="store_true",
                        help="print a concise scan summary")
    parser.add_argument("--counts-only", action="store_true",
                        help="print only aggregate diagnostic counts")
    parser.add_argument(
        "--trace-psych-discovery", action="store_true",
        help="print chart, section, and row provenance during Psych script discovery",
    )
    parser.add_argument(
        "--codename-event-walk", action="store_true",
        help="run only Codename song conversion plus authored-event array checks on one worker thread",
    )
    parser.add_argument(
        "--gc-debug-level-1",
        action="store_true",
        help="compile the native scanner with HXCPP_GC_DEBUG_LEVEL=1",
    )
    parser.add_argument(
        "--asan",
        action="store_true",
        help="build and run the native scanner with isolated AddressSanitizer instrumentation",
    )
    parser.add_argument(
        "--recycle-diagnostics", action="store_true",
        help="use a private, normal-GC hxcpp copy with recycler and row-mark invariant checks",
    )
    def positive_seconds(value: str) -> float:
        try:
            seconds = float(value)
        except ValueError as error:
            raise argparse.ArgumentTypeError("scan timeout must be a positive number of seconds") from error
        if not math.isfinite(seconds) or seconds <= 0:
            raise argparse.ArgumentTypeError("scan timeout must be a finite positive number of seconds")
        return seconds

    parser.add_argument(
        "--scan-timeout-seconds", type=positive_seconds, default=300.0,
        help="limit the native scanner run in seconds (default: 300; compilation has its own bound)",
    )
    args = parser.parse_args(argv)
    if sum((args.gc_debug_level_1, args.asan, args.recycle_diagnostics)) > 1:
        parser.error("--asan, --recycle-diagnostics and --gc-debug-level-1 are mutually exclusive")
    return args


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated method: {marker}")


def instrument_codename_event_walk(method: str) -> str:
    """Add index-only markers around the real authored-event array checks.

    Never stringify a candidate Dynamic here: if its object header is stale,
    formatting it can trigger the same invalid virtual call before the marker
    identifies which nested access was reached.
    """
    replacements = (
        (
            "var names:Array<String> = [];",
            "var names:Array<String> = [];\n\t\tvar traceChartIndex = 0;",
        ),
        (
            "for (chart in songData.convertedCharts) {",
            "for (chart in songData.convertedCharts) {\n\t\t\tvar traceChart = traceChartIndex++;",
        ),
        (
            "if (!Std.isOfType(groups, Array)) continue;",
            "diagnosticEventWalkMarker('CODEVENT_CHECK|groups|before|chart=' + traceChart);\n"
            "\t\t\tvar groupsAreArray = Std.isOfType(groups, Array);\n"
            "\t\t\tdiagnosticEventWalkMarker('CODEVENT_CHECK|groups|after|chart=' + traceChart + '|array=' + groupsAreArray);\n"
            "\t\t\tif (!groupsAreArray) continue;",
        ),
        (
            "for (group in (cast groups:Array<Dynamic>)) {",
            "var traceGroupIndex = 0;\n\t\t\tfor (group in (cast groups:Array<Dynamic>)) {\n"
            "\t\t\t\tvar traceGroup = traceGroupIndex++;",
        ),
        (
            "if (!Std.isOfType(group, Array) || group.length < 2 || !Std.isOfType(group[1], Array)) continue;",
            "diagnosticEventWalkMarker('CODEVENT_CHECK|group|before|chart=' + traceChart + '|group=' + traceGroup);\n"
            "\t\t\t\tvar groupIsArray = Std.isOfType(group, Array);\n"
            "\t\t\t\tdiagnosticEventWalkMarker('CODEVENT_CHECK|group|after|chart=' + traceChart + '|group=' + traceGroup + '|array=' + groupIsArray);\n"
            "\t\t\t\tif (!groupIsArray) continue;\n"
            "\t\t\t\tdiagnosticEventWalkMarker('CODEVENT_CHECK|group-length|before|chart=' + traceChart + '|group=' + traceGroup);\n"
            "\t\t\t\tvar groupLength:Int = cast group.length;\n"
            "\t\t\t\tdiagnosticEventWalkMarker('CODEVENT_CHECK|group-length|after|chart=' + traceChart + '|group=' + traceGroup + '|length=' + groupLength);\n"
            "\t\t\t\tif (groupLength < 2) continue;\n"
            "\t\t\t\tdiagnosticEventWalkMarker('CODEVENT_CHECK|group-rows-get|before|chart=' + traceChart + '|group=' + traceGroup);\n"
            "\t\t\t\tvar groupRows:Dynamic = group[1];\n"
            "\t\t\t\tdiagnosticEventWalkMarker('CODEVENT_CHECK|group-rows-get|after|chart=' + traceChart + '|group=' + traceGroup);\n"
            "\t\t\t\tdiagnosticEventWalkMarker('CODEVENT_CHECK|group-rows|before|chart=' + traceChart + '|group=' + traceGroup);\n"
            "\t\t\t\tvar groupRowsAreArray = Std.isOfType(groupRows, Array);\n"
            "\t\t\t\tdiagnosticEventWalkMarker('CODEVENT_CHECK|group-rows|after|chart=' + traceChart + '|group=' + traceGroup + '|array=' + groupRowsAreArray);\n"
            "\t\t\t\tif (!groupRowsAreArray) continue;",
        ),
        (
            "for (row in (cast group[1]:Array<Dynamic>)) {",
            "var traceRowIndex = 0;\n\t\t\t\tfor (row in (cast groupRows:Array<Dynamic>)) {\n"
            "\t\t\t\t\tvar traceRow = traceRowIndex++;",
        ),
        (
            "if (!Std.isOfType(row, Array)) continue;",
            "diagnosticEventWalkMarker('CODEVENT_CHECK|row|before|chart=' + traceChart + '|group=' + traceGroup + '|row=' + traceRow);\n"
            "\t\t\t\t\tvar rowIsArray = Std.isOfType(row, Array);\n"
            "\t\t\t\t\tdiagnosticEventWalkMarker('CODEVENT_CHECK|row|after|chart=' + traceChart + '|group=' + traceGroup + '|row=' + traceRow + '|array=' + rowIsArray);\n"
            "\t\t\t\t\tif (!rowIsArray) continue;",
        ),
    )
    for old, new in replacements:
        if method.count(old) != 1:
            raise ValueError(f"expected one diagnostic insertion point: {old!r}")
        method = method.replace(old, new, 1)
    return method


METHODS = (
    "static function importPathKey",
    "static function normalizedImportFileName",
    "static function isImportFile",
    "static function validImportPath",
    "static function validModuleName",
    "static function existingImportChild",
    "static function findImportFile",
    "static function findImportAudio",
    "static function findImportVocalStems",
    "static function readImportJson",
    "static function convertImportDialogue",
    "static function importCutsceneScript",
    "static function importCutsceneBool",
    "static function getImportDifficultyNames",
    "static function findImportChart",
    "static function isImportChartSidecar",
    "static function collectAssetCharts",
    "static function chartFieldString",
    "static function chartFieldBool",
    "static function chartFieldInt",
    "static function findNamedDirectory",
    "static function findChildDirectory",
    "static function importSongFolderName",
    "static function readSongChart",
    "static function prepareSongNoteDefinitions",
    "static function collectSongNoteDefinitions",
    "static function appendCodenameDiagnostic",
    "static function appendCodenameDiagnostics",
    "static function discoverCodenameSongImports",
    "static function appendCodenameRootScriptDiagnostics",
    "static function collectCodenameScriptDiagnostics",
    "static function discoverCodenameSongsFromBase",
    "static function findCodenameDefinitionXml",
    "static function codenameAuthoredEventNames",
    "static function safeSortedDirectoryListing",
    "static public function processInfo",
    "static public function getInfoValue",
    "static public function getInfoBool",
    "static public function getInfoInt",
    "static function inferPsychStageForImport",
    "static function normalizeImportedCategory",
    "static function songImportFromRoots",
    "static function applyKadeSourceStageCompatibility",
    "static function applyKadeSourceCharacterCompatibility",
    "static function prepareKadeSourceCharacter",
    "static function generateKadeCharacterHScript",
    "static function nativeCharacterComplete",
    "static function placedActorPoint",
    "static function injectAfterActorPlacement",
    "static function findLegacyMusicAudio",
    "static function songImportFromAssetFolders",
    "static function appendAssetSongImports",
    "static function importedChartFileName",
    "static function findVSliceFile",
    "static function findVSliceVideo",
    "static function findVSliceFreeplayIcon",
    "static function findVSliceVoices",
    "static function findVSliceNoteStyle",
    "static function appendVSliceDiagnostic",
    "static function appendVSliceDiagnostics",
    "static function importVSliceNoteStyleConversion",
    "static function vSliceDefinitionFolders",
    "static function vSliceDefinitionStem",
    "static function findVSliceDefinition",
    "static function readVSliceDefinition",
    "static function appendVSliceFolderAssetDiagnostics",
    "static function appendVSliceScriptDiagnostics",
    "static function appendUniqueScriptDiagnostic",
    "static function collectVSliceScriptDiagnostics",
    "static function vSliceNativeCharacterName",
    "static function codenameConvertedCharacterName",
    "static function codenameNativeCharacterName",
    "static function vSliceNativeCharacterReference",
    "static function findVSliceSongPairs",
    "static function safeVSliceVariationSuffix",
    "static function findVSliceVariationFile",
    "static function findVSliceInstrumental",
    "static function normalizeVSliceVariationDifficulty",
    "static function vSliceStemMatchesReference",
    "static function selectVSliceVocalStems",
    "static function removeVSliceDiagnosticCode",
    "static function discoverVSliceSongImports",
    "static function discoverLegacySongImportsFromRoot",
    "static function ensureDirectory",
    "static function vSliceMappingDestination",
    "static function mergeVSliceMapping",
    "static function chooseVSliceRegistry",
    "static function registryHasVSliceKey",
    "static function mergeVSliceRegistryEntry",
    "static function hasMaterializedFile",
    "static function hasExistingSongInstrumental",
    "static public function validateSongImport",
    "static function songCandidateChartCount",
    "static function songCandidateCompleteness",
    "static function compareSongCandidates",
    "static function songCandidateOrigin",
    "static function selectSongCandidates",
)

DEP_METHODS = (
    "static function chartBelongsToCodename",
    "static function chartBelongsToPsych",
    "static function psychSourceStageForChart",
    "static function psychStageImplementationFound",
    "static function codenameDefinitionCandidateFound",
    "static function normalized",
    "static function pathKey",
    "static function pathWithin",
    "static function dependencyRootsForChart",
    "static function descriptorScopes",
    "static function exists",
    "static function file",
    "static function caseInsensitiveFile",
    "static function caseInsensitivePath",
    "static function directory",
    "static function uniquePush",
    "static function uniquePushKeyed",
    "static function field",
    "static function readChart",
    "static function addError",
    "static function registryValue",
    "static function registryText",
    "static function canonicalLegacyCharacter",
    "static function characterRegistryVisualFound",
    "static function dependencyRootsWithDestination",
    "static function destinationBuiltinDependency",
    "static function legacyCharacterAtlas",
    "static function appendLegacyAtlasCandidates",
    "static function appendLegacyAtlasDiagnostics",
    "static function chartPayload",
    "static function rawChartValue",
    "static function chartSongIdentity",
    "static function visualDependencyKind",
    "static function visualDependencyFound",
    "static function addVisualChartCandidate",
    "static function collectSiblingVisualCharts",
    "static function addSongDiagnostic",
    "static function resolveVisualChartFallback",
    "static function dependency(result",
    "static function characterImplementationFound",
    "static function legacyCharacterAtlasNeeded",
    "static function charCandidates",
    "static function stageCandidates",
    "static function uiCandidates",
    "static function cutsceneCandidates",
    "static function layoutCandidates",
    "static function extractQuotedAfter",
    "static function extractQuotedAfterAll",
    "static function scriptCandidatesForToken",
    "static function inspectScript",
    "static function inspectImplementationScripts",
    "static function inspectImplementationHxcs",
    "static function inspectJsonValue",
    "static function inspectImplementationJsons",
    "static function psychCompanionEvents",
    "static function inspectPsychLuaScripts",
    "static function chartBelongsToVSlice",
    "static function vSliceDefinitionCandidateFound",
    "static function inspectChart",
)


COUNTS_ONLY_ACCUMULATOR = r'''typedef DiagnosticCompactCandidate = {
  var name:String;
  var root:String;
  var engine:String;
  var score:Int;
  var rootKey:String;
  var stableRoot:String;
  var origin:String;
  var diagnostics:Array<String>;
};

/** Compact duplicate selection used only by --counts-only.  Its ordering is
 * the same score/root/stable-spelling order as ModuleFunctions' batch selector,
 * but it never retains a SongImport or parsed chart tree. */
class DiagnosticCandidateAccumulator {
  public var candidateCount(default, null):Int = 0;
  var bestByName:Map<String, DiagnosticCompactCandidate> = new Map<String, DiagnosticCompactCandidate>();

  public function new() {}

  public function add(name:String, root:String, engine:String, score:Int, rootKey:String,
      stableRoot:String, diagnostics:Array<String>, origin:String):Void {
    candidateCount++;
    var key = StringTools.trim(name).toLowerCase();
    var physicalOrigin = origin == null || StringTools.trim(origin) == '' ? rootKey : origin;
    key += '|' + physicalOrigin;
    var candidate:DiagnosticCompactCandidate = {
      name:name, root:root, engine:engine, score:score, rootKey:rootKey,
      stableRoot:stableRoot, origin:physicalOrigin,
      diagnostics:diagnostics == null ? [] : diagnostics.copy()
    };
    var current = bestByName.get(key);
    if (current == null || compare(candidate, current) < 0)
      bestByName.set(key, candidate);
  }

  public function uniqueCount():Int {
    var count = 0;
    for (_ in bestByName.keys()) count++;
    return count;
  }

  public function winners():Iterator<DiagnosticCompactCandidate>
    return bestByName.iterator();

  static function compare(a:DiagnosticCompactCandidate, b:DiagnosticCompactCandidate):Int {
    if (a.score != b.score)
      return a.score > b.score ? -1 : 1;
    if (a.rootKey < b.rootKey)
      return -1;
    if (a.rootKey > b.rootKey)
      return 1;
    if (a.stableRoot < b.stableRoot)
      return -1;
    if (a.stableRoot > b.stableRoot)
      return 1;
    return 0;
  }
}
'''


MAIN = r'''class Main {
  static function main() {
    if (Sys.args().indexOf("--codename-event-walk") >= 0) {
      runCodenameEventWalk(Sys.args()[0]);
      return;
    }
    var roots = ImportRootScanner.scan(Sys.args()[0], ImportEngine.AUTO);
    var verbose = Sys.args().length < 2 || (Sys.args()[1] != "--summary" && Sys.args()[1] != "--counts-only");
    var quiet = Sys.args().length >= 2 && Sys.args()[1] == "--counts-only";
    trace("ROOTS=" + roots.length);
    // Full importer objects are needed for readable summaries and for the
    // existing duplicate report.  Counts-only keeps compact winners instead.
    var candidates:Array<SongImportCandidate> = [];
    var compactCandidates = new DiagnosticCandidateAccumulator();
    var descriptors:Array<ImportRootScanner.ImportRoot> = roots;
    var dependencyResult:ImportScanResult = {source:Sys.args()[0], missingDependencies:0,
      scriptsFound:0, errors:[]};
    var diagnosticCounts:Map<String, Int> = new Map<String, Int>();
    var diagnosticEngineCounts:Map<String, Int> = new Map<String, Int>();
    var selectedDiagnosticCounts:Map<String, Int> = new Map<String, Int>();
    var selectedDiagnosticEngineCounts:Map<String, Int> = new Map<String, Int>();
    var missingCounts:Map<String, Int> = new Map<String, Int>();
    var engineUniqueCounts:Map<String, Int> = new Map<String, Int>();
    for (root in roots) {
      trace("ROOT|" + root.engine + "|" + root.root + "|content=" + root.contentRoot
        + "|data=" + root.data + "|audio=" + root.audio + "|evidence=" + root.evidence.join(";"));
      var found = ModuleFunctions.discoverRoot(root);
      trace("ROOT_CANDIDATES|" + root.engine + "|" + found.length);
      var songIndex = 0;
      while (songIndex < found.length) {
        var song = found[songIndex];
        if (quiet)
          found[songIndex] = cast null;
        songIndex++;
        var chartCount = song.convertedCharts != null ? song.convertedCharts.length
          : (song.diffFiles == null ? 0 : song.diffFiles.length);
        var diagnosticCount = song.diagnostics == null ? 0 : song.diagnostics.length;
        if (!quiet)
          trace("CANDIDATE|" + root.engine + "|" + song.name + "|charts=" + chartCount
            + "|inst=" + (song.inst == null ? "" : song.inst)
            + "|voices=" + (song.voices == null ? "" : song.voices)
            + "|diagnostics=" + diagnosticCount);
        if (verbose && song.diagnostics != null)
          for (diagnostic in song.diagnostics)
            trace("DIAGNOSTIC|" + root.engine + "|" + song.name + "|" + diagnostic);
        var scanSong:ImportScanSong = {name:song.name, dependencies:[], missing:[]};
        var convertedPeers:Array<ImportVisualChart> = [];
        if (song.convertedCharts != null)
          for (converted in song.convertedCharts)
            if (converted != null && converted.chart != null)
              convertedPeers.push({path:converted.source, chart:converted.chart});
        if (song.convertedCharts != null)
          for (converted in song.convertedCharts)
            DependencyInspector.inspectSong(dependencyResult, scanSong, converted.source,
              descriptors, converted.chart, convertedPeers, song);
        else if (song.diffFiles != null)
          for (chartPath in song.diffFiles)
            DependencyInspector.inspectSong(dependencyResult, scanSong, chartPath,
              descriptors, null);
        for (item in scanSong.missing) {
          var missingKey = item.kind + "|" + item.reference;
          missingCounts.set(missingKey, (missingCounts.exists(missingKey) ? missingCounts.get(missingKey) : 0) + 1);
          if (verbose)
            trace("MISSING_DETAIL|" + root.engine + "|" + song.name + "|" + item.kind + "|"
              + item.reference + "|origin=" + item.origin + "|searched=" + item.searched.join(";"));
        }
        if (song.diagnostics != null)
          for (diagnostic in song.diagnostics) {
            var end = diagnostic.indexOf("]");
            var code = end > 1 && diagnostic.charAt(0) == "[" ? diagnostic.substr(1, end - 1) : "unclassified";
            diagnosticCounts.set(code, (diagnosticCounts.exists(code) ? diagnosticCounts.get(code) : 0) + 1);
            var engineKey = root.engine + "|" + code;
            diagnosticEngineCounts.set(engineKey,
              (diagnosticEngineCounts.exists(engineKey) ? diagnosticEngineCounts.get(engineKey) : 0) + 1);
          }
        if (quiet) {
          var stableRoot = root.root == null ? ''
            : haxe.io.Path.normalize(StringTools.replace(root.root, '\\', '/'));
          compactCandidates.add(song.name, root.root, root.engine,
            ModuleFunctions.diagnosticCompleteness(song),
            ModuleFunctions.diagnosticRootKey(root.root), stableRoot, song.diagnostics,
            ModuleFunctions.diagnosticOrigin(song, root.root));
          // These caches are parse memoization only. Clearing them after a
          // complete song keeps counts-only bounded by one song's dependency
          // graph instead of the entire mounted corpus.
          DependencyInspector.clearChartCache();
          convertedPeers.resize(0);
          scanSong = cast null;
          song = cast null;
        } else
          candidates.push({song:song, root:root.root, engine:root.engine});
      }
      if (quiet)
        found.resize(0);
    }
    var unique = 0;
    var duplicate = 0;
    var selectedRecordCount = 0;
    if (quiet) {
      unique = compactCandidates.uniqueCount();
      selectedRecordCount = compactCandidates.candidateCount;
      duplicate = selectedRecordCount - unique;
      for (candidate in compactCandidates.winners()) {
        engineUniqueCounts.set(candidate.engine,
          (engineUniqueCounts.exists(candidate.engine) ? engineUniqueCounts.get(candidate.engine) : 0) + 1);
        for (diagnostic in candidate.diagnostics) {
          var end = diagnostic.indexOf("]");
          var code = end > 1 && diagnostic.charAt(0) == "[" ? diagnostic.substr(1, end - 1) : "unclassified";
          selectedDiagnosticCounts.set(code,
            (selectedDiagnosticCounts.exists(code) ? selectedDiagnosticCounts.get(code) : 0) + 1);
          var engineKey = candidate.engine + "|" + code;
          selectedDiagnosticEngineCounts.set(engineKey,
            (selectedDiagnosticEngineCounts.exists(engineKey) ? selectedDiagnosticEngineCounts.get(engineKey) : 0) + 1);
        }
      }
    } else {
      var selected = ModuleFunctions.choose(candidates);
      selectedRecordCount = selected.length;
      for (candidate in selected) {
        if (candidate.song.sourceDuplicate) {
          duplicate++;
          if (!quiet)
          trace("SELECTED_DUPLICATE|" + candidate.song.name + "|source=" + candidate.root
            + "|winner=" + candidate.song.sourceDuplicateOf);
        } else {
          unique++;
          engineUniqueCounts.set(candidate.engine,
            (engineUniqueCounts.exists(candidate.engine) ? engineUniqueCounts.get(candidate.engine) : 0) + 1);
          if (candidate.song.diagnostics != null)
            for (diagnostic in candidate.song.diagnostics) {
              var end = diagnostic.indexOf("]");
              var code = end > 1 && diagnostic.charAt(0) == "[" ? diagnostic.substr(1, end - 1) : "unclassified";
              selectedDiagnosticCounts.set(code,
                (selectedDiagnosticCounts.exists(code) ? selectedDiagnosticCounts.get(code) : 0) + 1);
              var engineKey = candidate.engine + "|" + code;
              selectedDiagnosticEngineCounts.set(engineKey,
                (selectedDiagnosticEngineCounts.exists(engineKey) ? selectedDiagnosticEngineCounts.get(engineKey) : 0) + 1);
            }
          if (!quiet)
          trace("SELECTED_UNIQUE|" + candidate.song.name + "|engine=" + candidate.engine
            + "|source=" + candidate.root);
        }
      }
    }
    trace("CANDIDATES=" + (quiet ? compactCandidates.candidateCount : candidates.length)
      + "|SELECTED_RECORDS=" + selectedRecordCount
      + "|UNIQUE=" + unique + "|DUPLICATES=" + duplicate);
    trace("MISSING_DEPENDENCIES=" + dependencyResult.missingDependencies);
    trace("INSPECTED_SCRIPTS=" + dependencyResult.scriptsFound);
    for (key in missingCounts.keys())
      trace("MISSING|" + key + "|count=" + missingCounts.get(key));
    for (key in diagnosticCounts.keys())
      trace("DIAGNOSTIC_COUNT|" + key + "|count=" + diagnosticCounts.get(key));
    for (key in diagnosticEngineCounts.keys())
      trace("DIAGNOSTIC_ENGINE_COUNT|" + key + "|count=" + diagnosticEngineCounts.get(key));
    for (key in selectedDiagnosticCounts.keys())
      trace("SELECTED_DIAGNOSTIC_COUNT|" + key + "|count=" + selectedDiagnosticCounts.get(key));
    for (key in selectedDiagnosticEngineCounts.keys())
      trace("SELECTED_DIAGNOSTIC_ENGINE_COUNT|" + key + "|count=" + selectedDiagnosticEngineCounts.get(key));
    for (key in engineUniqueCounts.keys())
      trace("ENGINE_UNIQUE|" + key + "|count=" + engineUniqueCounts.get(key));
  }

  static function runCodenameEventWalk(source:String):Void {
    var finished = new sys.thread.Lock();
    var workerError:String = null;
    var songCount = 0;
    sys.thread.Thread.create(function():Void {
      try {
        ModuleFunctions.diagnosticEventWalkMarker("CODEVENT_SCAN_START|source=" + source);
        var roots = ImportRootScanner.scan(source, ImportEngine.AUTO);
        ModuleFunctions.diagnosticEventWalkMarker("CODEVENT_ROOTS|count=" + roots.length);
        for (root in roots) {
          ModuleFunctions.diagnosticEventWalkMarker("CODEVENT_ROOT|engine=" + root.engine + "|root=" + root.root);
          if (root.engine != ImportEngine.CODENAME) continue;
          var songs = ModuleFunctions.discoverRoot(root);
          for (song in songs) {
            var chartCount = song.convertedCharts == null ? 0 : song.convertedCharts.length;
            ModuleFunctions.diagnosticEventWalkMarker("CODEVENT_SONG_START|song=" + song.name + "|charts=" + chartCount);
            var names = ModuleFunctions.diagnosticCodenameAuthoredEventNames(song);
            ModuleFunctions.diagnosticEventWalkMarker("CODEVENT_SONG_DONE|song=" + song.name + "|eventNames=" + names.length);
            songCount++;
          }
        }
      } catch (error:Dynamic) {
        workerError = Std.string(error);
        ModuleFunctions.diagnosticEventWalkMarker("CODEVENT_WORKER_ERROR|" + workerError);
      }
      finished.release();
    });
    finished.wait();
    if (workerError != null) throw workerError;
    ModuleFunctions.diagnosticEventWalkMarker("CODEVENT_SCAN_DONE|songs=" + songCount);
  }
}
'''


def build_fixture(trace_codename_event_walk: bool = False) -> str:
    source = (ROOT / "tools/tests/test_mixed_auto_import.py").read_text()
    module = (ROOT / "source/ModuleFunctions.hx").read_text()
    start = source.index("fixture = f'''", source.index("def test_auto_discovers"))
    end = source.index("'''", start + len("fixture = f'''"))
    body = source[start + len("fixture = f'''") : end]
    extracted_methods = []
    for marker in METHODS:
        method = extract_method(module, marker)
        if trace_codename_event_walk and marker == "static function codenameAuthoredEventNames":
            method = instrument_codename_event_walk(method)
        extracted_methods.append(method)
    methods = "\n".join(extracted_methods)
    fixture = eval("f'''" + body + "'''", {"methods": methods})
    fixture = fixture.replace(
        """return root.engine == ImportEngine.V_SLICE
      ? discoverVSliceSongImports(root)
      : discoverLegacySongImportsFromRoot(root);""",
        """return root.engine == ImportEngine.V_SLICE
      ? discoverVSliceSongImports(root)
      : (root.engine == ImportEngine.CODENAME
        ? discoverCodenameSongImports(root)
        : discoverLegacySongImportsFromRoot(root));""",
        1,
    )
    # Keep the isolated discovery fixture's engine-neutral shape in sync with
    # ModuleFunctions' retained V-Slice note-style conversion metadata.  The
    # scanner is read-only, but it must compile the same field surface as the
    # native importer before it can produce authoritative HXC counts.
    if "typedef VSliceNoteStyleImport" not in fixture:
        fixture = fixture.replace(
            "typedef VSliceStageImport = {\n  var reference:String; var source:String; var conversion:VSliceImporter.VSliceStageConversion;\n};",
            "typedef VSliceStageImport = {\n  var reference:String; var source:String; var conversion:VSliceImporter.VSliceStageConversion;\n};\n"
            "typedef VSliceNoteStyleImport = {\n  var reference:String; var source:String; var conversion:VSliceImporter.VSliceNoteStyleConversion;\n};",
            1,
        )
    if "convertedNoteStyle" not in fixture:
        fixture = fixture.replace(
            "@:optional var convertedStage:VSliceStageImport;",
            "@:optional var convertedStage:VSliceStageImport; @:optional var convertedNoteStyle:VSliceNoteStyleImport;"
            " @:optional var convertedNoteStyles:Array<VSliceNoteStyleImport>;",
            1,
        )
    if "@:optional var freeplayIconSource:String;" not in fixture:
        fixture = fixture.replace(
            "@:optional var convertedNoteStyles:Array<VSliceNoteStyleImport>;",
            "@:optional var convertedNoteStyles:Array<VSliceNoteStyleImport>;"
            " @:optional var freeplayIconSource:String;",
            1,
        )
    fixture = fixture.replace(
        '''class CoolUtil {
  public static function parseJson(raw:String):Dynamic return Json.parse(raw);
  public static function stringifyJson(value:Dynamic):String return Json.stringify(value);
}''',
        '''class CoolUtil {
  public static function parseJson(raw:String):Dynamic {
    var end = raw.length;
    while (end > 0) {
      var code = raw.charCodeAt(end - 1);
      if (code == 0 || code == 9 || code == 10 || code == 13 || code == 32) end--;
      else break;
    }
    return Json.parse(end == raw.length ? raw : raw.substr(0, end));
  }
  public static function stringifyJson(value:Dynamic):String return Json.stringify(value);
}''',
        1,
    )
    fixture = fixture.replace(
        "@:optional var generatedModchart:String;",
        "@:optional var generatedModchart:String;"
        " @:optional var sourceDuplicate:Bool; @:optional var sourceDuplicateOf:String;",
        1,
    )
    # ModuleFunctions keeps provenance beside each selected song source.  The
    # diagnostic only needs the fields to type-check the same discovery methods;
    # it never writes or consumes the provenance manifest.
    fixture = fixture.replace(
        "typedef SongImportSource = { var song:String; var data:String; var destination:String; };",
        "typedef SongImportSource = { var song:String; var data:String; var destination:String;"
        " @:optional var sourceRoot:String; @:optional var engine:String; };",
        1,
    )
    fixture = fixture[: fixture.index("class Main {")]
    stage_parser = (ROOT / "source/PsychStageInference.hx").read_text().replace("package;", "", 1)
    stage_parser = stage_parser.replace("import haxe.io.Path;\n", "")
    stage_parser = stage_parser.replace("#if sys\nimport sys.FileSystem;\nimport sys.io.File;\n#end\n", "")
    stage_parser = stage_parser.replace("using StringTools;\n", "")
    fixture += "\n// PSYCH_STAGE_INFERENCE_FIXTURE\n" + stage_parser.strip() + "\n"
    workflow = (ROOT / "source/ImportWorkflow.hx").read_text()
    dep_methods = "\n".join(extract_method(workflow, marker) for marker in DEP_METHODS)
    dep_methods = dep_methods.replace("Array<ImportRoot>", "Array<ImportRootScanner.ImportRoot>")
    dep_methods = dep_methods.replace(
        "LegacyCharacterAtlasResult", "LegacyCharacterAtlasImporter.LegacyCharacterAtlasResult"
    )
    dep_methods = dep_methods.replace(
        "PsychCompiledStageSource", "PsychSourceStageCompat.PsychCompiledStageSource"
    )
    fixture += '''typedef ImportScanDependency = {
  var kind:String; var reference:String; var found:Bool; var searched:Array<String>; var origin:String;
};
typedef ImportScanSong = {
  var name:String; var dependencies:Array<ImportScanDependency>; var missing:Array<ImportScanDependency>;
  @:optional var diagnostics:Array<String>;
};
typedef ImportScanResult = {
  var source:String; var missingDependencies:Int; var scriptsFound:Int; var errors:Array<String>;
  @:optional var importType:String;
};
typedef ImportVisualChart = {
  var path:String; var chart:Dynamic;
};
class DependencyInspector {
  static inline var MAX_SCRIPT_BYTES:Int = 4 * 1024 * 1024;
  // The mounted corpus is on a filesystem where repeated case-insensitive
  // directory walks are expensive. Keep the diagnostic harness on the same
  // per-scan resolution cache as ImportWorkflow so every difficulty does not
  // re-stat the same atlas/registry paths.
  static var caseInsensitivePathCache:Map<String, String> = new Map<String, String>();
  static var caseInsensitiveFileCache:Map<String, String> = new Map<String, String>();
  static var registryValueCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  static var registryValueCacheKnown:Map<String, Bool> = new Map<String, Bool>();
  static var chartCache:Map<String, Dynamic> = new Map<String, Dynamic>();
  public static function clearChartCache():Void
    chartCache = new Map<String, Dynamic>();
  static function resolutionCacheKey(value:String):String
    return StringTools.replace(value == null ? '' : value, '\\\\', '/');
  static var visualFallbackFields:Array<String> = [
    'player1', 'player2', 'gf', 'stage', 'uiType', 'cutsceneType',
    'forceLayout', 'uiLayoutType'
  ];
  public static function inspectSong(result:ImportScanResult, song:ImportScanSong, chartPath:String,
      descriptors:Array<ImportRootScanner.ImportRoot>, ?chartOverride:Dynamic,
      ?convertedPeers:Array<ImportVisualChart>, ?plannedSong:Dynamic):Void
    inspectChart(result, song, chartPath, descriptors, chartOverride, convertedPeers, plannedSong);
'''
    fixture += dep_methods
    fixture += "}\n"
    typedef = '''typedef SongImportCandidate = {
  var song:SongImport; var root:String; var engine:String;
  @:optional var source:SongImportSource;
};
'''
    fixture = fixture.replace("class ModuleFunctions {", typedef + '''class ModuleFunctions {
  static function validateAndRecordSongImport(_rejections:SongImportRejectionCollector,
      songData:SongImport, _sourceRoot:String, _sourcePath:String, _engine:String):Bool
    return validateSongImport(songData) == null;
  public static function choose(candidates:Array<SongImportCandidate>):Array<SongImportCandidate>
    return selectSongCandidates(candidates);
  public static function diagnosticCompleteness(song:SongImport):Int
    return songCandidateCompleteness(song);
  public static function diagnosticRootKey(root:String):String
    return importPathKey(root);
  public static function diagnosticOrigin(song:SongImport, root:String):String
    return songCandidateOrigin({song:song, root:root,
      engine:song == null ? '' : song.engine,
      source:song == null ? null : song.importSourceInfo});
  public static function diagnosticCodenameAuthoredEventNames(song:SongImport):Array<String>
    return codenameAuthoredEventNames(song);
  public static function diagnosticEventWalkMarker(message:String):Void {
    Sys.println(message);
    Sys.stdout().flush();
  }
''', 1)
    return fixture + COUNTS_ONLY_ACCUMULATOR + MAIN


def main() -> int:
    args = parse_arguments(sys.argv[1:])
    private_diagnostic = args.asan or args.recycle_diagnostics
    source = args.source
    summary = args.summary or args.counts_only
    counts_only = args.counts_only
    if not source.is_dir():
        raise SystemExit(f"donor is not mounted: {source}")
    project_tmp = ROOT / "tmp"
    project_tmp.mkdir(parents=True, exist_ok=True)
    if private_diagnostic:
        # The private compile workspace is kept below project tmp so Build.xml,
        # Options.txt, the private hxcpp overlay, and generated C++ remain
        # reviewable after an instrumented failure.
        prefix = "disappointing-auto-scan-asan-" if args.asan else "disappointing-auto-scan-recycle-"
        folder = tempfile.mkdtemp(prefix=prefix, dir=str(project_tmp))
        temp_context = nullcontext(folder)
    else:
        temp_context = tempfile.TemporaryDirectory(
            prefix="disappointing-auto-scan-", dir=str(project_tmp)
        )
    with temp_context as folder:
        temp = Path(folder)
        install_import_io_dependencies(temp)
        (temp / "ImportEngine.hx").write_text((ROOT / "source/ImportEngine.hx").read_text())
        (temp / "ImportRootScanner.hx").write_text((ROOT / "source/ImportRootScanner.hx").read_text())
        (temp / "ImportDirectoryListing.hx").write_text(
            (ROOT / "source/ImportDirectoryListing.hx").read_text()
        )
        # The scan path can recover compiled legacy/Kade/FPS characters from
        # Sparrow atlases without touching the donor.  Keep the isolated
        # diagnostic fixture's source graph in sync with ImportWorkflow.
        (temp / "LegacyCharacterAtlasImporter.hx").write_text(
            (ROOT / "source/LegacyCharacterAtlasImporter.hx").read_text()
        )
        # VSliceImporter plans ASTC mappings through the shared portable
        # header/probe adapter. Keep the diagnostic harness's extracted source
        # graph identical to the native importer instead of stubbing that
        # dependency away.
        (temp / "VSliceAstcAdapter.hx").write_text((ROOT / "source" / "VSliceAstcAdapter.hx").read_text())
        # V-Slice note-kind conversion shares the engine-level note-type
        # aliases with PlayState. Include that helper in the isolated scanner
        # fixture so diagnostics exercise the same graph as the importer.
        (temp / "NoteTypeCompat.hx").write_text((ROOT / "source" / "NoteTypeCompat.hx").read_text())
        (temp / "VSliceImporter.hx").write_text((ROOT / "source/VSliceImporter.hx").read_text())
        # Use the real foreign-source analyzers.  Earlier versions stubbed these
        # classes because the tool only measured root/song discovery; that made
        # every HXC file look unsupported and inflated the diagnostic total even
        # though the in-game importer could generate a safe runtime adapter.
        for module in ("EngineBranding.hx", "EngineCompat.hx", "CompatScriptManifest.hx", "ImportSongOwnership.hx", "HxcEventSpriteDescriptor.hx", "HxcCompatRuntime.hx", "HxcDynamicMap.hx", "HxcDeferredValue.hx", "HxcMenuSpec.hx", "HxcPauseSpec.hx", "HxcNoteTextSpec.hx", "HxcStoryMenuSpec.hx", "LuaCompat.hx", "HxcCutsceneTimeline.hx", "HxcCompat.hx", "HxcScriptIdentity.hx", "HxcScriptDiscovery.hx", "PsychScriptDiscovery.hx", "PsychSourceStageCompat.hx", "KadeStageSource.hx", "NightmareVisionDifficultyCompat.hx", "NightmareVisionChartCompat.hx", "NightmareVisionScriptDiscovery.hx", "CodenameImporter.hx", "CodenameCharacterAtlas.hx", "CodenameEventMetadata.hx", "CodenameNoteMetadata.hx", "CodenameEventPack.hx", "CodenameStagePlacement.hx", "CodenameStrumlineLayout.hx", "CodenameScriptDiscovery.hx", "CodenameInstallationAssetOverlay.hx", "CodenameScriptPlan.hx", "CodenameSongMetadata.hx"):
            (temp / module).write_text((ROOT / "source" / module).read_text())
        # This count-only fixture compiles the real analyzer without the game
        # runtime's hxvlc/Flixel graph. The imported video host is a separate
        # native lifecycle boundary and is never instantiated by this scan.
        (temp / "HxcOwnedVideoSprite.hx").write_text('''class HxcOwnedVideoSprite {
  public static function create(_state:Dynamic, _root:String, _x:Float, _y:Float):Dynamic return null;
  public static function pauseForState(_state:Dynamic):Void {}
  public static function resumeForState(_state:Dynamic):Void {}
  public static function destroyForState(_state:Dynamic):Void {}
}
''')
        # Neko's stdlib raises from ``FileSystem.isDirectory`` for a missing
        # path, while the Haxe interpreter (and the native importer) returns
        # false.  The real scanner intentionally probes many optional sibling
        # paths, so give this diagnostic's Neko backend the same safe probe
        # semantics without changing any engine source.  Replace only the
        # copied fixture graph; the game/runtime continues to use sys.FileSystem.
        (temp / "DiagnosticFileSystem.hx").write_text('''class DiagnosticFileSystem {
  public static function isDirectory(path:String):Bool {
    if (path == null || path == '') return false;
    try {
      // Neko's isDirectory throws for absent paths; exists() is the cheap
      // probe that matches the interpreter/native contract and avoids an
      // exception for every optional chart/asset candidate.
      if (!sys.FileSystem.exists(path)) return false;
      return sys.FileSystem.isDirectory(path);
    } catch (_:Dynamic) return false;
  }
}
''')
        for module_path in temp.glob("*.hx"):
            if module_path.name == "DiagnosticFileSystem.hx":
                continue
            module_path.write_text(rewrite_diagnostic_filesystem_calls(module_path.read_text()))
        (temp / "DifficultyManager.hx").write_text('''class DifficultyManager {}
''')
        fixture = build_fixture(trace_codename_event_walk=args.codename_event_walk)
        fixture = rewrite_diagnostic_filesystem_calls(fixture)
        (temp / "Main.hx").write_text(fixture)
        # LuaCompat validates translated scripts with hscript.Parser.  Keep the
        # diagnostic harness on the repository's pinned hscript version rather
        # than relying on a caller's global haxelib configuration; otherwise a
        # clean checkout fails before it can report any importer counts.
        #
        # The mounted graph is too large for Haxe's eval/interpreter backend.
        # Prefer a native hxcpp executable: Haxe emits C++ once, hxcpp links it
        # once, and the exact same Main fixture then performs the scan.  The
        # generated C++ tree, aliases, and all build scratch stay below project
        # ``tmp``.  Pass aliases relative to the C++ output directory so
        # hxcpp's XML build tool never parses checkout paths with spaces.
        total_deadline = time.monotonic() + 300.0
        cpp_target = temp / "cpp"
        cpp_target.mkdir()
        alias_root = cpp_target / "aliases"
        alias_root.mkdir()
        short_links = {
            name: Path("aliases") / name
            for name in ("src", "hscript", "haxe", "haxelib", "hxcpp", "neko")
        }
        link_targets = {
            "src": temp,
            "hscript": ROOT / ".haxelib/hscript/2,5,0",
            "haxe": ROOT / ".tools/haxe",
            "haxelib": ROOT / ".haxelib",
            "hxcpp": ROOT / ".haxelib/hxcpp" / HXCPP_PACKAGE_DIRECTORY,
            "neko": ROOT / ".tools/neko",
        }

        def remaining() -> float:
            return max(1.0, total_deadline - time.monotonic())

        def report(result: subprocess.CompletedProcess[str]) -> int:
            print(result.stdout, end="")
            print(result.stderr, end="")
            return result.returncode

        keep_private_workspace = False
        root_dir_fd: int | None = None
        try:
            for name, link in short_links.items():
                (cpp_target / link).symlink_to(link_targets[name], target_is_directory=True)

            absolute_haxe = alias_root / "haxe"
            absolute_neko = alias_root / "neko"
            native_env = asan_build_env(os.environ) if args.asan else os.environ.copy()
            native_env.update({
                "TMPDIR": str(project_tmp),
                "HAXEPATH": str(short_links["haxe"]),
                "NEKOPATH": str(short_links["neko"]),
                "HAXELIB_PATH": str(short_links["haxelib"]),
                # hxcpp's runner changes cwd before invoking neko and the
                # native compiler, so tool lookup paths must be absolute even
                # though paths passed to Haxe/hxcpp remain relative.
                "LD_LIBRARY_PATH": str(absolute_neko)
                + (os.pathsep + os.environ["LD_LIBRARY_PATH"]
                   if os.environ.get("LD_LIBRARY_PATH") else ""),
                "PATH": str(absolute_haxe) + os.pathsep
                + str(absolute_neko) + os.pathsep
                + os.environ.get("PATH", ""),
            })
            # Haxe can derive its standard library from the short HAXEPATH.
            # An explicit HAXE_STD_PATH symlink is counterproductive here: the
            # compiler treats the symlinked std directory as an ordinary
            # classpath on this portable toolchain and emits Std.hx's guard
            # error.  Do not inherit a caller-provided value either.
            native_env.pop("HAXE_STD_PATH", None)
            if args.recycle_diagnostics:
                # Match ordinary scanner GC scheduling; a caller's diagnostic
                # environment must not silently turn this into GC-debug/ASan.
                native_env.pop("HXCPP_GC_DEBUG_LEVEL", None)
                native_env.pop("ASAN_OPTIONS", None)
            runtime_env = (
                asan_runtime_env(os.environ, project_tmp)
                if args.asan else os.environ.copy()
            )
            if args.recycle_diagnostics:
                runtime_env.pop("ASAN_OPTIONS", None)
                runtime_env.pop("HXCPP_GC_DEBUG_LEVEL", None)
            runtime_env["TMPDIR"] = str(project_tmp)
            # The trace is a runtime switch, so a cached scanner binary can
            # be used without recompilation. Override an inherited value to
            # keep the default scanner quiet and deterministic.
            if args.trace_psych_discovery:
                runtime_env["DISAPPOINTINGPLUS_PSYCH_DISCOVERY_TRACE"] = "1"
            else:
                runtime_env.pop("DISAPPOINTINGPLUS_PSYCH_DISCOVERY_TRACE", None)

            short_haxe = short_links["haxe"] / "haxe"
            short_haxelib = short_links["haxe"] / "haxelib"
            short_neko = short_links["neko"] / "neko"
            native_available = (
                (cpp_target / short_haxe).is_file()
                and (cpp_target / short_haxelib).is_file()
                and shutil.which("g++") is not None
            )
            if private_diagnostic and not native_available:
                print("private diagnostic mode requires the native Haxe/hxcpp/g++ toolchain", file=sys.stderr)
                return 1
            if native_available:
                cache_key = native_scan_cache_key(
                    temp,
                    gc_debug_level_1=args.gc_debug_level_1,
                    asan=args.asan,
                    recycle_diagnostics=args.recycle_diagnostics,
                )
                cache_base = (
                    project_tmp / "auto-import-diagnostic-asan-cache"
                    if args.asan else project_tmp / "auto-import-diagnostic-recycle-cache"
                    if args.recycle_diagnostics else project_tmp / "auto-import-diagnostic-cache"
                )
                cache_root = cache_base / cache_key
                cached_executable = cache_root / "Main"
                diagnostic_run_dir: Path | None = None
                if cached_executable.is_file():
                    command = [str(cached_executable), str(source)]
                    if summary:
                        command.append("--counts-only" if counts_only else "--summary")
                    if args.codename_event_walk:
                        command.append("--codename-event-walk")
                    native_run, timed_out = run_bounded_native_scan(
                        command, ROOT, runtime_env, args.scan_timeout_seconds
                    )
                    if private_diagnostic:
                        diagnostic_run_dir = cache_root / f"run-{os.getpid()}-{uuid.uuid4().hex}"
                        save_process_output(native_run, diagnostic_run_dir, "scan")
                        (diagnostic_run_dir / "run.json").write_text(json.dumps({
                            "command": command,
                            "cwd": str(ROOT),
                            "mode": "asan" if args.asan else "recycle",
                            "ASAN_OPTIONS": runtime_env.get("ASAN_OPTIONS"),
                            "returncode": native_run.returncode,
                            "timed_out": timed_out,
                            "scan_timeout_seconds": args.scan_timeout_seconds,
                            "cached_binary": True,
                        }, indent=2) + "\n")
                    return report(native_run)

                build_artifacts: Path | None = None
                preflight_command: list[str] | None = None
                if private_diagnostic:
                    keep_private_workspace = True
                    cache_root.mkdir(parents=True, exist_ok=True)
                    build_artifacts = cache_root / f"build-{os.getpid()}-{uuid.uuid4().hex}"
                    build_artifacts.mkdir()
                    private_haxelib = temp / "private-haxelib-overlay"
                    prepare_private_haxelib_overlay(ROOT / ".haxelib", private_haxelib)
                    # Replace only this fixture's aliases. The working tree's
                    # .haxelib remains untouched, and both compile and hxcpp
                    # package resolution use the private copied hxcpp tree.
                    for name, target in (
                        ("haxelib", private_haxelib),
                        ("hxcpp", private_haxelib / "hxcpp" / HXCPP_PACKAGE_DIRECTORY),
                    ):
                        link_path = cpp_target / short_links[name]
                        link_path.unlink()
                        link_path.symlink_to(target.resolve(), target_is_directory=True)
                    compiler = Path(shutil.which("g++") or "g++").resolve()
                    compiler_log: Path | None = None
                    if args.asan:
                        compiler_log = build_artifacts / "asan-cxx-arguments"
                        wrapper = alias_root / "asan-cxx"
                        wrapper.write_text(asan_cxx_wrapper_text(compiler, compiler_log))
                        wrapper.chmod(0o755)
                        root_dir_fd = os.open(ROOT, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
                        native_env["CXX"] = asan_cxx_command(wrapper, root_dir_fd)
                    else:
                        native_env["CXX"] = str(compiler)
                    native_env["HAXELIB_PATH"] = str(private_haxelib.resolve())

                    # The checkout's ancestor .haxelib directory takes
                    # precedence over HAXELIB_PATH unless haxelib is explicitly
                    # told to use its global repository. Verify the exact
                    # command environment before Haxe/hxcpp compiles anything.
                    preflight_command = haxelib_path_command(
                        short_haxelib, private_repo=True
                    )
                    preflight = subprocess.run(
                        preflight_command,
                        cwd=cpp_target,
                        env=native_env,
                        capture_output=True,
                        text=True,
                        timeout=remaining(),
                    )
                    save_process_output(preflight, build_artifacts, "haxelib-preflight")
                    (build_artifacts / "haxelib-preflight.json").write_text(json.dumps({
                        "command": preflight_command,
                        "cwd": str(cpp_target),
                        "HAXELIB_PATH": native_env["HAXELIB_PATH"],
                        "returncode": preflight.returncode,
                        "resolved_private": haxelib_paths_are_private(
                            preflight.stdout, private_haxelib
                        ),
                    }, indent=2) + "\n")
                    if preflight.returncode != 0 or not haxelib_paths_are_private(
                        preflight.stdout, private_haxelib
                    ):
                        print(
                            "refusing private compilation: haxelib path hxcpp resolved outside the private overlay",
                            file=sys.stderr,
                        )
                        return 1

                generate_command = [
                    str(short_haxe),
                    "-cp", str(short_links["hscript"]),
                    "-cp", str(short_links["src"]),
                    "-main", "Main",
                    "-cpp", ".",
                    "-D", "no-compilation",
                ]
                generated = subprocess.run(
                    generate_command,
                    # Keep generated files and compiler cwd at the same local
                    # output directory. Relative aliases keep hxcpp's inputs
                    # free of this checkout's spaces.
                    cwd=cpp_target,
                    env=native_env,
                    capture_output=True,
                    text=True,
                    timeout=remaining(),
                )
                if build_artifacts is not None:
                    save_process_output(generated, build_artifacts, "haxe-generate")
                    save_build_inputs(cpp_target, build_artifacts)
                if generated.returncode != 0:
                    return report(generated)

                build_command = hxcpp_build_command(
                    short_haxelib,
                    native_scan_build_args(
                        args.gc_debug_level_1, asan=args.asan,
                        recycle_diagnostics=args.recycle_diagnostics,
                    ),
                    private_repo=private_diagnostic,
                )
                native_build = subprocess.run(
                    build_command,
                    cwd=cpp_target,
                    env=native_env,
                    capture_output=True,
                    text=True,
                    timeout=remaining(),
                )
                if build_artifacts is not None:
                    save_process_output(native_build, build_artifacts, "hxcpp-build")
                    save_build_inputs(cpp_target, build_artifacts)
                    metadata = {
                        "cache_key": cache_key,
                        "fixture_workspace": str(temp),
                        "private_haxelib": str(private_haxelib),
                        "private_hxcpp_version": HXCPP_PACKAGE_VERSION,
                        "private_hxcpp_directory": HXCPP_PACKAGE_DIRECTORY,
                        "original_hxcpp_capture_sha256": HXCPP_CAPTURE_SOURCE_SHA256,
                        "original_hxcpp_immix_sha256": HXCPP_IMMIX_SOURCE_SHA256,
                        "diagnostic_mode": "asan" if args.asan else "recycle",
                        "recycle_diagnostic_version": RECYCLE_DIAGNOSTIC_VERSION,
                        "asan_diagnostic_version": ASAN_DIAGNOSTIC_VERSION if args.asan else None,
                        "asan_flags": list(ASAN_FLAGS) if args.asan else [],
                        "asan_options": ASAN_RUNTIME_OPTIONS if args.asan else None,
                        "compiler": str(compiler),
                        "compiler_argument_log_directory": str(compiler_log) if compiler_log else None,
                        "haxelib_preflight_command": preflight_command,
                        "generate_command": [str(part) for part in generate_command],
                        "build_command": build_command,
                        "build_returncode": native_build.returncode,
                    }
                    (build_artifacts / "build.json").write_text(
                        json.dumps(metadata, indent=2) + "\n"
                    )
                if native_build.returncode != 0:
                    return report(native_build)

                executable = cpp_target / "Main"
                if not executable.is_file():
                    print("native diagnostic build produced no Main executable", file=sys.stderr)
                    return 1
                cached_executable.parent.mkdir(parents=True, exist_ok=True)
                staged = cached_executable.with_name(f"Main.{os.getpid()}.{uuid.uuid4().hex}.tmp")
                try:
                    shutil.copy2(executable, staged)
                    os.replace(staged, cached_executable)
                finally:
                    staged.unlink(missing_ok=True)
                if build_artifacts is not None:
                    (build_artifacts / "binary-path.txt").write_text(str(cached_executable) + "\n")
                executable = cached_executable
                command = [str(executable), str(source)]
                if summary:
                    command.append("--counts-only" if counts_only else "--summary")
                if args.codename_event_walk:
                    command.append("--codename-event-walk")
                native_run, timed_out = run_bounded_native_scan(
                    command,
                    # DependencyInspector mirrors the game's destination
                    # namespace with the relative ``assets`` root.  Run the
                    # read-only diagnostic from the checkout so that this
                    # generic native registry/HXC fallback resolves against
                    # the real destination assets instead of the temporary
                    # hxcpp build directory.
                    ROOT, runtime_env, args.scan_timeout_seconds,
                )
                if build_artifacts is not None:
                    diagnostic_run_dir = cache_root / f"run-{os.getpid()}-{uuid.uuid4().hex}"
                    save_process_output(native_run, diagnostic_run_dir, "scan")
                    (diagnostic_run_dir / "run.json").write_text(json.dumps({
                        "command": command,
                        "cwd": str(ROOT),
                        "mode": "asan" if args.asan else "recycle",
                        "ASAN_OPTIONS": runtime_env.get("ASAN_OPTIONS"),
                        "returncode": native_run.returncode,
                        "timed_out": timed_out,
                        "scan_timeout_seconds": args.scan_timeout_seconds,
                        "cached_binary": False,
                    }, indent=2) + "\n")
                return report(native_run)

            # Keep a portable fallback for environments that have the Haxe/Neko
            # toolchain but no hxcpp/g++ installation.  CI still exercises the
            # native path whenever hxcpp is available; this branch is only for
            # reduced source-only checkouts.
            neko_target = temp / "Main.n"
            neko_target_relative = Path("..") / neko_target.name
            compile_result = subprocess.run(
                [str(short_haxe), "-cp", str(short_links["hscript"]),
                 "-cp", str(short_links["src"]), "-main", "Main", "-neko",
                 str(neko_target_relative)],
                cwd=cpp_target,
                env=native_env,
                capture_output=True,
                text=True,
                timeout=remaining(),
            )
            if compile_result.returncode != 0:
                return report(compile_result)
            command = [str(absolute_neko / "neko"),
                       str(neko_target), str(source)]
            if summary:
                command.append("--counts-only" if counts_only else "--summary")
            if args.codename_event_walk:
                command.append("--codename-event-walk")
            fallback_env = os.environ.copy()
            fallback_env.update({
                "TMPDIR": str(project_tmp),
                "LD_LIBRARY_PATH": str(absolute_neko)
                + (os.pathsep + os.environ["LD_LIBRARY_PATH"]
                   if os.environ.get("LD_LIBRARY_PATH") else ""),
            })
            if args.trace_psych_discovery:
                fallback_env["DISAPPOINTINGPLUS_PSYCH_DISCOVERY_TRACE"] = "1"
            else:
                fallback_env.pop("DISAPPOINTINGPLUS_PSYCH_DISCOVERY_TRACE", None)
            return report(subprocess.run(
                command,
                # Keep the fallback backend on the same destination-relative
                # working directory as the native diagnostic above.
                cwd=ROOT,
                env=fallback_env,
                capture_output=True,
                text=True,
                timeout=remaining(),
            ))
        finally:
            for link in short_links.values():
                try:
                    (cpp_target / link).unlink()
                except FileNotFoundError:
                    pass
            if root_dir_fd is not None:
                os.close(root_dir_fd)
            if private_diagnostic and not keep_private_workspace:
                shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
