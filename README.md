# CammieEngine v0.0.1

An **alpha** Friday Night Funkin’ engine built on Disappointing Plus, Modding
Plus, and HaxeFlixel. Includes gameplay, a chart editor, scripting, and mod imports.

Compatibility with **Codename, Modding Plus/Poop, Psych, V-Slice, and Nightmare
Vision** is experimental. Some scripts, effects, menus, and editors remain
incomplete; importing successfully does not guarantee accurate playback.

## Play on Windows

Download the **Windows x64 ZIP** from [GitHub Releases](https://github.com/UwUCammie/CammieEngine/releases), extract
it to a writable folder, and run **Funkin.exe**. Keep the included assets, DLLs,
and tools beside it. Players do not need a compiler or source checkout.

Development ZIPs are also available from successful **Windows x64 alpha** runs
under GitHub Actions. Maintainers can run that workflow manually or push a tag
such as `v0.0.1-alpha.1` to attach a ZIP and checksum to a prerelease. The first
Windows build still needs native verification.

## Build from source

Linux, with C++ build tools installed:

```sh
./run.sh build  # compile without launching
./run.sh        # compile when needed and play
```

Windows developers can use `run.bat build` with the Visual Studio C++ workload.
The launchers install the pinned Haxe/Neko tools and libraries automatically.
Close the game before rebuilding.

## Local imports

Bundled assets are included. Imported mod libraries, build output, and personal
runtime files stay local and are excluded from Git automatically—including
future imports. Deliberate new engine assets in ignored folders require
`git add -f`; ordinary source-code changes do not.

## Details and credits

Maintained by **UwUCammie**, building on AFunkinDisappointment’s Disappointing
Plus and the original Modding Plus and Friday Night Funkin’ contributors.

- [Compatibility inventory](tools/reports/example-mods-compatibility-inventory.md)
  and [verification report](tools/reports/engine-discrepancies-verification.md)
- [Architecture](ENGINE_ARCHITECTURE.md) · [Update log](updateLog.txt)
- [Credits](assets/data/credits.txt) · [License](LICENSE) · [Third-party notices](NOTICE)
