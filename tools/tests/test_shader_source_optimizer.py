"""Conservative shader reductions preserve authored samples and observable loop values."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND

ROOT = Path(__file__).resolve().parents[2]

class ShaderSourceOptimizerTest(unittest.TestCase):
    def test_nearest_distance_reduction_and_unsafe_loops(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            base = Path(work)
            (base / 'Main.hx').write_text(r'''class Main {
 static function main() {
  var source = "float nearest(vec2 coord) { float dist = 1.0; for(int x=0;x<5;x++) { for(int y=0;y<5;y++) { vec2 point = vec2(x,y); dist = min(dist, distance(point, coord)); } } return dist; }";
  var output = ShaderSourceOptimizer.nearestDistance(source);
  if(output == source || output.indexOf("sqrt(cammieNearestSquared0)") < 0 || output.indexOf("dot(") < 0) throw "reduction missing";
  if(output.indexOf("x<5") < 0 || output.indexOf("y<5") < 0) throw "samples changed";
  if(ShaderSourceOptimizer.nearestDistance(output) != output) throw "not idempotent";
  var unsafe = [
   StringTools.replace(source, "1.0;", "-1.0;"),
   StringTools.replace(source, "1.0;", "1e-40;"),
   StringTools.replace(source, "dist = min", "if(dist < 0.5) break; dist = min"),
   StringTools.replace(source, "distance(point, coord)", "distance(nextPoint(), coord)"),
   "#define min(a,b) (a)\n" + source,
   "#define OBSERVE sample(dist)\n" + StringTools.replace(source,"vec2 point", "OBSERVE; vec2 point"),
   StringTools.replace(source, "vec2 point", "#if ENABLED\nvec2 point"),
   StringTools.replace(source, "float dist = 1.0", "float dist = cap"),
   StringTools.replace(source, "vec2 point", "vec3 point"),
   StringTools.replace(source, "dist = min", "other.dist = min"),
   StringTools.replace(source, "dist = min", "value = dist = min"),
   StringTools.replace(source, "dist = min(dist, distance(point, coord));", "for (dist = min(dist, distance(point, coord)); true;) break;"),
   "float distance(vec2 a, vec2 b) { return 0.5; }" + source
  ];
  for(candidate in unsafe) if(ShaderSourceOptimizer.nearestDistance(candidate) != candidate) throw "unsafe rewrite: " + candidate;
  // Independent reductions and local names must remain distinct.
  var twice = source + StringTools.replace(source,"nearest(","other(");
  var both = ShaderSourceOptimizer.nearestDistance(twice);
  if(both.indexOf("cammieNearestSquared1") < 0) throw "second reduction missing";
  var collision = "float cammieNearestSquared0;" + source;
  if(ShaderSourceOptimizer.nearestDistance(collision).indexOf("float cammieNearestSquared0_ =") < 0) throw "name collision";
 }
}''')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(base), '--run', 'Main'], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
