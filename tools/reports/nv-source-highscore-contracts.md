# Nightmare Vision owner highscore contract

Audit date: 2026-10-06
Donor: `fnf_sources/NightmareVision`, revision `733165c42ca71eb0961a70e4173b2d81ba4a29ea`, `source/funkin/data/Highscore.hx`.

`NightmareVisionHighscore` ports the donor's song and week score surface into an authenticated owner's save scope. The owner supplies its `CodenameOwnerSaveData` view as a `Dynamic` backend and typed callbacks for `Paths.sanitize` and `Difficulty.getDifficultyFilePath`. The service has no native `FlxG.save` reference or base-game `Highscore` alias.

The public `weekScores`, `songScores` and `songRating` fields are live `Map<String, Int>` / `Map<String, Float>` values. `formatSong` calls the path sanitizer first, then resolves the requested difficulty label and joins them with `-`. `saveScore` and `saveWeekScore` replace existing values only on a strict improvement. Ratings may be fractional; `saveScore` changes a rating only when the score improves and the provided rating is nonnegative. The donor defaults remain intact for reset/save methods. Missing score, week score or rating reads insert and persist zero through the same private setter used by writes.

The private `setScore`, `setWeekScore` and `setRating` methods stay reflected with `@:keep`. Each mutates its live map, writes the matching owner field name, then flushes the owner save. `resetSong` therefore flushes the score and rating separately in source order. `load()` reads `weekScores`, `songScores` and `songRating` in donor order; each non-null JSON-decoded map is cloned into a stable typed Haxe `Map`, while a null field leaves its current map reference unchanged. The JSON snapshot uses sorted key/value entries so arbitrary song keys remain data rather than object property names. Legacy plain JSON object maps also restore into typed maps.

The focused interpreter fixture covers callback order, method defaults, missing-value writes, strict improvement, fractional ratings, `resetSong`/`resetWeek`, reflected private writes, live map mutation, JSON cloning and reload pointer behavior. Run with:

```powershell
$env:PYTHONPATH='tools/tests'
python -m unittest test_nightmare_vision_highscore
```

Focused result: 2 tests passed. No build or full suite was run in this bounded service package.
