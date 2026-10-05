"""Fast checks for the platform build entry points.

These tests intentionally inspect only small scripts and documentation. They
must not walk or package the repository's multi-gigabyte asset library.
"""
from pathlib import Path
from haxe_test_support import FixturePath as Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class BuildScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build_sh = (ROOT / "build.sh").read_text(encoding="utf-8")
        cls.run_sh = (ROOT / "run.sh").read_text(encoding="utf-8")
        cls.run_bat = (ROOT / "run.bat").read_text(encoding="utf-8")
        cls.apprun = (ROOT / "tools" / "appimage" / "AppRun").read_text(
            encoding="utf-8"
        )
        cls.flixel_patch = (ROOT / "tools" / "patch_flixel_fallback.ps1").read_text(
            encoding="utf-8"
        )
        cls.desktop = (
            ROOT / "tools" / "appimage" / "disappointing-plus.desktop"
        ).read_text(encoding="utf-8")
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        cls.project_xml = (ROOT / "Project.xml").read_text(encoding="utf-8")
        cls.release_build = (ROOT / "build-windows-release.sh").read_text(encoding="utf-8")
        cls.package_script = (ROOT / "tools/package_windows_release.py").read_text(encoding="utf-8")
        cls.gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    def test_build_sh_has_explicit_targets(self):
        self.assertIn("./build.sh linux", self.build_sh)
        self.assertIn("./build.sh appimage", self.build_sh)
        self.assertIn("./build.sh windows", self.build_sh)
        self.assertIn("run.sh", self.build_sh)
        self.assertIn("appimagetool", self.build_sh)
        self.assertIn('"$APPDIR/disappointing-plus.desktop"', self.build_sh)
        self.assertIn('"$APPDIR/disappointing-plus.png"', self.build_sh)

    def test_run_sh_allows_an_intentionally_empty_source_asset_tree(self):
        self.assertIn("mkdir -p assets/images assets/videos assets/data", self.run_sh)
        self.assertIn("assets/songs assets/sounds assets/module", self.run_sh)
        self.assertIn("if not os.path.isdir(data):", self.run_sh)
        self.assertIn("case fix: skipped (assets/data is not present)", self.run_sh)
        self.assertLess(
            self.run_sh.index("if not os.path.isdir(data):"),
            self.run_sh.index("data_mtime = os.path.getmtime(data)"),
        )

    def test_run_sh_preserves_runtime_imports_across_lime_asset_sync(self):
        self.assertIn('RUNTIME_ASSETS="$BUILD_DIR/linux/bin/assets"', self.run_sh)
        self.assertIn('cp -al "$RUNTIME_ASSETS" "$ASSETS_BAK"', self.run_sh)
        self.assertIn('cp -aln "$ASSETS_BAK"/. "$RUNTIME_ASSETS"/', self.run_sh)
        self.assertIn("restore_runtime_assets", self.run_sh)
        self.assertIn("trap finish_build EXIT", self.run_sh)

    def test_run_sh_preserves_standalone_import_cache_by_rename(self):
        self.assertIn('RUNTIME_IMPORT_CACHE="$BUILD_DIR/linux/bin/import-cache"', self.run_sh)
        self.assertIn('IMPORT_CACHE_HOLD="$BUILD_DIR/linux/.import-cache-preserve-$$"', self.run_sh)
        self.assertIn('mv -- "$RUNTIME_IMPORT_CACHE" "$IMPORT_CACHE_HOLD"', self.run_sh)
        self.assertIn('mv -- "$IMPORT_CACHE_HOLD" "$RUNTIME_IMPORT_CACHE"', self.run_sh)
        self.assertIn("restore_import_cache", self.run_sh)
        self.assertNotIn('cp -al "$RUNTIME_IMPORT_CACHE"', self.run_sh)
        self.assertIn("/import-cache/", self.gitignore)

    def test_live_options_are_saved_before_runtime_assets_snapshot(self):
        self.assertLess(
            self.run_sh.index('cp "$LIVE_OPTS" "$OPTS_BAK"'),
            self.run_sh.index('cp -al "$RUNTIME_ASSETS" "$ASSETS_BAK"'),
        )
        self.assertLess(
            self.run_sh.index('restore_runtime_assets\n'),
            self.run_sh.index('restore_options\n'),
        )

    def test_run_sh_has_a_cross_build_setup_only_mode(self):
        # The Linux-host Windows path must get the same repository preparation
        # without triggering a native Linux build or launch.
        for text in (
            "./run.sh setup",
            "SETUP_ONLY=0",
            '[[ "$MODE" == "setup" ]] && SETUP_ONLY=1',
            "project setup complete (no Linux build or launch)",
            '"$SETUP_ONLY" == "0"',
            '"$MODE" != "server" && "$SETUP_ONLY" == "0"',
        ):
            self.assertIn(text, self.run_sh)
        self.assertIn("case fix: ", self.run_sh)
        self.assertIn('Project.xml', self.run_sh)
        self.assertIn("rapidjson const-assignment", self.run_sh)
        self.assertIn("dpui-fallback-frame", self.run_sh)
        self.assertIn("python3 tools/patch_openfl_context3d_readback.py", self.run_sh)

    def test_builds_bootstrap_a_checksum_verified_astc_decoder(self):
        self.assertIn('ASTCENC_VERSION="3.7"', self.run_sh)
        self.assertIn("astcenc-3.7", self.run_bat)
        for script in (self.run_sh, self.run_bat):
            self.assertIn("astcenc-sse2", script)
            self.assertIn("SHA256", script.upper())
        self.assertIn(
            "f69c2acbb3b07386cc95001c253cddfa567e71b9618682856f0ff600955cc2ba",
            self.run_sh,
        )
        self.assertIn(
            "ecb0e1a5dcbfbaca8a38630e427638380b9d337c266660b39738260e1df5244a",
            self.run_bat,
        )
        self.assertIn('runtime_decoder="$bin_dir/tools/astcenc"', self.run_sh)
        self.assertIn('!ASTCENC_RUNTIME!\\astcenc.exe', self.run_bat)
        self.assertIn("ASTCENC_VERSION_FILE", self.run_sh)
        self.assertIn("ASTCENC_VERSION_FILE", self.run_bat)
        license_path = ROOT / "tools" / "licenses" / "astcenc-LICENSE.txt"
        self.assertIn("Apache License", license_path.read_text(encoding="utf-8"))
        self.assertIn("astcenc-LICENSE.txt", self.run_sh)
        self.assertIn("astcenc-LICENSE.txt", self.run_bat)

    def test_windows_target_uses_hxcpp_mingw_and_keeps_native_delegate(self):
        # Wine is now an explicit post-build smoke mode, while compilation
        # must use hxcpp's Linux-host MinGW path and native run.bat remains the
        # Windows/MSVC entry point.
        self.assertIn("-Dwindows", self.build_sh)
        self.assertIn("-DHXCPP_MINGW", self.build_sh)
        self.assertIn("-DHXCPP_M64", self.build_sh)
        # Lime's target selector is separate from the Haxe/hxcpp defines;
        # keep the Linux-host build on the C++ MinGW path instead of its
        # foreign-desktop Neko fallback.
        self.assertIn("windows -mingw -Dwindows", self.build_sh)
        self.assertIn("MINGW_ROOT", self.build_sh)
        self.assertIn("HXCPP_MINGW_EXE", self.build_sh)
        self.assertIn("x86_64-w64-mingw32-g++", self.build_sh)
        self.assertIn("run.bat", self.build_sh)
        self.assertIn("native Windows", self.build_sh)

    def test_windows_cross_build_accepts_self_contained_llvm_mingw(self):
        # CachyOS/Arch's llvm-mingw package provides target-prefixed clang
        # wrappers and a PREFIX/<triplet> sysroot instead of GCC's usual
        # /usr/<triplet> layout.
        for text in (
            "x86_64-w64-mingw32-clang++",
            "compiler_family=\"llvm-mingw\"",
            "compiler_sysroot/$triplet/include",
            "$root_value/$triplet/include",
            "x86_64-w64-windows-gnu*",
            "HXCPP_AR",
            "HXCPP_RANLIB",
            "HXCPP_STRIP",
        ):
            self.assertIn(text, self.build_sh)
        self.assertIn("self-contained LLVM-MinGW", self.build_sh)

    def test_windows_cross_build_keeps_setup_lock_and_decoder_packaging(self):
        for text in (
            "prepare_cross_project",
            '"$ROOT/run.sh" setup',
            'source "$ROOT/tools/runtime_lock.sh"',
            'lock_runtime "$ROOT/.tools/runtime-$debug.lock"',
            "ensure_windows_astc_decoder",
            "ecb0e1a5dcbfbaca8a38630e427638380b9d337c266660b39738260e1df5244a",
            "astcenc-sse2.exe",
            '"$runtime_tools/astcenc.exe"',
            '"$runtime_tools/astcenc-LICENSE.txt"',
            "tools/licenses/astcenc-LICENSE.txt",
        ):
            self.assertIn(text, self.build_sh)

    def test_wine_smoke_is_explicit_bounded_and_reports_outcomes(self):
        self.assertIn("--wine-smoke", self.build_sh)
        self.assertIn("--kill-after=5s", self.build_sh)
        self.assertIn("GNU coreutils", self.build_sh)
        self.assertIn('"${wine_timeout}s"', self.build_sh)
        self.assertIn("startup window", self.build_sh)
        self.assertIn("crashed or exited", self.build_sh)
        self.assertIn("WINEPREFIX", self.build_sh)
        self.assertIn("WINE_BIN", self.readme)
        self.assertIn("GNU `timeout`", self.readme)
        self.assertIn("export/<mode>/windows/bin/tools/", self.readme)

    def test_cross_build_dependency_checks_are_actionable_and_path_safe(self):
        for text in (
            "run ./run.sh setup once",
            "portable Haxe 4.3.x is missing",
            "MinGW compiler",
            "LLVM-MinGW",
            "MINGW_ROOT must be a MinGW sysroot",
            'export TMPDIR="$PROJECT_TMP"',
            '"$root_value/include"',
            '"$root_value/lib"',
            '"$resolved_compiler" -print-sysroot',
            '"$resolved_compiler" --version',
            '"$resolved_compiler" -dumpmachine',
            'resolved="$ROOT/$resolved"',
            'wine_prefix="$ROOT/$wine_prefix"',
        ):
            self.assertIn(text, self.build_sh)
        # The compiler and executable paths are always passed as quoted shell
        # arguments, including paths with spaces.
        self.assertIn('"${lime_args[@]}"', self.build_sh)
        self.assertIn('"$executable"', self.build_sh)

    def test_run_bat_is_cwd_safe_and_native_windows(self):
        self.assertIn("cd /d", self.run_bat.lower())
        self.assertIn("%~dp0", self.run_bat)
        self.assertIn("HAXELIB_PATH", self.run_bat)
        self.assertIn("haxe-4.3.6-win64.zip", self.run_bat)
        self.assertIn("neko-2.3.0-win64.zip", self.run_bat)
        self.assertIn("haxelib run lime build windows", self.run_bat)
        self.assertIn(":ensure_git", self.run_bat)
        self.assertIn("MinGit-2.56.0-64-bit.zip", self.run_bat)
        self.assertIn("064b440ff870ed5198527e8f3a92cdf5bd2fd0fedf5e718af95e3fdaddeff718", self.run_bat)
        self.assertIn("Funkin.exe", self.run_bat)
        self.assertIn("-D32bit -32", self.run_bat)
        # The documented default/release path must actually compile before
        # launching.  Keep the native compiler check explicit too: hxcpp
        # cannot produce a Windows binary from a Linux Wine environment.
        self.assertIn(":do_build", self.run_bat)
        self.assertIn('if /I not "!MODE!"=="release"', self.run_bat)
        self.assertIn(":ensure_native_compiler", self.run_bat)
        self.assertIn("vswhere.exe", self.run_bat)
        self.assertIn(":patch_haxelibs", self.run_bat)
        self.assertIn("patch_flixel_fallback.ps1", self.run_bat)

    def test_windows_cache_hit_skips_repeated_setup_but_keeps_full_test_suite(self):
        cache_check = self.run_bat.index('tools\\launch_cache.py" check')
        haxelib_setup = self.run_bat.index('call :ensure_haxelibs')
        self.assertLess(cache_check, haxelib_setup)
        self.assertIn('if /I "!MODE!"=="rebuild" goto prepare_build', self.run_bat)
        self.assertIn(':cached_tests', self.run_bat)
        self.assertIn('goto run_tests', self.run_bat)
        self.assertIn('tools\\run_tests.py"', self.run_bat)

    def test_build_entry_points_use_project_local_scratch_space(self):
        self.assertIn('PROJECT_TMP="$PWD/tmp"', self.run_sh)
        self.assertIn('export TMPDIR="$PROJECT_TMP"', self.run_sh)
        self.assertIn('HAXE_ARCHIVE="$PROJECT_TMP/', self.run_sh)
        self.assertIn('NEKO_ARCHIVE="$PROJECT_TMP/', self.run_sh)
        self.assertNotIn("/tmp/haxe", self.run_sh)
        self.assertNotIn("/tmp/neko", self.run_sh)
        self.assertIn('PROJECT_TMP="$ROOT/tmp"', self.build_sh)
        self.assertIn('export TMPDIR="$PROJECT_TMP"', self.build_sh)
        self.assertIn('set "PROJECT_TMP=!ROOT!\\tmp"', self.run_bat)
        self.assertIn('set "TEMP=!PROJECT_TMP!"', self.run_bat)
        self.assertIn('set "TMP=!PROJECT_TMP!"', self.run_bat)
        self.assertIn("project-local `tmp/`", self.readme)

    def test_windows_applies_the_native_empty_frame_fix(self):
        # The fallback prevents the same FlxSprite null-frame crash on MSVC
        # builds.  rapidjson remains intentionally Linux/gcc-only.
        self.assertIn("dpui-fallback-frame", self.flixel_patch)
        self.assertIn("makeGraphic(1, 1, 0, true", self.flixel_patch)
        self.assertIn("rapidjson", self.run_bat)
        self.assertIn("Linux/gcc-specific", self.run_bat)

    def test_native_flixel_action_cache_uses_per_update_frames(self):
        patcher = "tools/patch_flixel_input_frame_cache.py"
        self.assertIn(patcher, self.run_sh)
        self.assertIn("tools\\patch_flixel_input_frame_cache.py", self.run_bat)
        self.assertIn("prepare_cross_project", self.build_sh)
        self.assertIn('"$ROOT/run.sh" setup', self.build_sh)
        self.assertIn('python3 "$ROOT/tools/patch_flixel_input_frame_cache.py"', self.build_sh)
        from tools import launch_cache
        self.assertIn(patcher, launch_cache.HELPERS)

    def test_desktop_runtime_trees_stay_on_disk(self):
        for asset in ("music", "songs", "module"):
            self.assertIn(
                f'<assets path="assets/{asset}" embed="false" />',
                self.project_xml,
            )

    def test_apprun_has_writable_runtime_options(self):
        self.assertIn("DISAPPOINTINGPLUS_RUNTIME_DIR", self.apprun)
        self.assertIn("APPIMAGE_EXTRACT_AND_RUN", self.apprun)
        self.assertIn("cp -a", self.apprun)
        self.assertIn("assets/data", self.apprun)
        self.assertIn("read-only", self.apprun)

    def test_appimage_desktop_entry_points_at_apprun(self):
        self.assertIn("Type=Application", self.desktop)
        self.assertIn("Exec=AppRun %U", self.desktop)
        self.assertIn("Icon=disappointing-plus", self.desktop)

    def test_readme_documents_native_targets_and_appimage_writes(self):
        for text in (
            "./build.sh appimage",
            "./build-windows-release.sh",
            ".\\run.bat test",
            "DISAPPOINTINGPLUS_RUNTIME_DIR",
            "APPIMAGE_EXTRACT_AND_RUN",
            "read-only",
            "Windows x64 ZIP",
            "-Dwindows -DHXCPP_MINGW -DHXCPP_M64",
            ".tools/llvm-mingw",
            "HXCPP_MINGW_EXE",
            "MINGW_ROOT",
            "--wine-smoke",
            "run.bat` is the native Windows entry point",
        ):
            self.assertIn(text, self.readme)

    def test_current_release_version_is_used_by_branding_and_package_defaults(self):
        version = (ROOT / "VERSION").read_text(encoding="ascii").strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertIn(f'version="{version}"', self.project_xml)
        self.assertIn(f"CammieEngine v{version}", self.readme)
        user_readme = (ROOT / "USER-README.txt").read_text(encoding="utf-8")
        self.assertIn(f"CammieEngine v{version}", user_readme)
        update_log = (ROOT / "updateLog.txt").read_text(encoding="utf-8")
        current_headings = (f"{version} development - CammieEngine", f"v{version} alpha - CammieEngine")
        self.assertTrue(any(heading in update_log for heading in current_headings),
                        "Current version needs a development or alpha changelog heading")
        branding = (ROOT / "source/EngineBranding.hx").read_text(encoding="utf-8")
        self.assertIn(f"FALLBACK_VERSION:String = '{version}'", branding)
        self.assertIn("< VERSION", self.release_build)
        self.assertIn('DEFAULT_RELEASE_TAG = "v" + (ROOT / "VERSION")', self.package_script)
        self.assertIn("default=DEFAULT_RELEASE_TAG", self.package_script)


if __name__ == "__main__":
    unittest.main()
