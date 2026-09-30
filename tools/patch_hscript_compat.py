#!/usr/bin/env python3
"""Apply the pinned HScript 2.5.0 compatibility patches on every host.

The ordered transformations below are the former run.sh patch chain.  Each
step keeps its exact source pattern and marker, while this runner makes a clean
pinned install usable from both run.sh and run.bat and fails when upstream
source no longer matches.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTERP = ROOT / ".haxelib" / "hscript" / "2,5,0" / "hscript" / "Interp.hx"

PATCH_STEPS = [
    {
        "name": 'null-access fallback',
        "mode": 'missing',
        "marker": 'hscript-null-access',
        "checks": ('function nullAccessDiagnose', '_dpNullAccessSeen'),
        "script": r'''
import sys
p = sys.argv[1]
s = open(p).read()
old_set = "\tfunction set( o : Dynamic, f : String, v : Dynamic ) : Dynamic {\n\t\tif( o == null ) error(EInvalidAccess(f));\n\t\tReflect.setProperty(o,f,v);\n\t\treturn v;\n\t}"
new_set_lines = [
"\tfunction set( o : Dynamic, f : String, v : Dynamic ) : Dynamic {",
"\t\t// DisappointingPlus local patch: a donor script writing a field on a",
"\t\t// null object (for example a V-Slice PlayState member this engine does",
"\t\t// not carry) used to throw EInvalidAccess which, through the native",
"\t\t// Dynamic-call plumbing, aborted the remainder of the closure with no",
"\t\t// visible error - entire stage backgrounds silently disappeared. Degrade",
"\t\t// the write to a diagnosed no-op so the rest of the callback keeps",
"\t\t// running; genuinely null objects are still reported once per field.",
"\t\tif( o == null ) {",
"\t\t\tnullAccessDiagnose(\"write\", f);",
"\t\t\treturn v;",
"\t\t}",
"\t\tReflect.setProperty(o,f,v);",
"\t\treturn v;",
"\t}",
"",
"\tfunction nullAccessDiagnose( kind : String, f : String ) : Void {",
"\t\t#if sys",
"\t\tvar key = kind + \":\" + f;",
"\t\tvar seen = _dpNullAccessSeen;",
"\t\tif( seen == null ) {",
"\t\t\tseen = new haxe.ds.StringMap();",
"\t\t\t_dpNullAccessSeen = seen;",
"\t\t}",
"\t\tif( !seen.exists(key) ) {",
"\t\t\tseen.set(key, true);",
"\t\t\tSys.println('[hscript-null-access] ' + kind + ' to \"' + f + '\" on a null object was ignored so the script can continue');",
"\t\t}",
"\t\t#end",
"\t}",
]
new_set = "\n".join(new_set_lines)
old_get = "\tfunction get( o : Dynamic, f : String ) : Dynamic {\n\t\tif ( o == null ) error(EInvalidAccess(f));"
new_get_lines = [
"\tfunction get( o : Dynamic, f : String ) : Dynamic {",
"\t\t// DisappointingPlus local patch: reading a field of a null object used",
"\t\t// to throw EInvalidAccess which, on native Dynamic-call paths, can end",
"\t\t// the whole callback with no visible error. Imported scripts commonly",
"\t\t// probe optional graph members this way; return null (diagnosed once)",
"\t\t// so their own null checks keep working.",
"\t\tif ( o == null ) {",
"\t\t\tnullAccessDiagnose(\"read\", f);",
"\t\t\treturn null;",
"\t\t}",
]
new_get = "\n".join(new_get_lines)
old_field_map = "\tvar binops : Map<String, Expr -> Expr -> Dynamic >;\n\t#else"
new_field_map = "\tvar binops : Map<String, Expr -> Expr -> Dynamic >;\n\t// DisappointingPlus local patch: dedupe set for null-access diagnostics.\n\tvar _dpNullAccessSeen : Map<String,Bool>;\n\t#else"
old_field_hash = "\tvar binops : Hash< Expr -> Expr -> Dynamic >;\n\t#end"
new_field_hash = "\tvar binops : Hash< Expr -> Expr -> Dynamic >;\n\t// DisappointingPlus local patch: dedupe set for null-access diagnostics.\n\tvar _dpNullAccessSeen : Map<String,Bool>;\n\t#end"
ok = 0
if old_set in s:
    s = s.replace(old_set, new_set); ok += 1
if old_get in s:
    s = s.replace(old_get, new_get); ok += 1
if old_field_map in s:
    s = s.replace(old_field_map, new_field_map, 1); ok += 1
if old_field_hash in s:
    s = s.replace(old_field_hash, new_field_hash, 1); ok += 1
if ok == 4:
    open(p, 'w').write(s)
    print('>> patched hscript null-access silent-abort fallback')
else:
    print('!! hscript patch matched only %d/4 patterns - Interp.hx changed upstream?' % ok)
''',
    },
    {
        "name": 'null-access diagnostic context',
        "mode": 'missing',
        "marker": 'hscript-null-access-context',
        "checks": ('hscript-null-access-context',),
        "script": r"""
