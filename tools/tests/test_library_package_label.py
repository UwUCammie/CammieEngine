"""Package display labels remain separate from full owner and chart identities."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND
ROOT=Path(__file__).resolve().parents[2]

class PackageLabelTest(unittest.TestCase):
    def test_same_names_renames_filters_and_save_identity(self):
        body=r"""class Main {
 static function check(ok:Bool,message:String){if(!ok)throw message;}
 static function main(){
  var one='assets/imported_mods/psych-engine-mods-51a38873d6';
  var two='assets/imported_mods/psych-engine-segatendo-collection-d6dc626aab';
  var title='SEGATENDO COLLECTION';
  var a=LibraryPackageLabel.caption(one,title);var b=LibraryPackageLabel.caption(two,title);
  check(a!=b && a.indexOf(title)>0 && b.indexOf(title)>0,'same title remains ambiguous');
  check(LibraryPackageLabel.badge(one)==LibraryPackageLabel.badge('  '+one+'/ '),'trailing slash changed badge');
  check(LibraryPackageLabel.caption(one,'Renamed').indexOf(LibraryPackageLabel.badge(one))>=0,'rename changed badge');
  check(LibraryPackageLabel.caption('',title)==title && LibraryPackageLabel.badge(null)=='','base game received invented owner');
  check(LibraryPackageLabel.caption(one,title)==a,'filter/order affected display');
  check(LibraryPackageLabel.matches(one,LibraryPackageLabel.badge(one).toLowerCase()),'lowercase badge query failed');
  check(!LibraryPackageLabel.matches(two,LibraryPackageLabel.badge(one)),'badge matched different owner');
  check(!LibraryPackageLabel.isBadgeQuery('cafe cafe') && !LibraryPackageLabel.isBadgeQuery('abc'),'ordinary search classified as badge lookup');
  check(FreeplayBrowserLayout.label(a,24).indexOf(LibraryPackageLabel.badge(one))>=0,'bounded label cut disambiguator');
  var data=new UserLibraryData();var key=UserLibraryData.chartKey(one,'song');
  var category=data.createCategory('Same names');data.setMembership(category,one,true);data.setFavorite(key,true);
  var before=data.encode();LibraryPackageLabel.caption(one,title);LibraryPackageLabel.caption(two,title);
  for(i in 0...4100) LibraryPackageLabel.caption('assets/imported_mods/cache-'+i,title);
  check(LibraryPackageLabel.caption(one,title)==a,'cache turnover changed visible identity');
  check(data.encode()==before && data.hasMod(category,one) && !data.hasMod(category,two),'presentation changed category ownership');
  check(data.isFavorite(key) && !data.isFavorite(UserLibraryData.chartKey(two,'song')),'presentation merged favorites');
 }
}"""
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            (Path(temp)/'Main.hx').write_text(body)
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',temp,'--run','Main'],cwd=ROOT,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
if __name__=='__main__': unittest.main()
