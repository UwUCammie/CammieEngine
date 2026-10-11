"""Shared shader call reuse is bounded, pure, and independent of asset names."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]

class ShaderRepeatedCallOptimizerTest(unittest.TestCase):
    def test_safe_reuse_and_unsupported_semantics(self):
        fixture = r'''class Main {
 static function check(v:Bool,m:String):Void if(!v)throw m;
 static function main() {
  var source = '#define FACTOR 0.125\n'
   + 'float sampleGrid(int x,int y) { vec2 p=vec2(x,y); p += vec2(FACTOR); return fract(dot(p,p)); }\n'
   + 'float neighborhood(int x,int y) { return sampleGrid(x,y)/4.0 + sampleGrid(x+1,y)/4.0 + sampleGrid(x,y+1)/4.0 + sampleGrid(x+1,y+1)/4.0; }\n'
   + 'float shade(ivec2 cell) { float a=neighborhood(cell.x,cell.y); float b=neighborhood(cell.x+1,cell.y); return a+b; }';
  var result=ShaderRepeatedCallOptimizer.optimize(source);
  check(result!=source,'generic reuse did not match');
  check(result.split('float cammieSharedCall').length-1==6,'eight calls did not become six unique samples');
  check(result.indexOf('sampleGrid(cell.x + 2, cell.y + 1)')>=0,'integer offset composition incorrect');
  check(result.indexOf('/4.0 + ')>=0,'floating expression order changed');
  check(ShaderRepeatedCallOptimizer.optimize(result)==result,'rewrite not idempotent');
  var renamed=StringTools.replace(StringTools.replace(source,'sampleGrid','arbitraryLeaf'),'neighborhood','arbitraryWrapper');
  check(ShaderRepeatedCallOptimizer.optimize(renamed)!=renamed,'function name dependency');
  var negative=StringTools.replace(source,'cell.x+1','cell.x-1');
  var neg=ShaderRepeatedCallOptimizer.optimize(negative);
  check(neg!=negative && neg.indexOf('sampleGrid(cell.x - 1, cell.y)')>=0,'negative offsets not composed');
  var nested=StringTools.replace(source,'float a=','{ float a=');
  nested=StringTools.replace(nested,'return a+b; }','return a+b; }}');
  var nr=ShaderRepeatedCallOptimizer.optimize(nested);
  check(nr.indexOf('{ float cammieSharedCall')>=0,'declarations escaped lexical block');
  var collision='float cammieSharedCall0;\n'+source;
  check(ShaderRepeatedCallOptimizer.optimize(collision).indexOf('float cammieSharedCall0_ =')>=0,'generated name collision');
  var unsafe=[
   'float globalValue;\n'+StringTools.replace(source,'p += vec2(FACTOR);','globalValue += 1.0;'),
   'float globalValue;\n'+StringTools.replace(source,'vec2(FACTOR)','vec2(globalValue)'),
   StringTools.replace(source,'fract(dot(p,p))','dFdx(p.x)'),
   StringTools.replace(source,'fract(dot(p,p))','unknownCall(p)'),
   StringTools.replace(source,'int x,int y) { vec2','out int x,int y) { vec2'),
   StringTools.replace(source,'float b=','cell.x++; float b='),
   StringTools.replace(source,'cell.x+1','cell.x++'),
   StringTools.replace(source,'ivec2 cell','vec2 cell'),
   StringTools.replace(source,'cell.x+1','cell.x+1000'),
   StringTools.replace(source,'return sampleGrid(x,y)/4.0','return float(x)+sampleGrid(x,y)/4.0'),
   '#define sampleGrid(x,y) external(x,y)\n'+source,
   '#define fract(x) external(x)\n'+source,
   '#define cell hidden\n'+source,
   '#if ENABLED\n'+source+'\n#endif',
   '#undef FACTOR\n'+source,
   StringTools.replace(source,'float sampleGrid','highp float sampleGrid'),
   'precision mediump float;\n'+source,
   StringTools.replace(source,'float a=','precise float a='),
   '#define xy hidden\n'+StringTools.replace(source,'dot(p,p)','dot(p.xy,p)'),
   '#define return hidden\n'+source,
   StringTools.replace(source,'return sampleGrid(x,y)/4.0','return x>0 ? 0.0 : sampleGrid(x,y)/4.0'),
   source+'\nfloat sampleGrid(float x,float y){return x+y;}',
   StringTools.replace(source,'p += vec2(FACTOR);','if(p.x>0.0) p.x=0.0;'),
   StringTools.replace(source,'p += vec2(FACTOR);','discard;'),
   StringTools.replace(source,'p += vec2(FACTOR);','p.x = recursive(p.x);')+'\nfloat recursive(float v) {return recursive(v);}',
   StringTools.replace(source,'float b=neighborhood(cell.x+1,cell.y);','float b=neighborhood(cell.x+7,cell.y);')
  ];
  for(s in unsafe) check(ShaderRepeatedCallOptimizer.optimize(s)==s,'unsafe rewrite: '+s);
  var deep=StringTools.replace(source,'fract(dot(p,p))','chain0(p)');
  for(i in 0...40) deep+='\nfloat chain'+i+'(vec2 p) { return '+(i==39?'dot(p,p)':'chain'+(i+1)+'(p)')+'; }';
  check(ShaderRepeatedCallOptimizer.optimize(deep)==deep,'deep call graph should fall back');
  check(ShaderRepeatedCallOptimizer.optimize(null)==null,'null input');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            base=Path(directory)
            (base/'Main.hx').write_text(fixture,encoding='utf-8')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(base),'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__ == '__main__':
    unittest.main()