import sys
p = sys.argv[1]
s = open(p).read()
start = s.find("\tfunction nullAccessDiagnose( kind : String, f : String ) : Void {")
body_end = s.find("\n\t}", start)
if start < 0 or body_end < 0:
    raise SystemExit('hscript null-access context patch could not find nullAccessDiagnose')
end = body_end + len("\n\t}")
new = '''\tfunction nullAccessDiagnose( kind : String, f : String ) : Void {
		// DisappointingPlus local patch (hscript-null-access-context): include
		// the active imported source/callback so a null receiver can be traced
		// to its source API use without changing the safe null result.
		#if sys
		var source = variables.get("__compatDiagnosticSource");
		var callback = variables.get("__compatDiagnosticCallback");
		var context = source == null ? "" : Std.string(source);
		if( callback != null ) context += "#" + Std.string(callback);
		var key = kind + ":" + f + ":" + context;
		var seen = _dpNullAccessSeen;
		if( seen == null ) {
			seen = new haxe.ds.StringMap();
			_dpNullAccessSeen = seen;
		}
		if( !seen.exists(key) ) {
			seen.set(key, true);
			Sys.println('[hscript-null-access] ' + kind + ' to "' + f + '" on a null object was ignored so the script can continue' + (context == '' ? '' : ' (' + context + ')'));
		}
		#end
	}'''
open(p, 'w').write(s[:start] + new + s[end:])
print('patched hscript null-access diagnostic context')
""",
    },
    {
        "name": 'null-operand guards',
        "mode": 'missing',
        "marker": 'hscript-null-operand',
        "checks": ('function nullOperandDiagnose', 'me.nullOperandDiagnose("+")'),
        "script": r'''
import sys
p = sys.argv[1]
s = open(p).read()
helper = """\t/**
\t * On hxcpp, arithmetic/ordering Dynamic operations with a null operand
\t * dereference the null value's vtable inside generated operator plumbing
\t * and SIGSEGV before any exception can be raised. Ported scripts that
\t * chain optional lookups (e.g. missing donor metadata) must degrade like
\t * the web engines do instead of taking the process down.
\t */
\tfunction nullOperandDiagnose( op : String ) : Void {
\t\t#if sys
\t\tvar key = "operand:" + op;
\t\tvar seen = _dpNullAccessSeen;
\t\tif( seen == null ) {
\t\t\tseen = new haxe.ds.StringMap();
\t\t\t_dpNullAccessSeen = seen;
\t\t}
\t\tif( !seen.exists(key) ) {
\t\t\tseen.set(key, true);
\t\t\tSys.println('[hscript-null-operand] "' + op + '" used a null operand and returned null so the script can continue');
\t\t}
\t\t#end
\t}

