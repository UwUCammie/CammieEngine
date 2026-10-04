"""Apply the Linux build's LLVM-MinGW resource fix for native Windows builds."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_source(text: str) -> str:
    if 'dp-llvm-mingw-dll-auto-import' not in text:
        old = '<flag value="--enable-auto-import"/>'
        if text.count(old) != 1:
            raise ValueError('Pinned hxcpp DLL auto-import flag was not unique')
        text = text.replace(old, '<!-- dp-llvm-mingw-dll-auto-import -->\n'
                            '  <flag value="-Wl,--enable-auto-import"/>', 1)
    if "dp-llvm-mingw-resource-compiler" not in text:
        if text.count('</compiler>') != 1:
            raise ValueError('Pinned hxcpp MinGW compiler section was not unique')
        text = text.replace('</compiler>', '''  <!-- dp-llvm-mingw-resource-compiler -->
  <rcexe name="${HXCPP_RC}" if="HXCPP_RC" />
  <rcext value=".res" if="HXCPP_RC" />
</compiler>''', 1)
    if 'dp-llvm-mingw-gcc-runtime-section' not in text:
        rules = []
        for name in ('libgcc_s_dw2-1.dll', 'libstdc++-6.dll'):
            rule = f'<copyFile toolId="exe" name="{name}" from="${{MINGW_ROOT}}/bin" allowMissing="true" unless="no_shared_libs"/>'
            if rule not in text:
                raise ValueError(f'Pinned hxcpp runtime rule missing: {name}')
            text = text.replace(rule, '', 1)
            rules.append(rule)
        text = text.replace('</xml>', '<!-- dp-llvm-mingw-gcc-runtime-section -->\n'
                            '<section unless="HXCPP_RC">\n' + '\n'.join(rules)
                            + '\n</section>\n</xml>', 1)
    return text


def main() -> int:
    path = ROOT / '.haxelib/hxcpp/4,3,2/toolchain/mingw-toolchain.xml'
    original = path.read_text(encoding='utf-8')
    patched = patch_source(original)
    if patched != original:
        path.write_text(patched, encoding='utf-8')
    print('>> verified native LLVM-MinGW resource and runtime rules')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