\tfunction fcall( o : Dynamic, f : String, args : Array<Dynamic> ) : Dynamic {"""
anchor_fcall = "\tfunction fcall( o : Dynamic, f : String, args : Array<Dynamic> ) : Dynamic {"
if anchor_fcall in s and "nullOperandDiagnose" not in s:
    s = s.replace(anchor_fcall, helper, 1)

old_ops = """\t\tbinops.set("+",function(e1,e2) return me.expr(e1) + me.expr(e2));
\t\tbinops.set("-",function(e1,e2) return me.expr(e1) - me.expr(e2));
\t\tbinops.set("*",function(e1,e2) return me.expr(e1) * me.expr(e2));
\t\tbinops.set("/",function(e1,e2) return me.expr(e1) / me.expr(e2));
\t\tbinops.set("%",function(e1,e2) return me.expr(e1) % me.expr(e2));
\t\tbinops.set("&",function(e1,e2) return me.expr(e1) & me.expr(e2));
\t\tbinops.set("|",function(e1,e2) return me.expr(e1) | me.expr(e2));
\t\tbinops.set("^",function(e1,e2) return me.expr(e1) ^ me.expr(e2));
\t\tbinops.set("<<",function(e1,e2) return me.expr(e1) << me.expr(e2));
\t\tbinops.set(">>",function(e1,e2) return me.expr(e1) >> me.expr(e2));
\t\tbinops.set(">>>",function(e1,e2) return me.expr(e1) >>> me.expr(e2));"""
def guarded(symbol, body):
    return ('\t\tbinops.set("%s",function(e1,e2) { var a = me.expr(e1), b = me.expr(e2); '
            'if( a == null || b == null ) { me.nullOperandDiagnose("%s"); return null; } return %s; });'
            % (symbol, symbol, body))
new_ops_lines = [
    guarded("+", "a + b"),
    guarded("-", "a - b"),
    guarded("*", "a * b"),
    guarded("/", "a / b"),
    guarded("%", "a % b"),
    guarded("&", "a & b"),
    guarded("|", "a | b"),
    guarded("^", "a ^ b"),
    guarded("<<", "a << b"),
    guarded(">>", "a >> b"),
    guarded(">>>", "a >>> b"),
]
if old_ops in s:
    s = s.replace(old_ops, "\n".join(new_ops_lines), 1)

old_cmp = """\t\tbinops.set(">=",function(e1,e2) return me.expr(e1) >= me.expr(e2));
\t\tbinops.set("<=",function(e1,e2) return me.expr(e1) <= me.expr(e2));
\t\tbinops.set(">",function(e1,e2) return me.expr(e1) > me.expr(e2));
\t\tbinops.set("<",function(e1,e2) return me.expr(e1) < me.expr(e2));"""
def guarded_cmp(symbol, body):
    return ('\t\tbinops.set("%s",function(e1,e2) { var a = me.expr(e1), b = me.expr(e2); '
            'if( a == null || b == null ) { me.nullOperandDiagnose("%s"); return false; } return %s; });'
            % (symbol, symbol, body))
new_cmp_lines = [
    guarded_cmp(">=", "a >= b"),
    guarded_cmp("<=", "a <= b"),
    guarded_cmp(">", "a > b"),
    guarded_cmp("<", "a < b"),
]
if old_cmp in s:
    s = s.replace(old_cmp, "\n".join(new_cmp_lines), 1)

old_range = '\t\tbinops.set("...",function(e1,e2) return new #if (haxe_211 || haxe3) IntIterator #else IntIter #end(me.expr(e1),me.expr(e2)));'
new_range = ('\t\tbinops.set("...",function(e1,e2) { var a = me.expr(e1), b = me.expr(e2); '
             'if( a == null || b == null ) { me.nullOperandDiagnose("..."); return new #if (haxe_211 || haxe3) IntIterator #else IntIter #end(0,0); } '
             'return new #if (haxe_211 || haxe3) IntIterator #else IntIter #end(a,b); });')
if old_range in s:
    s = s.replace(old_range, new_range, 1)

import re
for symbol, body in [("+=", "v1 + v2"), ("-=", "v1 - v2"), ("*=", "v1 * v2"), ("/=", "v1 / v2"),
                     ("%=", "v1 % v2"), ("&=", "v1 & v2"), ("|=", "v1 | v2"), ("^=", "v1 ^ v2"),
                     ("<<=", "v1 << v2"), (">>=", "v1 >> v2"), (">>>=", "v1 >>> v2")]:
    pat = re.compile(r'assignOp\("' + re.escape(symbol) + r'",function\(v1(:[^)]*)?,v2(:[^)]*)?\) return (v1 [^;]+);\)')
    m = pat.search(s)
    if m:
        s = s[:m.start()] + ('assignOp("%s",function(v1:Dynamic,v2:Dynamic) { if( v1 == null || v2 == null ) { me.nullOperandDiagnose("%s"); return null; } return %s; })'
                             % (symbol, symbol, m.group(3))) + s[m.end():]

if "nullOperandDiagnose" not in s:
    print("hscript binop guard patch did not apply", file=sys.stderr)
    sys.exit(1)
open(p, "w").write(s)
print("patched hscript binops with null-operand guards")
''',
    },
    {
        "name": 'null-operand diagnostic context',
        "mode": 'legacy-key',
        "marker": 'var key = "operand:" + op;',
        "checks": ('var key = "operand:" + op + ":" + context;',),
        "script": r"""
import sys
p = sys.argv[1]
s = open(p).read()
old_key = '\t\tvar key = "operand:" + op;'
new_key = '''\t\tvar source = variables.get("__compatDiagnosticSource");
\t\tvar callback = variables.get("__compatDiagnosticCallback");
\t\tvar context = source == null ? "" : Std.string(source);
\t\tif( callback != null ) context += "#" + Std.string(callback);
\t\tvar key = "operand:" + op + ":" + context;'''
# Include the closing quote around the operator in the original message.
old_message = "'\" used a null operand and returned null so the script can continue'"
new_message = old_message + " + (context == '' ? '' : ' (' + context + ')')"
if old_key not in s or old_message not in s:
    raise SystemExit('hscript diagnostic context patch did not apply')
s = s.replace(old_key, new_key, 1).replace(old_message, new_message, 1)
open(p, 'w').write(s)
print('patched hscript null-operand diagnostic context')
""",
    },
    {
        "name": 'float arithmetic promotion',
        "mode": 'missing',
        "marker": 'dpFloatAwareArith',
        "checks": ('function dpFloatAwareArith', 'me.dpFloatAwareArith("-", a, b)', 'me.dpFloatAwareArith("*", a, b)', 'me.dpFloatAwareArith("%", a, b)'),
        "script": r'''
import sys
p = sys.argv[1]
s = open(p).read()
changed = False
for symbol in ("-", "*", "%"):
    old = ('\t\tbinops.set("%s",function(e1,e2) { var a = me.expr(e1), b = me.expr(e2); '
           'if( a == null || b == null ) { me.nullOperandDiagnose("%s"); return null; } return a %s b; });'
           % (symbol, symbol, symbol))
    new = ('\t\tbinops.set("%s",function(e1,e2) { var a = me.expr(e1), b = me.expr(e2); '
           'if( a == null || b == null ) { me.nullOperandDiagnose("%s"); return null; } return me.dpFloatAwareArith("%s", a, b); });'
           % (symbol, symbol, symbol))
    if old in s:
        s = s.replace(old, new, 1)
        changed = True
for symbol in ("-=", "*=", "%="):
    old = ('\t\tassignOp("%s",function(v1:Dynamic,v2:Dynamic) { if( v1 == null || v2 == null ) { me.nullOperandDiagnose("%s"); return null; } return v1 %s v2; });'
           % (symbol, symbol, symbol[:-1]))
    new = ('\t\tassignOp("%s",function(v1:Dynamic,v2:Dynamic) { if( v1 == null || v2 == null ) { me.nullOperandDiagnose("%s"); return null; } return me.dpFloatAwareArith("%s", v1, v2); });'
           % (symbol, symbol, symbol[:-1]))
    if old in s:
        s = s.replace(old, new, 1)
        changed = True
helper = (
    '\tfunction dpFloatAwareArith(op:String, a:Dynamic, b:Dynamic):Dynamic {\n'
    '\t\tif (Std.isOfType(a, Float) || Std.isOfType(b, Float)) {\n'
    '\t\t\tvar fa:Float = a;\n'
    '\t\t\tvar fb:Float = b;\n'
    '\t\t\treturn switch (op) {\n'
    '\t\t\t\tcase "-": fa - fb;\n'
    '\t\t\t\tcase "*": fa * fb;\n'
    '\t\t\t\tcase "%": fa % fb;\n'
    '\t\t\t\tdefault: a;\n'
    '\t\t\t};\n'
    '\t\t}\n'
    '\t\treturn switch (op) {\n'
    '\t\t\tcase "-": a - b;\n'
    '\t\t\tcase "*": a * b;\n'
    '\t\t\tcase "%": a % b;\n'
    '\t\t\tdefault: a;\n'
    '\t\t};\n'
    '\t}\n'
)
if 'function dpFloatAwareArith' not in s:
    anchor_fn = '\tfunction nullOperandDiagnose( op : String ) : Void {'
    if anchor_fn in s:
        s = s.replace(anchor_fn, helper + anchor_fn, 1)
        changed = True
if not changed and 'dpFloatAwareArith' not in s:
    print('hscript float-arith patch did not apply', file=sys.stderr)
    sys.exit(1)
open(p, 'w').write(s)
print('patched hscript arith with float-aware promotion')
''',
    },
    {
        "name": 'null iterator guard',
        "mode": 'missing',
        "marker": 'hscript-null-iterator',
        "checks": ('hscript-null-iterator', 'if( v == null )'),
        "script": r'''
import sys
p = sys.argv[1]
s = open(p).read()
old = """\tfunction makeIterator( v : Dynamic ) : Iterator<Dynamic> {
\t\t#if ((flash && !flash9) || (php && !php7 && haxe_ver < '4.0.0'))
\t\tif ( v.iterator != null ) v = v.iterator();
\t\t#else
\t\ttry v = v.iterator() catch( e : Dynamic ) {};
\t\t#end
\t\tif( v.hasNext == null || v.next == null ) error(EInvalidIterator(v));
\t\treturn v;
\t}"""
new = """\tfunction makeIterator( v : Dynamic ) : Iterator<Dynamic> {
\t\t// DisappointingPlus local patch (hscript-null-iterator): for-in over a
\t\t// null value used to call .iterator() on a null Dynamic, which on hxcpp
\t\t// dereferences the null object inside generated call plumbing and
\t\t// SIGSEGVs before any Haxe exception can surface. Imported scripts
\t\t// iterate optional members (for example FlxG.touches.list on a host
\t\t// which does not carry them); degrade the loop to empty with a one-time
\t\t// diagnostic, consistent with the null-access / null-operand guards.
\t\tif( v == null ) {
\t\t\tnullIteratorDiagnose();
\t\t\tvar emptyIterator : Iterator<Dynamic> = { hasNext : function() : Bool return false, next : function() : Dynamic return null };
\t\t\treturn emptyIterator;
\t\t}
\t\t#if ((flash && !flash9) || (php && !php7 && haxe_ver < '4.0.0'))
\t\tif ( v.iterator != null ) v = v.iterator();
\t\t#else
\t\ttry v = v.iterator() catch( e : Dynamic ) {};
\t\t#end
\t\tif( v.hasNext == null || v.next == null ) error(EInvalidIterator(v));
\t\treturn v;
\t}

\tfunction nullIteratorDiagnose() : Void {
\t\t#if sys
\t\tvar key = "iterator:null";
\t\tvar seen = _dpNullAccessSeen;
\t\tif( seen == null ) {
\t\t\tseen = new haxe.ds.StringMap();
\t\t\t_dpNullAccessSeen = seen;
\t\t}
\t\tif( !seen.exists(key) ) {
\t\t\tseen.set(key, true);
\t\t\tSys.println('[hscript-null-iterator] for-in used a null value and was treated as an empty loop so the script can continue');
\t\t}
\t\t#end
\t}"""
if old in s:
    open(p, 'w').write(s.replace(old, new))
    print('>> patched hscript makeIterator with null for-in guard')
else:
    print('!! hscript makeIterator patch pattern not found - Interp.hx changed upstream?')
''',
    },
    {
        "name": 'null iterator diagnostic context',
        "mode": 'missing',
        "marker": 'hscript-null-iterator-context',
        "checks": ('hscript-null-iterator-context',),
        "script": r"""
import sys
p = sys.argv[1]
s = open(p).read()
start = s.find("\tfunction nullIteratorDiagnose() : Void {")
end = s.find("\n\tfunction forLoop(", start)
if start < 0 or end < 0:
    raise SystemExit('hscript null-iterator context patch could not find nullIteratorDiagnose')
new = '''\tfunction nullIteratorDiagnose() : Void {
\t\t// DisappointingPlus local patch (hscript-null-iterator-context): keep
\t\t// null for-in diagnostics attributable to the active source callback.
\t\t#if sys
\t\tvar source = variables.get("__compatDiagnosticSource");
\t\tvar callback = variables.get("__compatDiagnosticCallback");
\t\tvar context = source == null ? "" : Std.string(source);
\t\tif( callback != null ) context += "#" + Std.string(callback);
\t\tvar key = "iterator:null:" + context;
\t\tvar seen = _dpNullAccessSeen;
\t\tif( seen == null ) {
\t\t\tseen = new haxe.ds.StringMap();
\t\t\t_dpNullAccessSeen = seen;
\t\t}
\t\tif( !seen.exists(key) ) {
\t\t\tseen.set(key, true);
\t\t\tSys.println('[hscript-null-iterator] for-in used a null value and was treated as an empty loop so the script can continue' + (context == '' ? '' : ' (' + context + ')'));
\t\t}
\t\t#end
\t}'''
open(p, 'w').write(s[:start] + new + s[end:])
print('patched hscript null-iterator diagnostic context')
""",
    },
    {
        "name": 'IntIterator bridge',
        "mode": 'missing',
        "marker": 'hscript-int-iterator',
        "checks": ('hscript-int-iterator', 'Std.isOfType(v, IntIterator)'),
        "script": r"""
import sys
p = sys.argv[1]
s = open(p).read()
old = '\t\tif( v.hasNext == null || v.next == null ) error(EInvalidIterator(v));'
new = '''\t\t// DisappointingPlus local patch (hscript-int-iterator): Haxe 4.3
\t\t// inlines these methods, which are not visible to dynamic reflection.
\t\tif( Std.isOfType(v, IntIterator) ) {
\t\t\tvar range:IntIterator = cast v;
\t\t\treturn { hasNext:function():Bool return range.hasNext(),
\t\t\t\tnext:function():Dynamic return range.next() };
\t\t}
''' + old
if old not in s:
    print('!! hscript IntIterator patch pattern not found - Interp.hx changed upstream?')
else:
    open(p, 'w').write(s.replace(old, new, 1))
    print('>> patched hscript IntIterator reflection bridge')
""",
    },
    {
        "name": 'null fcall guard',
        "mode": 'missing',
        "marker": 'hscript-null-fcall',
        "checks": ('hscript-null-fcall',),
        "script": r'''
import sys
p = sys.argv[1]
s = open(p).read()
old = """\tfunction fcall( o : Dynamic, f : String, args : Array<Dynamic> ) : Dynamic {
\t\treturn call(o, get(o, f), args);
\t}"""
new = """\tfunction fcall( o : Dynamic, f : String, args : Array<Dynamic> ) : Dynamic {
\t\t// DisappointingPlus local patch (hscript-null-fcall): calling a method
\t\t// on a null object, or on a member which does not exist, handed a null
\t\t// function to Reflect.callMethod - which on hxcpp dereferences the null
\t\t// function and SIGSEGVs before any Haxe exception can surface (donor
\t\t// scripts probe optional APIs such as missing module methods this way).
\t\t// Degrade to a diagnosed null return so the callback keeps running,
\t\t// consistent with the null-access / null-iterator guards.
\t\tvar field : Dynamic = get(o, f);
\t\tif( field == null ) {
\t\t\tnullAccessDiagnose("call", f);
\t\t\treturn null;
\t\t}
\t\treturn call(o, field, args);
\t}"""
if old in s:
    open(p, 'w').write(s.replace(old, new))
    print('>> patched hscript fcall with null-target guard')
else:
    print('!! hscript fcall patch pattern not found - Interp.hx changed upstream?')
''',
    },
    {
        "name": 'null ECall guard',
        "mode": 'missing',
        "marker": 'hscript-null-ecall',
        "checks": ('hscript-null-ecall',),
        "script": r'''
import sys
p = sys.argv[1]
s = open(p).read()
old = """\t\t\tcase EField(e,f):
\t\t\t\tvar obj = expr(e);
\t\t\t\tif( obj == null ) error(EInvalidAccess(f));
\t\t\t\treturn fcall(obj,f,args);"""
new = """\t\t\tcase EField(e,f):
\t\t\t\tvar obj = expr(e);
\t\t\t\t// DisappointingPlus local patch (hscript-null-ecall): a method
\t\t\t\t// call on a null object used to throw EInvalidAccess here, which
\t\t\t\t// through the native Dynamic-call plumbing aborts the remainder
\t\t\t\t// of the callback (after the null-access shims the null never
\t\t\t\t// surfaces as a catchable script error). Imported scripts probe
\t\t\t\t// optional donor APIs this way; degrade to a diagnosed null
\t\t\t\t// return, consistent with the null-access / null-iterator guards.
\t\t\t\tif( obj == null ) {
\t\t\t\t\tnullAccessDiagnose("call", f);
\t\t\t\t\treturn null;
\t\t\t\t}
\t\t\t\treturn fcall(obj,f,args);"""
if old in s:
    open(p, 'w').write(s.replace(old, new))
    print('>> patched hscript ECall with null-object guard')
else:
    print('!! hscript ECall patch pattern not found - Interp.hx changed upstream?')
''',
    },
    {
        "name": 'null EArray guard',
        "mode": 'missing',
        "marker": 'hscript-null-earray',
        "checks": ('hscript-null-earray',),
        "script": r'''
import sys
p = sys.argv[1]
s = open(p).read()
old = """\t\tcase EArray(e, index):
\t\t\tvar arr:Dynamic = expr(e);
\t\t\tvar index:Dynamic = expr(index);
\t\t\tif (isMap(arr)) {
\t\t\t\treturn getMapValue(arr, index);
\t\t\t}
\t\t\telse {
\t\t\t\treturn arr[index];
\t\t\t}"""
new = """\t\tcase EArray(e, index):
\t\t\tvar arr:Dynamic = expr(e);
\t\t\tvar index:Dynamic = expr(index);
\t\t\t// DisappointingPlus local patch (hscript-null-earray): indexing a
\t\t\t// null value dereferences the null inside hxcpp array access and
\t\t\t// SIGSEGVs before any exception can surface (imported scripts index
\t\t\t// optional donor metadata, such as missing splash offsets, this
\t\t\t// way). Degrade to a diagnosed null return, consistent with the
\t\t\t// null-access / null-operand / null-iterator guards.
\t\t\tif( arr == null ) {
\t\t\t\tnullAccessDiagnose("index", Std.string(index));
\t\t\t\treturn null;
\t\t\t}
\t\t\tif (isMap(arr)) {
\t\t\t\treturn getMapValue(arr, index);
\t\t\t}
\t\t\telse {
\t\t\t\treturn arr[index];
\t\t\t}"""
if old in s:
    open(p, 'w').write(s.replace(old, new))
    print('>> patched hscript EArray with null-object guard')
else:
    print('!! hscript EArray patch pattern not found - Interp.hx changed upstream?')
''',
    },
    {
        "name": 'null compound-assignment guard',
        "mode": 'missing',
        "marker": 'hscript-null-assignop',
        "checks": ('hscript-null-assignop', 'var nullOperandSeen : Bool;'),
        "script": r'''
import sys
p = sys.argv[1]
s = open(p).read()

anchor = "\tfunction nullOperandDiagnose( op : String ) : Void {\n\t\t#if sys"
flagged = """\tfunction nullOperandDiagnose( op : String ) : Void {
\t\tnullOperandSeen = true;
\t\t#if sys"""
# Declare the flag next to the existing diagnostics dedupe set (both branches).
flag_decl = "\tvar nullOperandSeen : Bool;"
if "nullOperandSeen" not in s:
    s = s.replace("\tvar _dpNullAccessSeen : Map<String,Bool>;",
                  "\tvar _dpNullAccessSeen : Map<String,Bool>;\n" + flag_decl)
    s = s.replace(anchor, flagged, 1)

old_field = """\t\tcase EField(e,f):
\t\t\tvar obj = expr(e);
\t\t\tv = fop(get(obj,f),expr(e2));
\t\t\tv = set(obj,f,v);"""
new_field = """\t\tcase EField(e,f):
\t\t\tvar obj = expr(e);
\t\t\tnullOperandSeen = false;
\t\t\tv = fop(get(obj,f),expr(e2));
\t\t\t// DisappointingPlus local patch (hscript-null-assignop): a compound
\t\t\t// assign whose operation was skipped for a null operand keeps the
\t\t\t// previous value instead of writing null into a native non-nullable
\t\t\t// field, which on hxcpp SIGSEGVs inside the reflection write.
\t\t\tif( v != null || !nullOperandSeen )
\t\t\t\tv = set(obj,f,v);
\t\t\tnullOperandSeen = false;"""
if old_field in s:
    s = s.replace(old_field, new_field, 1)

old_array = """\t\tcase EArray(e, index):
\t\t\tvar arr:Dynamic = expr(e);
\t\t\tvar index:Dynamic = expr(index);
\t\t\tif (isMap(arr)) {
\t\t\t\tv = fop(getMapValue(arr, index), expr(e2));
\t\t\t\tsetMapValue(arr, index, v);
\t\t\t}
\t\t\telse {
\t\t\t\tv = fop(arr[index],expr(e2));
\t\t\t\tarr[index] = v;
\t\t\t}"""
new_array = """\t\tcase EArray(e, index):
\t\t\tvar arr:Dynamic = expr(e);
\t\t\tvar index:Dynamic = expr(index);
\t\t\tnullOperandSeen = false;
\t\t\tif (isMap(arr)) {
\t\t\t\tv = fop(getMapValue(arr, index), expr(e2));
\t\t\t\tif( v != null || !nullOperandSeen )
\t\t\t\t\tsetMapValue(arr, index, v);
\t\t\t}
\t\t\telse {
\t\t\t\tv = fop(arr[index],expr(e2));
\t\t\t\tif( v != null || !nullOperandSeen )
\t\t\t\t\tarr[index] = v;
\t\t\t}
\t\t\tnullOperandSeen = false;"""
if old_array in s:
    s = s.replace(old_array, new_array, 1)

if "hscript-null-assignop" not in s:
    print("hscript compound-assign guard patch did not apply", file=sys.stderr)
    sys.exit(1)
open(p, "w").write(s)
print("patched hscript compound assigns with null-operand write-back guard")
''',
    },
    {
        "name": 'safe Stop catch handling',
        "mode": 'missing',
        "marker": 'hscript-stop-catch',
        "checks": ('hscript-stop-catch', 'function isHscriptStop'),
        "script": r'''
import sys
p = sys.argv[1]
s = open(p).read()
ok = 0

# runtime Stop matcher, added next to the Stop enum declaration
old_enum = """private enum Stop {"""
new_enum = """// DisappointingPlus local patch (hscript-stop-catch): Stop values must be
// matched by runtime type on hxcpp, whose typed enum catch wrongly grabs
// hscript.Error values thrown by real script errors.
function isHscriptStop( v : Dynamic ) : Bool {
	// hxcpp's enum type resolution collapses distinct enums (both the typed
	// catch and the type checks above report hscript.Error values as Stop),
	// but each value keeps its constructor name, which never collides.
	if( v == null )
		return false;
	// DisappointingPlus local patch (hscript-stop-safe-enum): hxcpp can
	// segfault inside Type.enumConstructor for an ordinary Dynamic object;
	// its try/catch cannot intercept that native fault. Only inspect enums.
	switch( Type.typeof(v) ) {
	case TEnum(_):
		try {
			var name : String = Type.enumConstructor(v);
			return name == 'SBreak' || name == 'SContinue' || name == 'SReturn';
		} catch( e : Dynamic ) {
			return false;
		}
	default:
		return false;
	}
}

private enum Stop {"""
if old_enum in s:
    s = s.replace(old_enum, new_enum); ok += 1

# exprReturn: a non-Stop must propagate to the caller, not fall through.
old_exprreturn = """		} catch( e : Stop ) {
			switch( e ) {
			case SBreak: throw "Invalid break";
			case SContinue: throw "Invalid continue";
			case SReturn:
				var v = returnValue;
				returnValue = null;
				return v;
			}
		}"""
new_exprreturn = """		} catch( e : Dynamic ) {
			// DisappointingPlus local patch (hscript-stop-catch): rethrow
			// genuine script errors instead of silently ignoring them.
			if( !isHscriptStop(e) )
				throw e;
			switch( e ) {
			case SBreak: throw "Invalid break";
			case SContinue: throw "Invalid continue";
			case SReturn:
				var v = returnValue;
				returnValue = null;
				return v;
			}
		}"""
if old_exprreturn in s:
    s = s.replace(old_exprreturn, new_exprreturn); ok += 1

# ETry: one dynamic catch; real Stop signals rethrow, script errors reach the
# catch block (previously the Stop catch swallowed script errors entirely).
old_etry = """			} catch( err : Stop ) {
				inTry = oldTry;
				throw err;
			} catch( err : Dynamic ) {
				// restore vars
				restore(old);
				inTry = oldTry;
				// declare 'v'
				declared.push({ n : n, old : locals.get(n) });
				locals.set(n,{ r : err });
				var v : Dynamic = expr(ecatch);
				restore(old);
				return v;
			}"""
new_etry = """			} catch( err : Dynamic ) {
				inTry = oldTry;
				// DisappointingPlus local patch (hscript-stop-catch): real
				// Stop signals (break/continue/return) keep unwinding;
				// hscript.Error values from script errors reach the catch
				// block, which the hxcpp typed enum catch wrongly swallowed.
				if( isHscriptStop(err) )
					throw err;
				// restore vars
				restore(old);
				// declare 'v'
				declared.push({ n : n, old : locals.get(n) });
				locals.set(n,{ r : err });
				var v : Dynamic = expr(ecatch);
				restore(old);
				return v;
			}"""
if old_etry in s:
    s = s.replace(old_etry, new_etry); ok += 1

# loops: a non-Stop must propagate to the script's own try/catch instead of
# degrading into a phantom break/continue.
old_loop = """			} catch( err : Stop ) {
				switch(err) {
				case SContinue:
				case SBreak: break;
				case SReturn: throw err;
				}
			}"""
new_loop = """			} catch( err : Dynamic ) {
				// DisappointingPlus local patch (hscript-stop-catch): genuine
				// script errors propagate to the script's own try/catch
				// instead of becoming a phantom break/continue on hxcpp.
				if( !isHscriptStop(err) )
					throw err;
				var stop : Stop = err;
				switch(stop) {
				case SContinue:
				case SBreak: break;
				case SReturn: throw err;
				}
			}"""
count = s.count(old_loop)
if count >= 2:
    s = s.replace(old_loop, new_loop)
    ok += count

old_forloop = """			} catch( err : Stop ) {
				switch( err ) {
				case SContinue:
				case SBreak: break;
				case SReturn: throw err;
				}
			}"""
new_forloop = """			} catch( err : Dynamic ) {
				// DisappointingPlus local patch (hscript-stop-catch): genuine
				// script errors propagate to the script's own try/catch
				// instead of becoming a phantom break/continue on hxcpp.
				if( !isHscriptStop(err) )
					throw err;
				var stop : Stop = err;
				switch(stop) {
				case SContinue:
				case SBreak: break;
				case SReturn: throw err;
				}
			}"""
if old_forloop in s:
    s = s.replace(old_forloop, new_forloop); ok += 1

if ok == 6:
    open(p, 'w').write(s)
    print('>> patched hscript Stop catches with runtime type checks (6 sites)')
else:
    open(p, 'w').write(s)
    print('!! hscript Stop-catch patch matched only %d/6 patterns - Interp.hx changed upstream?' % ok)
''',
    },
    {
        "name": 'safe Stop enum inspection upgrade',
        "mode": 'stop-upgrade',
        "marker": 'hscript-stop-safe-enum',
        "checks": ('hscript-stop-safe-enum',),
        "script": r'''
import sys
p = sys.argv[1]
s = open(p).read()
start = s.find("function isHscriptStop( v : Dynamic ) : Bool {")
end = s.find("\nprivate enum Stop {", start)
if start < 0 or end < 0:
    print('hscript safe-enum matcher patch could not find the old Stop helper', file=sys.stderr)
    sys.exit(1)
replacement = """function isHscriptStop( v : Dynamic ) : Bool {
	// hxcpp's enum type resolution collapses distinct enums (both the typed
	// catch and the type checks above report hscript.Error values as Stop),
	// but each value keeps its constructor name, which never collides.
	if( v == null )
		return false;
	// DisappointingPlus local patch (hscript-stop-safe-enum): hxcpp can
	// segfault inside Type.enumConstructor for an ordinary Dynamic object;
	// its try/catch cannot intercept that native fault. Only inspect enums.
	switch( Type.typeof(v) ) {
	case TEnum(_):
		try {
			var name : String = Type.enumConstructor(v);
			return name == 'SBreak' || name == 'SContinue' || name == 'SReturn';
		} catch( e : Dynamic ) {
			return false;
		}
	default:
		return false;
	}
}"""
s = s[:start] + replacement + s[end:]
open(p, 'w').write(s)
print('>> patched hscript Stop matcher to type-check Dynamics before enum inspection')
''',
    },

]


def should_run(step: dict[str, object], source: str) -> bool:
    mode = step["mode"]
    marker = step["marker"]
    if mode == "missing":
        return marker not in source
    if mode == "legacy-key":
        return marker in source
    if mode == "stop-upgrade":
        return "hscript-stop-catch" in source and marker not in source
    raise AssertionError(f"unknown hscript patch mode: {mode}")


def apply_patches(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"pinned hscript 2.5.0 Interp.hx was not found: {path}")

    for step in PATCH_STEPS:
        source = path.read_text(encoding="utf-8")
        name = step["name"]
        checks = step["checks"]
        missing = [needle for needle in checks if needle not in source]
        if missing and should_run(step, source):
            result = subprocess.run(
                [sys.executable, "-c", step["script"], str(path)],
                capture_output=True,
                text=True,
            )
            if result.stdout:
                sys.stdout.write(result.stdout)
            if result.stderr:
                sys.stderr.write(result.stderr)
            if result.returncode != 0:
                raise SystemExit(f"hscript patch failed ({name}, exit {result.returncode})")
            if "!!" in result.stdout or "!!" in result.stderr:
                raise SystemExit(f"hscript patch reported a source mismatch ({name})")
            source = path.read_text(encoding="utf-8")
            missing = [needle for needle in checks if needle not in source]
        if missing:
            raise SystemExit(
                f"hscript patch source mismatch ({name}); missing: " + ", ".join(missing)
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_INTERP,
                        help="Interp.hx path (defaults to pinned .haxelib source)")
    args = parser.parse_args()
    apply_patches(args.path)
    print(f">> applied/verified {len(PATCH_STEPS)} hscript 2.5.0 compatibility patches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
