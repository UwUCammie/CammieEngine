from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import audit_script_api_coverage as audit_api


def write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


PSYCH_ACHIEVEMENT_LUA_NAMES = (
    "getAchievementScore", "setAchievementScore", "addAchievementScore",
    "unlockAchievement", "isAchievementUnlocked", "achievementExists",
)
PSYCH_LANGUAGE_LUA_NAMES = ("getTranslationPhrase", "getFileTranslation")
PSYCH_DISCORD_LUA_NAMES = ("changeDiscordPresence", "changeDiscordClientID")


def write_psych_achievement_donor(root: Path) -> None:
    write(root, "source/psychlua/FunkinLua.hx", '''
        class FunkinLua {
            public function new(scriptName:String) {
                #if ACHIEVEMENTS_ALLOWED Achievements.addLuaCallbacks(lua); #end
            }
        }
    ''')
    registrations = "\n".join(
        f"Lua_helper.add_callback(lua, '{name}', function() return null);"
        for name in PSYCH_ACHIEVEMENT_LUA_NAMES
    )
    write(root, "source/backend/Achievements.hx", f'''
        #if ACHIEVEMENTS_ALLOWED
        class Achievements {{
            #if LUA_ALLOWED
            public static function addLuaCallbacks(lua:State) {{
                {registrations}
            }}
            #end
        }}
        #end
    ''')
    write(root, "source/psychlua/HScript.hx", "set('Achievements', Achievements);\n")


def write_psych_achievement_engine(root: Path) -> None:
    write(root, "source/PlayState.hx", '''
        class PlayState {
            function makeHaxeState(plainPsych:Bool, translatedLua:Bool):Void {
                var interp:Dynamic = plainPsych ? PluginManager.addVarsToInterp(new SourceIrisBridge(this))
                    : translatedLua ? PluginManager.addVarsToInterp(new LuaCompatInterp()) : null;
                seedEngineCompat(interp, null);
            }
            function seedEngineCompat(interp:Dynamic, ?ownerRoot:String):Void {
                var runtime = new PsychRuntimeBindings(this, interp, 'chart.lua');
                runtime.install();
            }
        }
    ''')
    write(root, "source/PsychRuntimeBindings.hx", '''
        class PsychRuntimeBindings {
            function install():Void {
                if (Std.isOfType(owner, SourceIrisBridge)) installHscriptPreset(owner, null);
                else if (Std.isOfType(owner, LuaCompatInterp)) {
                    PsychAchievementsIntegration.installLua(host, owner, origin);
                    PsychStandardServices.installLua(host, owner, origin);
                }
                var run = function() return module();
            }
            function module():SourceIrisBridge {
                embedded = new SourceIrisBridge(host);
                installHscriptPreset(embedded, Std.isOfType(owner, LuaCompatInterp) ? owner : null);
                return embedded;
            }
            function installHscriptPreset(scope:Dynamic, parent:Dynamic):Void {
                new PsychHscriptSourceBindings(host, scope, origin, parent).install();
            }
        }
    ''')
    write(root, "source/PsychHscriptSourceBindings.hx", '''
        class PsychHscriptSourceBindings {
            function install():Void {
                PsychAchievementsIntegration.installHscript(host, interp, origin);
            }
        }
    ''')
    write(root, "source/PsychAchievementsIntegration.hx", '''
        class PsychAchievementsIntegration {
            function installLua(host:Dynamic, interp:Dynamic, origin:String):Void {
                var runtime = runtimeFor(host, interp.variables.get('Paths'), origin);
                if (runtime == null) return;
                PsychAchievementsLuaBindings.install(interp, runtime.service, report);
            }
            function installHscript(host:Dynamic, interp:Dynamic, origin:String):Void {
                if (!Std.isOfType(interp, SourceIrisBridge)) return;
                var runtime = runtimeFor(host, interp.variables.get('Paths'), origin);
                if (runtime == null) return;
                PsychAchievementsBindings.install((cast interp:SourceIrisBridge).evaluator,
                    runtime.service, function() requireRuntime(runtime));
            }
        }
    ''')
    lua_registrations = "\n".join(
        f"interp.variables.set('{name}', function() return null);"
        for name in PSYCH_ACHIEVEMENT_LUA_NAMES
    )
    write(root, "source/PsychAchievementsLuaBindings.hx", f'''
        class PsychAchievementsLuaBindings {{
            function install(interp:Dynamic, service:Dynamic, report:Dynamic):Void {{
                {lua_registrations}
            }}
        }}
    ''')
    write(root, "source/PsychAchievementsBindings.hx", '''
        class PsychAchievementsBindings {
            function install(interp:Dynamic, service:Dynamic, guard:Dynamic):Void {
                interp.variables.set('Achievements', service);
                interp.bindImport('backend.Achievements', service);
            }
        }
    ''')


def write_psych_standard_donor(root: Path) -> None:
    write(root, "source/psychlua/FunkinLua.hx", '''
        class FunkinLua {
            public function new(scriptName:String) {
                #if DISCORD_ALLOWED DiscordClient.addLuaCallbacks(lua); #end
                #if TRANSLATIONS_ALLOWED Language.addLuaCallbacks(lua); #end
            }
        }
    ''')
    for class_name, names in (
        ("Language", PSYCH_LANGUAGE_LUA_NAMES),
        ("DiscordClient", PSYCH_DISCORD_LUA_NAMES),
    ):
        registrations = "\n".join(
            f"Lua_helper.add_callback(lua, '{name}', function() return null);"
            for name in names
        )
        write(root, f"source/backend/{class_name}.hx", f'''
            class {class_name} {{
                #if LUA_ALLOWED
                public static function addLuaCallbacks(lua:State) {{
                    {registrations}
                }}
                #end
            }}
        ''')


def write_psych_standard_engine(root: Path) -> None:
    write(root, "source/PlayState.hx", '''
        class PlayState {
            function makeHaxeState(plainPsych:Bool, translatedLua:Bool):Void {
                var interp:Dynamic = plainPsych ? PluginManager.addVarsToInterp(new SourceIrisBridge(this))
                    : translatedLua ? PluginManager.addVarsToInterp(new LuaCompatInterp()) : null;
                seedEngineCompat(interp, null);
            }
            function seedEngineCompat(interp:Dynamic, ?ownerRoot:String):Void {
                var runtime = new PsychRuntimeBindings(this, interp, 'chart.lua');
                runtime.install();
            }
        }
    ''')
    write(root, "source/PsychRuntimeBindings.hx", '''
        class PsychRuntimeBindings {
            function install():Void {
                if (Std.isOfType(owner, SourceIrisBridge)) installHscriptPreset(owner, null);
                else if (Std.isOfType(owner, LuaCompatInterp)) {
                    PsychAchievementsIntegration.installLua(host, owner, origin);
                    PsychStandardServices.installLua(host, owner, origin);
                }
                var run = function() return module();
            }
            function module():SourceIrisBridge {
                embedded = new SourceIrisBridge(host);
                installHscriptPreset(embedded, Std.isOfType(owner, LuaCompatInterp) ? owner : null);
                return embedded;
            }
            function installHscriptPreset(scope:Dynamic, parent:Dynamic):Void {
                new PsychHscriptSourceBindings(host, scope, origin, parent).install();
            }
        }
    ''')
    write(root, "source/PsychHscriptSourceBindings.hx", '''
        class PsychHscriptSourceBindings {
            function install():Void {
                PsychStandardServices.installHscript(host, interp, origin);
            }
        }
    ''')
    write(root, "source/PsychStandardServices.hx", '''
        class PsychStandardServices {
            function installLua(host:PlayState, interp:Interp, origin:String):Void {
                var owner = runtimeFor(host, interp.variables.get('Paths'), origin);
                if (owner == null) return;
                PsychLanguageBindings.installLua(interp, owner.language);
                PsychDiscordBindings.installLua(interp, owner.discord);
            }
            function installHscript(host:PlayState, interp:Interp, origin:String):Void {
                if (!Std.isOfType(interp, SourceIrisBridge)) return;
                var owner = runtimeFor(host, interp.variables.get('Paths'), origin);
                if (owner == null) return;
                var evaluator = (cast interp:SourceIrisBridge).evaluator;
                PsychLanguageBindings.install(evaluator, owner.language);
                PsychDiscordBindings.install(evaluator, owner.discord);
            }
        }
    ''')
    write(root, "source/PsychLanguageBindings.hx", '''
        class PsychLanguageBindings {
            function install(interp:Dynamic, runtime:Dynamic):Void {
                interp.variables.set('Language', type);
                interp.bindImport('backend.Language', type);
            }
            function installLua(interp:Dynamic, runtime:Dynamic):Void {
                interp.variables.set('getTranslationPhrase', callback);
                interp.variables.set('getFileTranslation', callback);
            }
        }
    ''')
    write(root, "source/PsychDiscordBindings.hx", '''
        class PsychDiscordBindings {
            function install(interp:Dynamic, facade:Dynamic):Void {
                interp.variables.set('DiscordClient', type);
                interp.bindImport('backend.DiscordClient', type);
            }
            function installLua(interp:Dynamic, facade:Dynamic):Void {
                interp.variables.set('changeDiscordPresence', callback);
                interp.variables.set('changeDiscordClientID', callback);
            }
        }
    ''')


class ScriptApiCoverageAuditTests(unittest.TestCase):
    def test_psych_inventory_ignores_comments_and_string_examples(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, "source/psychlua/FunkinLua.hx", '''
                Lua_helper.add_callback(lua, "makeThing", function() {});
                funk.addLocalCallback("localThing", function() {});
                addLocalCallback('moduleHelper', function() {});
                // Lua_helper.add_callback(lua, "commentOnly", function() {});
                var docs = "Lua_helper.add_callback(lua, 'stringOnly', fn)";
            ''')
            write(root, "source/psychlua/HScript.hx", '''
                set('helper', function(x:Int) return x);
                set("FlxSprite", flixel.FlxSprite);
                // set("commentOnly", Function);
                var docs = "set('stringOnly', value)";
            ''')
            write(root, "source/states/PlayState.hx", '''
                callOnScripts('onUpdate', [elapsed]);
                newScript.call('onCreate');
                // callOnLuas('commentOnly');
            ''')

            entries = audit_api._psych_donor_entries(root)
            names = {(entry.group, entry.name): entry for entry in entries}
            self.assertEqual(set(names), {
                ("registered functions", "makeThing"),
                ("registered functions", "localThing"),
                ("registered functions", "moduleHelper"),
                ("seeded globals", "helper"),
                ("seeded globals", "FlxSprite"),
                ("dispatched callbacks", "onUpdate"),
                ("dispatched callbacks", "onCreate"),
            })
            self.assertEqual(names[("seeded globals", "helper")].kind, "function")
            self.assertEqual(names[("seeded globals", "FlxSprite")].kind, "class/value")
            self.assertEqual(names[("registered functions", "makeThing")].source[0].line, 2)

    def test_psych_inventory_follows_only_reachable_lua_callback_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, "source/psychlua/FunkinLua.hx", '''
                package psychlua;
                import backend.Achievements;
                class FunkinLua {
                    public function new(scriptName:String) {
                        #if ACHIEVEMENTS_ALLOWED Achievements.addLuaCallbacks(lua); #end
                    }
                }
            ''')
            write(root, "source/backend/Achievements.hx", '''
                package backend;
                #if ACHIEVEMENTS_ALLOWED
                class Achievements {
                    #if LUA_ALLOWED
                    public static function addLuaCallbacks(lua:State) {
                        Lua_helper.add_callback(lua, "getAchievementScore", function(name:String) return 0);
                        Lua_helper.add_callback(lua, "setAchievementScore", function(name:String) return 0);
                        Lua_helper.add_callback(lua, "addAchievementScore", function(name:String) return 0);
                        Lua_helper.add_callback(lua, "unlockAchievement", function(name:String) return null);
                        Lua_helper.add_callback(lua, "isAchievementUnlocked", function(name:String) return false);
                        Lua_helper.add_callback(lua, "achievementExists", function(name:String) return false);
                    }
                    #end
                }
                #end
            ''')
            write(root, "source/backend/UnusedCallbacks.hx", '''
                class UnusedCallbacks {
                    #if LUA_ALLOWED
                    public static function addLuaCallbacks(lua:State) {
                        Lua_helper.add_callback(lua, "notRegistered", function() return null);
                    }
                    #end
                }
            ''')

            expected = {
                "getAchievementScore", "setAchievementScore", "addAchievementScore",
                "unlockAchievement", "isAchievementUnlocked", "achievementExists",
            }
            entries = audit_api._psych_donor_entries(root)
            callbacks = {
                entry.name: entry for entry in entries
                if entry.dialect == "Psych Lua" and entry.group == "registered functions"
                and entry.name in expected
            }
            self.assertEqual(set(callbacks), expected)
            for name, entry in callbacks.items():
                self.assertEqual(entry.source[0].path, "source/backend/Achievements.hx")
                self.assertEqual(entry.source[1].path, "source/backend/Achievements.hx")
                self.assertEqual(entry.source[2].path, "source/psychlua/FunkinLua.hx")
                self.assertEqual(entry.contract["registration_conditions"],
                                 ["ACHIEVEMENTS_ALLOWED", "LUA_ALLOWED"])
                self.assertEqual(entry.contract["registration_chain"][0]["source"],
                                 {"path": "source/psychlua/FunkinLua.hx", "line": 6})
            self.assertNotIn("notRegistered", {entry.name for entry in entries})
            audit_api._build_contract_inventory(
                entries,
                {"Psych Lua": root, "Psych HScript": root, "Psych chart hooks": root},
                root,
            )
            self.assertEqual(callbacks["getAchievementScore"].contract["registration_conditions"],
                             ["ACHIEVEMENTS_ALLOWED", "LUA_ALLOWED"])
            self.assertEqual(callbacks["getAchievementScore"].contract["registration_chain"][0]["source"],
                             {"path": "source/psychlua/FunkinLua.hx", "line": 6})

            # A matching helper declaration is not donor API evidence unless
            # the actual constructor calls it under the achievement define.
            write(root, "source/psychlua/FunkinLua.hx", '''
                class FunkinLua {
                    public function new(scriptName:String) {
                        #if TRANSLATIONS_ALLOWED Achievements.addLuaCallbacks(lua); #end
                    }
                }
            ''')
            self.assertFalse(expected.intersection(
                entry.name for entry in audit_api._psych_donor_entries(root)
                if entry.dialect == "Psych Lua"
            ))

            write(root, "source/psychlua/FunkinLua.hx", '''
                class FunkinLua {
                    public function new(scriptName:String) {
                        #if ACHIEVEMENTS_ALLOWED Achievements.addLuaCallbacks(lua); #end
                    }
                }
            ''')
            achievements = root / "source" / "backend" / "Achievements.hx"
            achievements.write_text(
                achievements.read_text(encoding="utf-8").replace("#if LUA_ALLOWED", ""),
                encoding="utf-8",
            )
            self.assertFalse(expected.intersection(
                entry.name for entry in audit_api._psych_donor_entries(root)
                if entry.dialect == "Psych Lua"
            ))

            write(root, "source/psychlua/FunkinLua.hx", '''
                class FunkinLua {
                    public function new(scriptName:String) {
                        // #if ACHIEVEMENTS_ALLOWED Achievements.addLuaCallbacks(lua); #end
                    }
                }
            ''')
            self.assertFalse(expected.intersection(
                entry.name for entry in audit_api._psych_donor_entries(root)
                if entry.dialect == "Psych Lua"
            ))

    def test_nightmare_vision_inventory_keeps_its_script_dialect(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, "source/funkin/scripts/FunkinScript.hx", '''
                set('FlxG', flixel.FlxG);
                set("setVar", (name:String, value:Dynamic) -> value);
            ''')
            write(root, "source/funkin/states/PlayState.hx", '''
                class PlayState {
                    var chartField:Int = 1;
                    private var privateField:Int = 2;
                    scripts.call('onBeatHit', []);
                    script.call('onLoad');
                    public function setNightmareValue(name:String):Void {}
                }
            ''')
            write(root, "source/funkin/scripting/ScriptedState.hx", "scriptGroup.call('onCreate');\n")

            entries = audit_api._nv_donor_entries(root)
            names = {(entry.group, entry.name): entry for entry in entries}
            self.assertIn(("seeded globals", "FlxG"), names)
            self.assertEqual(names[("seeded globals", "setVar")].kind, "function")
            self.assertIn(("dispatched callbacks", "onBeatHit"), names)
            self.assertIn(("dispatched callbacks", "onLoad"), names)
            self.assertIn(("dispatched callbacks", "onCreate"), names)
            self.assertIn(("PlayState member surface", "setNightmareValue"), names)
            self.assertIn(("PlayState member surface", "chartField"), names)
            self.assertNotIn(("PlayState member surface", "privateField"), names)
            self.assertFalse(any(entry.dialect == "Psych Lua" for entry in entries))

    def test_coverage_states_require_direct_bindings_for_implemented(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, "source/PlayState.hx", '''
                interp.variables.set('boundApi', function() {});
                public function namedOnlyApi():Void {}
                // missingApi occurs in a comment only
                var note = "stringOnly";
            ''')
            entries = [
                audit_api.ApiEntry("Psych HScript", "seeded globals", name, "value")
                for name in ("boundApi", "namedOnlyApi", "missingApi", "stringOnly")
            ]
            direct, mentions, dynamic, _ = audit_api._engine_inventory(root, {entry.name for entry in entries})
            audit_api._apply_statuses(entries, root, direct, mentions, dynamic)
            self.assertEqual({entry.name: entry.status for entry in entries}, {
                "boundApi": "implemented",
                "namedOnlyApi": "names-only",
                "missingApi": "missing",
                "stringOnly": "missing",
            })

    def test_source_versions_and_callback_alias_maps_are_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, "source/PlayState.hx", "class PlayState {}\n")
            write(root, "source/states/MainMenuState.hx",
                  "class MainMenuState { public static var psychEngineVersion:String = '1.0.4'; }\n")
            write(root, "Project.xml", '<project><app version="0.2.8" /></project>\n')
            metadata = audit_api._metadata(root, "Psych Engine")
            self.assertEqual(metadata.version, "Psych Engine 1.0.4 / project 0.2.8")

            write(root, "source/EngineCompat.hx", '''
                class EngineCompat {
                    static function callbackNames(name:String):Array<String> {
                        switch (name.toLowerCase()) {
                            case 'recalculaterating': appendName(result, 'onRecalculateRating');
                        }
                    }
                    static function unrelated():Void appendName(result, 'notAChartHook');
                }
            ''')
            write(root, "source/PsychRuntimeBindings.hx", '''
                class PsychRuntimeBindings {
                    function install():Void {
                        for (kind in ['Scripts', 'Luas', 'HScript']) {
                            var family = kind;
                            owner.variables.set('callOn' + family, function() {});
                        }
                    }
                }
            ''')
            write(root, "source/PlayState.hx", "class PlayState { function dispatch():Void callAllHScript('recalculateRating', []); }\n")
            entries = [
                audit_api.ApiEntry("Psych chart hooks", "dispatched callbacks", "onRecalculateRating", "callback"),
            ]
            direct, mentions, dynamic, _ = audit_api._engine_inventory(root, {entry.name for entry in entries})
            audit_api._apply_statuses(entries, root, direct, mentions, dynamic)
            self.assertEqual(entries[0].status, "implemented")
            self.assertNotIn("@psych-hook:notAChartHook", direct)
            self.assertTrue({"callOnScripts", "callOnLuas", "callOnHScript"}.issubset(direct))
            aliases = audit_api._callback_alias_inventory(root)
            self.assertEqual(aliases, [{
                "host_callback_spellings": ["recalculaterating"],
                "script_callback_spellings": ["onRecalculateRating"],
                "source": {"path": "source/EngineCompat.hx", "line": 5},
                "append_sites": [{"path": "source/EngineCompat.hx", "line": 5}],
                "evidence_kind": "literal-callbackNames-branch",
                "behavioral_verification": "unverified",
            }])

    def test_callback_alias_requires_a_dispatched_host_spelling(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, "source/EngineCompat.hx", '''
                class EngineCompat {
                    static function callbackNames(name:String):Array<String> {
                        switch (name.toLowerCase()) {
                            case 'recalculaterating': appendName(result, 'onRecalculateRating');
                        }
                    }
                }
            ''')
            write(root, "source/PlayState.hx", "class PlayState {}\n")
            entry = audit_api.ApiEntry(
                "Psych chart hooks", "dispatched callbacks", "onRecalculateRating", "callback"
            )
            direct, mentions, dynamic, _ = audit_api._engine_inventory(root, {entry.name})
            audit_api._apply_statuses([entry], root, direct, mentions, dynamic)
            self.assertEqual(entry.status, "names-only")

    def test_nightmare_vision_parent_surface_is_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, "source/PlayState.hx", '''
                class PlayState {
                    public function reflectedMember():Void {}
                    static function seedNightmareVisionCommon(interp:Dynamic):Void {
                        var preset:Map<String, Dynamic> = ['PlayState' => PlayState];
                    }
                    function seedNightmareVision(interp:Dynamic):Void {
                        interp.bindClassParent(PlayState);
                        interp.variables.set('game', this);
                    }
                }
            ''')
            write(root, "source/NightmareVisionScriptInterp.hx", '''
                class NightmareVisionScriptInterp {
                    var classParents:Array<Dynamic> = [];
                    public function bindClassParent(type:Dynamic):Void classParents.push({type:type});
                    public function usesClassParent(type:Dynamic):Bool return classParents.length > 0;
                    public function resolve(name:String):Dynamic return Type.getClassFields(PlayState);
                }
            ''')
            entry = audit_api.ApiEntry(
                "Nightmare Vision chart state", "PlayState member surface", "reflectedMember", "reflective member"
            )
            direct, mentions, dynamic, _ = audit_api._engine_inventory(root, {entry.name})
            audit_api._apply_statuses([entry], root, direct, mentions, dynamic)
            self.assertEqual(entry.status, "unverified")
            evidence = audit_api._nightmare_vision_reflection_evidence(root)
            self.assertEqual(evidence["status"], "dynamic-path-present-unverified")
            self.assertEqual({item["name"] for item in evidence["seed_aliases"]}, {"game", "PlayState"})
            self.assertIsNotNone(evidence["class_parent"])

    def test_nightmare_vision_spawn_callbacks_and_dynamic_sites_are_found(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            donor = root / "donor"
            write(donor, "source/funkin/states/PlayState.hx", '''
                class PlayState {
                    function spawn(note:Dynamic):Void {
                        scripts.call('onSpawnNote', [note], false, [note.noteType]);
                        scripts.call('onSpawnNotePost', [note], false, [note.noteType]);
                        var result = script.call(event, args)?.returnValue;
                    }
                }
            ''')
            write(root, "source/PlayState.hx", '''
                class PlayState {
                    function spawn(note:Dynamic):Void {
                        nightmareVisionScripts.call('onSpawnNote', [note], false, [note.noteType]);
                        nightmareVisionScripts.call('onSpawnNotePost', [note], false, [note.noteType]);
                        var result = nightmareVisionScripts.call(callbackName, args);
                        callNightmareVision(event, args);
                    }
                }
            ''')
            entries = audit_api._nv_donor_entries(donor)
            donor_roots = {"Nightmare Vision HScript": donor, "Nightmare Vision chart state": donor}
            engine_entries = [
                audit_api.ApiEntry("Nightmare Vision HScript", "dispatched callbacks", name, "callback")
                for name in ("onSpawnNote", "onSpawnNotePost")
            ]
            engine_entries.extend(
                audit_api.ApiEntry("Psych chart hooks", "dispatched callbacks", name, "callback")
                for name in ("onSpawnNote", "onSpawnNotePost")
            )
            direct, mentions, dynamic, _ = audit_api._engine_inventory(root, {entry.name for entry in engine_entries})
            audit_api._apply_statuses(engine_entries, root, direct, mentions, dynamic)
            self.assertEqual([entry.status for entry in engine_entries], ["implemented", "implemented", "missing", "missing"])

            donor_dynamic = audit_api._build_contract_inventory(entries, donor_roots, root)
            unresolved_donor = [site for site in donor_dynamic if site["name_resolution"] == "dynamic-expression"]
            self.assertTrue(any(site["callback_expression"] == "event" for site in unresolved_donor))
            engine_dynamic = audit_api._dynamic_dispatch_sites(root)
            self.assertTrue(any(site["callback_expression"] == "callbackName" for site in engine_dynamic))
            self.assertTrue(any(site["callback_expression"] == "event" for site in engine_dynamic))

    def test_psych_dispatch_routes_resolve_aliases_and_report_dynamic_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, "source/PlayState.hx", '''
                class PlayState {
                    function dispatch(playerOne:Bool):Void {
                        callAllHScript(playerOne ? 'goodNoteHit' : 'opponentNoteHit', [note]);
                        callAllHScript(callbackName, [elapsed]);
                    }
                }
            ''')
            write(root, "source/EngineCompat.hx", '''
                class EngineCompat {
                    static function callbackNames(name:String):Array<String> {
                        switch (name.toLowerCase()) {
                            case 'recalculaterating': appendName(result, 'onRecalculateRating');
                        }
                    }
                }
            ''')
            entries = [
                audit_api.ApiEntry("Psych chart hooks", "dispatched callbacks", name, "callback")
                for name in ("goodNoteHit", "opponentNoteHit")
            ]
            direct, mentions, dynamic, _ = audit_api._engine_inventory(root, {entry.name for entry in entries})
            audit_api._apply_statuses(entries, root, direct, mentions, dynamic)
            self.assertEqual([entry.status for entry in entries], ["implemented", "implemented"])
            sites = audit_api._dynamic_dispatch_sites(root)
            ternary = next(site for site in sites if site["receiver"] == "callAllHScript" and "?" in site["callback_expression"])
            self.assertEqual(ternary["literal_callback_choices"], ["goodNoteHit", "opponentNoteHit"])
            unresolved = next(site for site in sites if site["callback_expression"] == "callbackName")
            self.assertEqual(unresolved["name_resolution"], "dynamic-unresolved")

    def test_psych_runtime_dispatcher_counts_literal_and_wired_pre_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, "source/PsychRuntimeBindings.hx", '''
                class PsychRuntimeBindings {
                    public static function dispatch(host:PlayState, name:String,
                        args:Array<Dynamic>, family:String = 'Scripts'):Dynamic {
                        return dispatchScopes(host, name, args, family);
                    }
                }
            ''')
            write(root, "source/PlayState.hx", '''
                class PlayState {
                    function dispatchPsychNoteSpawn(note:Note):Void {
                        PsychRuntimeBindings.dispatch(this, 'onSpawnNote', [note], 'HScript');
                    }
                    function dispatchPsychNoteHitPre(note:Note, playerOne:Bool):Bool {
                        var callback = playerOne ? 'goodNoteHitPre' : 'opponentNoteHitPre';
                        var result = PsychRuntimeBindings.dispatch(this, callback, [note], 'Luas');
                        return result != STOP;
                    }
                    function goodNoteHit(note:Note):Void {
                        dispatchPsychNoteHitPre(note, true);
                    }
                    function dispatchHxcAutoNoteHit(note:Note):Void {
                        dispatchPsychNoteHitPre(note, true);
                    }
                    function notifySourceCountdownStarted():Void {
                        PsychRuntimeBindings.dispatch(this, 'onCountdownStarted', []);
                    }
                    function startCountdown():Void {
                        PsychRuntimeBindings.dispatch(this, 'onStartCountdown', []);
                        notifySourceCountdownStarted();
                    }
                }
            ''')
            names = (
                "onSpawnNote", "goodNoteHitPre", "opponentNoteHitPre",
                "onCountdownStarted", "onStartCountdown",
            )
            entries = [audit_api.ApiEntry("Psych chart hooks", "dispatched callbacks", name, "callback")
                       for name in names]
            direct, mentions, dynamic, _ = audit_api._engine_inventory(root, set(names))
            audit_api._apply_statuses(entries, root, direct, mentions, dynamic)
            self.assertEqual([entry.status for entry in entries], ["implemented"] * len(names))

            sites = audit_api._dynamic_dispatch_sites(root)
            pre_site = next(site for site in sites
                            if site["receiver"] == "PsychRuntimeBindings.dispatch")
            self.assertEqual(pre_site["callback_expression"], "callback")
            self.assertEqual(pre_site["literal_callback_choices"], ["goodNoteHitPre", "opponentNoteHitPre"])
            self.assertEqual(pre_site["name_resolution"], "dynamic-with-literal-alternatives")
            for callback in ("goodNoteHitPre", "opponentNoteHitPre"):
                refs = direct["@psych-hook:" + callback]
                self.assertTrue(any(ref.path == "source/PlayState.hx" and ref.line == 8 for ref in refs))
                self.assertTrue(any(ref.path == "source/PlayState.hx" and ref.line in (12, 15) for ref in refs))

    def test_psych_post_hit_adapter_requires_the_installed_hit_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, "source/PsychRuntimeBindings.hx", '''
                class PsychRuntimeBindings {
                    public static function dispatch(host:PlayState, name:String,
                        args:Array<Dynamic>, family:String = 'Scripts'):Dynamic {
                        return dispatchScopes(host, name, args, family);
                    }
                }
            ''')
            write(root, "source/PlayState.hx", '''
                class PlayState {
                    function dispatchPsychNoteHit(note:Note, playerOne:Bool):Void {
                        var callback = playerOne ? 'goodNoteHit' : 'opponentNoteHit';
                        PsychNoteCallbacks.dispatch(callback, note, 0, 0,
                            function(name, args, family) return PsychRuntimeBindings.dispatch(this, name, args, family), null);
                    }
                    function finishGoodNoteHit(note:Note, playerOne:Bool):Void {
                        var psychSource = sourceScoreLedgerActive() && !sourceScoreNightmare;
                        if (psychSource) dispatchPsychNoteHit(note, playerOne);
                    }
                    function goodNoteHit(note:Note):Void finishGoodNoteHit(note, true);
                    function dispatchHxcAutoNoteHit(note:Note):Void finishGoodNoteHit(note, true);
                }
            ''')
            names = {"goodNoteHit", "opponentNoteHit"}
            entries = [audit_api.ApiEntry("Psych chart hooks", "dispatched callbacks", name, "callback")
                       for name in sorted(names)]
            direct, mentions, dynamic, _ = audit_api._engine_inventory(root, names)
            audit_api._apply_statuses(entries, root, direct, mentions, dynamic)
            self.assertEqual({entry.name: entry.status for entry in entries}, {
                "goodNoteHit": "implemented", "opponentNoteHit": "implemented",
            })
            for name in names:
                refs = direct["@psych-hook:" + name]
                self.assertGreaterEqual(len(refs), 3)
                self.assertTrue(all(ref.path == "source/PlayState.hx" for ref in refs))
            post_site = next(site for site in audit_api._dynamic_dispatch_sites(root)
                             if site["receiver"] == "PsychRuntimeBindings.dispatch")
            self.assertEqual(post_site["literal_callback_choices"], ["goodNoteHit", "opponentNoteHit"])
            self.assertEqual(post_site["name_resolution"], "dynamic-with-literal-alternatives")

            # A disconnected helper remains unresolved even when it uses the
            # same callback-name ternary and runtime bridge.
            write(root, "source/PlayState.hx", '''
                class PlayState {
                    function dispatchPsychNoteHit(note:Note, playerOne:Bool):Void {
                        var callback = playerOne ? 'goodNoteHit' : 'opponentNoteHit';
                        PsychNoteCallbacks.dispatch(callback, note, 0, 0,
                            function(name, args, family) return PsychRuntimeBindings.dispatch(this, name, args, family), null);
                    }
                }
            ''')
            entries = [audit_api.ApiEntry("Psych chart hooks", "dispatched callbacks", name, "callback")
                       for name in sorted(names)]
            direct, mentions, dynamic, _ = audit_api._engine_inventory(root, names)
            audit_api._apply_statuses(entries, root, direct, mentions, dynamic)
            self.assertEqual([entry.status for entry in entries], ["missing", "missing"])

    def test_gameover_substate_routes_keep_source_mode_dialects_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            psych = root / "psych-donor"
            nv = root / "nv-donor"
            write(root, "source/PsychRuntimeBindings.hx", '''
                class PsychRuntimeBindings {
                    public static function dispatch(host:PlayState, name:String,
                        args:Array<Dynamic>, family:String = 'Scripts'):Dynamic {
                        return dispatchScopes(host, name, args, family);
                    }
                }
            ''')
            write(root, "source/PlayState.hx", '''
                class PlayState {
                    public function sourceGameOverMode():Int
                        return !sourceScoreOwner ? 0 : sourceScoreNightmare ? 2 : 1;
                    function sourceGameOverCall(callback:String, args:Array<Dynamic>):Dynamic {
                        if (!sourceScoreOwner) return null;
                        if (sourceScoreNightmare) return callNightmareVision(callback, args);
                        return PsychRuntimeBindings.dispatch(this, callback, args);
                    }
                    function callNightmareVision(event:String, args:Array<Dynamic>):Dynamic {
                        return nightmareVisionScripts.call(event, args);
                    }
                }
            ''')
            write(root, "source/GameOverSubstate.hx", '''
                class GameOverSubstate {
                    function psychCalls(owner:PlayState):Void {
                        if (sourceMode == 1) owner.sourceGameOverCall('onGameOverStart', []);
                        if (sourceMode == 1) owner.sourceGameOverCall('onGameOverConfirm', [false]);
                    }
                    function nvCalls(owner:PlayState):Void {
                        if (sourceMode == 2) owner.sourceGameOverCall('onGameOverPost', []);
                        if (sourceMode == 2) owner.sourceGameOverCall('onGameOverCancel', []);
                    }
                    function ambiguous(owner:PlayState):Void {
                        owner.sourceGameOverCall('unscopedCallback', []);
                        if (sourceMode == 1) owner.sourceGameOverCall('laterPsychOnly', []);
                        // owner.sourceGameOverCall('commentOnly', []);
                        var docs = "owner.sourceGameOverCall('stringOnly', [])";
                    }
                }
            ''')
            write(psych, "source/substates/GameOverSubstate.hx", '''
                class GameOverSubstate {
                    function scripts():Void {
                        callOnScripts('onGameOverStart', []);
                        callOnScripts('onGameOverConfirm', [false]);
                        callOnScripts('onGameOverPost', []);
                        callOnScripts('laterPsychOnly', []);
                    }
                }
            ''')
            write(nv, "source/funkin/states/substates/GameOverSubstate.hx", '''
                class GameOverSubstate {
                    function scripts():Void {
                        scripts.call('onGameOverPost', []);
                        scripts.call('onGameOverCancel', []);
                        scripts.call('unscopedCallback', []);
                    }
                }
            ''')

            entries = audit_api._psych_donor_entries(psych) + audit_api._nv_donor_entries(nv)
            names = {entry.name for entry in entries}
            direct, mentions, dynamic, _ = audit_api._engine_inventory(root, names)
            audit_api._apply_statuses(entries, root, direct, mentions, dynamic)
            by_dialect = {(entry.dialect, entry.name): entry for entry in entries}
            self.assertEqual(by_dialect[("Psych chart hooks", "onGameOverStart")].status, "implemented")
            self.assertEqual(by_dialect[("Psych chart hooks", "onGameOverConfirm")].status, "implemented")
            self.assertEqual(by_dialect[("Psych chart hooks", "onGameOverPost")].status, "missing")
            self.assertEqual(by_dialect[("Psych chart hooks", "laterPsychOnly")].status, "implemented")
            self.assertEqual(by_dialect[("Nightmare Vision HScript", "onGameOverPost")].status, "implemented")
            self.assertEqual(by_dialect[("Nightmare Vision HScript", "onGameOverCancel")].status, "implemented")
            self.assertEqual(by_dialect[("Nightmare Vision HScript", "unscopedCallback")].status, "missing")
            sites = audit_api._dynamic_dispatch_sites(root)
            gameover_sites = [site for site in sites if site["receiver"] == "sourceGameOverCall"]
            self.assertTrue(gameover_sites)
            self.assertTrue(all(site["behavioral_verification"] == "unverified" for site in gameover_sites))
            self.assertFalse(any("commentOnly" in site["literal_callback_choices"]
                                 or "stringOnly" in site["literal_callback_choices"] for site in sites))

    def test_psych_runtime_dispatch_does_not_promote_unwired_or_arbitrary_names(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, "source/PsychRuntimeBindings.hx", '''
                class PsychRuntimeBindings {
                    public static function dispatch(host:PlayState, name:String,
                        args:Array<Dynamic>, family:String = 'Scripts'):Dynamic {
                        return dispatchScopes(host, name, args, family);
                    }
                }
            ''')
            write(root, "source/PlayState.hx", '''
                class PlayState {
                    function dispatchPsychNoteSpawn(note:Note):Void {
                        PsychRuntimeBindings.dispatch(this, 'onSpawnNote', [note], 'HScript');
                    }
                    function unusedHitPre(note:Note, playerOne:Bool):Void {
                        var callback = playerOne ? 'goodNoteHitPre' : 'opponentNoteHitPre';
                        PsychRuntimeBindings.dispatch(this, callback, [note], 'Luas');
                    }
                    function unrelated(note:Note, enabled:Bool):Void {
                        var callback = enabled ? 'madeUpCallback' : 'anotherMadeUpCallback';
                        PsychRuntimeBindings.dispatch(this, callback, [note]);
                    }
                }
            ''')
            names = {"onSpawnNote", "goodNoteHitPre", "opponentNoteHitPre",
                     "madeUpCallback", "anotherMadeUpCallback"}
            entries = [audit_api.ApiEntry("Psych chart hooks", "dispatched callbacks", name, "callback")
                       for name in sorted(names)]
            direct, mentions, dynamic, _ = audit_api._engine_inventory(root, names)
            audit_api._apply_statuses(entries, root, direct, mentions, dynamic)
            self.assertEqual({entry.name: entry.status for entry in entries}, {
                "onSpawnNote": "implemented",
                "goodNoteHitPre": "missing",
                "opponentNoteHitPre": "missing",
                "madeUpCallback": "missing",
                "anotherMadeUpCallback": "missing",
            })

            # A same-named but non-public dispatcher is not a wired source route.
            write(root, "source/PsychRuntimeBindings.hx", '''
                class PsychRuntimeBindings {
                    static function dispatch(host:PlayState, name:String,
                        args:Array<Dynamic>, family:String = 'Scripts'):Dynamic {
                        return dispatchScopes(host, name, args, family);
                    }
                }
            ''')
            direct, mentions, dynamic, _ = audit_api._engine_inventory(root, {"onSpawnNote"})
            entry = audit_api.ApiEntry("Psych chart hooks", "dispatched callbacks", "onSpawnNote", "callback")
            audit_api._apply_statuses([entry], root, direct, mentions, dynamic)
            self.assertEqual(entry.status, "missing")

    def test_ghost_miss_callback_is_conditional_alias_not_nv_route(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, "source/EngineCompat.hx", '''
                class EngineCompat {
                    static function canonicalCallback(name:String):String return name == 'noteMiss' ? 'noteMiss' : name;
                    static function psychMissPressArguments(name:String, args:Array<Dynamic>):Null<Array<Dynamic>> {
                        if (canonicalCallback(name) != 'noteMiss' || args[0] != null) return null;
                        return [args[2]];
                    }
                }
            ''')
            write(root, "source/PlayState.hx", '''
                class PlayState {
                    function callHscript(func_name:String, args:Array<Dynamic>):Void {
                        var pressArgs = EngineCompat.psychMissPressArguments(func_name, args);
                        if (pressArgs != null) {
                            func_name = 'noteMissPress';
                            args = pressArgs;
                        }
                    }
                    function miss():Void callAllHScript('noteMiss', [note, playerOne, direction]);
                }
            ''')
            psych = audit_api.ApiEntry("Psych chart hooks", "dispatched callbacks", "noteMissPress", "callback")
            nv = audit_api.ApiEntry("Nightmare Vision HScript", "dispatched callbacks", "noteMissPress", "callback")
            aliases = audit_api._callback_alias_inventory(root)
            self.assertTrue(any(item["evidence_kind"] == "conditional-argument-adapter" for item in aliases), aliases)
            direct, mentions, dynamic, _ = audit_api._engine_inventory(root, {psych.name})
            audit_api._apply_statuses([psych, nv], root, direct, mentions, dynamic)
            self.assertEqual(psych.status, "implemented")
            self.assertEqual(nv.status, "names-only")
            alias = next(item for item in aliases
                         if item["evidence_kind"] == "conditional-argument-adapter")
            self.assertEqual(alias["host_callback_spellings"], ["noteMiss"])
            self.assertIn("args[2]", alias["argument_mapping"])

    def test_source_contracts_include_signatures_returns_units_and_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            donor = root / "psych"
            write(donor, "source/psychlua/FunkinLua.hx", '''
                /** Set health and return whether the value was accepted in milliseconds. */
                Lua_helper.add_callback(lua, "setHealth", function(value:Float = 1.0):Bool {
                    game.health = value;
                    trace(value);
                    return true;
                });
            ''')
            write(donor, "source/psychlua/HScript.hx", '''
                set("setScriptValue", (name:String, value:Dynamic = null) -> game.variables.set(name, value));
            ''')
            entries = audit_api._psych_donor_entries(donor)
            audit_api._build_contract_inventory(
                entries,
                {"Psych Lua": donor, "Psych HScript": donor, "Psych chart hooks": donor},
                root,
            )
            by_key = {(entry.dialect, entry.name): entry.contract for entry in entries}
            lua = by_key[("Psych Lua", "setHealth")]
            self.assertEqual(lua["signature_status"], "source-signature")
            self.assertEqual(lua["parameters"][0]["default"], "1.0")
            self.assertTrue(lua["parameters"][0]["omittable"])
            self.assertEqual(lua["declared_return_type"], "Bool")
            self.assertEqual(lua["return_evidence"][0]["expression"], "true")
            self.assertEqual(lua["units"], ["milliseconds"])
            self.assertEqual(lua["side_effect_evidence"]["writes"][0]["target"], "game.health")

            hscript = by_key[("Psych HScript", "setScriptValue")]
            self.assertEqual(hscript["signature_status"], "source-signature")
            self.assertEqual(hscript["parameters"][1]["default"], "null")
            self.assertEqual(hscript["return_evidence"][0]["kind"], "implicit-arrow-result")
            self.assertEqual(lua["behavioral_verification"], "unverified")

    def test_dispatch_contract_captures_payload_and_return_use_without_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = write(root, "source/PlayState.hx", '''
                class PlayState {
                    function spawn(note:Dynamic):Void {
                        if (scripts.call('onSpawnNote', [note], false, [note.noteType]) == STOP_FUNC) return;
                        scripts.call('onSpawnNotePost', [note], false, [note.noteType]);
                    }
                }
            ''')
            sites = audit_api._dispatch_contracts(root, audit_api._read_code(source), source, "Nightmare Vision HScript")
            pre, post = sites
            self.assertEqual(pre["callback_payload_items"], ["note"])
            self.assertEqual(pre["return_use"], "compared-to-script-sentinel")
            self.assertEqual(post["return_use"], "return-value-not-observed-in-containing-statement")
            self.assertEqual(pre["name_resolution"], "literal")

    def test_dispatch_audit_excludes_callback_dispatcher_declarations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = write(root, "source/PlayState.hx", '''
                public function callOnScripts(funcToCall:String, args:Array<Dynamic> = null):Dynamic {
                    var result = callOnLuas(funcToCall, args);
                    return result;
                }
                callOnScripts('onUpdate', [elapsed]);
            ''')
            sites = audit_api._dispatch_contracts(root, audit_api._read_code(source), source, "Psych chart hooks")
            self.assertEqual([site["callback"] for site in sites if site["callback"]], ["onUpdate"])
            self.assertFalse(any(site["callback_expression"] == "funcToCall:String" for site in sites))

    def test_psych_achievement_bindings_require_complete_runtime_reachability(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            donor = root / "donor"
            engine = root / "engine"
            write_psych_achievement_donor(donor)
            write_psych_achievement_engine(engine)

            def inventory():
                entries = audit_api._psych_donor_entries(donor)
                routes = audit_api._source_binding_audit(engine)
                names = {entry.name for entry in entries}
                direct, mentions, dynamic, _ = audit_api._engine_inventory(engine, names, routes)
                audit_api._apply_statuses(entries, engine, direct, mentions, dynamic)
                return entries, {route["name"]: route for route in routes[1]}

            entries, routes = inventory()
            by_key = {(entry.dialect, entry.name): entry for entry in entries}
            self.assertEqual(
                {name: by_key[("Psych Lua", name)].status for name in PSYCH_ACHIEVEMENT_LUA_NAMES},
                {name: "implemented" for name in PSYCH_ACHIEVEMENT_LUA_NAMES},
            )
            self.assertEqual(by_key[("Psych HScript", "Achievements")].status, "implemented")
            lua_route = routes["Psych Lua achievements callbacks"]
            hscript_route = routes["Psych HScript Achievements global"]
            self.assertEqual(lua_route["binding_names"], sorted(PSYCH_ACHIEVEMENT_LUA_NAMES))
            self.assertEqual(hscript_route["binding_names"], ["Achievements"])
            self.assertTrue(all(step["status"] == "found" for step in lua_route["chain"]))
            self.assertTrue(all(step["status"] == "found" for step in hscript_route["chain"]))

            # Literal callback registrations are insufficient when translated
            # Lua no longer reaches their owner binding helper.
            runtime_path = engine / "source" / "PsychRuntimeBindings.hx"
            runtime = runtime_path.read_text(encoding="utf-8")
            runtime_path.write_text(runtime.replace("owner, LuaCompatInterp", "owner, OtherLuaInterp"), encoding="utf-8")
            entries, routes = inventory()
            by_key = {(entry.dialect, entry.name): entry for entry in entries}
            self.assertEqual(routes["Psych Lua achievements callbacks"]["status"], "not-wired")
            self.assertEqual(
                {by_key[("Psych Lua", name)].status for name in PSYCH_ACHIEVEMENT_LUA_NAMES},
                {"missing"},
            )
            self.assertEqual(by_key[("Psych HScript", "Achievements")].status, "implemented")

            # The HScript class token is not implemented by a detached binder;
            # its SourceIrisBridge integration handoff must reach the binder.
            runtime_path.write_text(runtime, encoding="utf-8")
            integration_path = engine / "source" / "PsychAchievementsIntegration.hx"
            integration = integration_path.read_text(encoding="utf-8")
            integration_path.write_text(
                integration.replace("PsychAchievementsBindings.install(", "PsychAchievementsBindings.unwired("),
                encoding="utf-8",
            )
            entries, routes = inventory()
            by_key = {(entry.dialect, entry.name): entry for entry in entries}
            self.assertEqual(routes["Psych HScript Achievements global"]["status"], "not-wired")
            self.assertEqual(by_key[("Psych HScript", "Achievements")].status, "missing")
            self.assertEqual(
                {by_key[("Psych Lua", name)].status for name in PSYCH_ACHIEVEMENT_LUA_NAMES},
                {"implemented"},
            )

    def test_psych_language_and_discord_routes_require_standard_service_handoffs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            donor = root / "donor"
            engine = root / "engine"
            write_psych_standard_donor(donor)
            write_psych_standard_engine(engine)

            entries = audit_api._psych_donor_entries(donor)
            routes = audit_api._source_binding_audit(engine)
            names = {entry.name for entry in entries}
            direct, mentions, dynamic, _ = audit_api._engine_inventory(engine, names, routes)
            audit_api._apply_statuses(entries, engine, direct, mentions, dynamic)
            by_key = {(entry.dialect, entry.name): entry for entry in entries}
            route_by_name = {route["name"]: route for route in routes[1]}

            self.assertEqual(
                {name: by_key[("Psych Lua", name)].status
                 for name in (*PSYCH_LANGUAGE_LUA_NAMES, *PSYCH_DISCORD_LUA_NAMES)},
                {name: "implemented"
                 for name in (*PSYCH_LANGUAGE_LUA_NAMES, *PSYCH_DISCORD_LUA_NAMES)},
            )
            self.assertEqual(
                route_by_name["Psych Lua Language callbacks"]["binding_names"],
                sorted(PSYCH_LANGUAGE_LUA_NAMES),
            )
            self.assertEqual(
                route_by_name["Psych Lua Discord callbacks"]["binding_names"],
                sorted(PSYCH_DISCORD_LUA_NAMES),
            )
            for name in (
                "Psych Lua Language callbacks", "Psych Lua Discord callbacks",
                "Psych HScript Language import (plain HScript)",
                "Psych HScript Language import (embedded runHaxeCode)",
                "Psych HScript DiscordClient import (plain HScript)",
                "Psych HScript DiscordClient import (embedded runHaxeCode)",
            ):
                self.assertEqual(route_by_name[name]["status"], "wired")
                self.assertTrue(all(step["status"] == "found" for step in route_by_name[name]["chain"]))
                self.assertEqual(route_by_name[name]["behavioral_verification"], "unverified")
            self.assertEqual(
                route_by_name["Psych HScript Language import (plain HScript)"]["binding_names"],
                ["backend.Language"],
            )
            self.assertEqual(
                route_by_name["Psych HScript DiscordClient import (plain HScript)"]["binding_names"],
                ["backend.DiscordClient"],
            )

    def test_psych_standard_routes_reject_disconnected_and_swapped_methods(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            donor = root / "donor"
            engine = root / "engine"
            write_psych_standard_donor(donor)
            write_psych_standard_engine(engine)

            def inspect():
                entries = audit_api._psych_donor_entries(donor)
                routes = audit_api._source_binding_audit(engine)
                names = {entry.name for entry in entries}
                direct, mentions, dynamic, _ = audit_api._engine_inventory(engine, names, routes)
                audit_api._apply_statuses(entries, engine, direct, mentions, dynamic)
                return entries, {route["name"]: route for route in routes[1]}

            standard_path = engine / "source" / "PsychStandardServices.hx"
            standard_original = standard_path.read_text(encoding="utf-8")
            runtime_path = engine / "source" / "PsychRuntimeBindings.hx"
            runtime_original = runtime_path.read_text(encoding="utf-8")

            # The literal Language and Discord callback names remain in their
            # binders, but a disconnected runtime route invalidates both APIs.
            runtime_path.write_text(
                runtime_original.replace(
                    "PsychStandardServices.installLua(host, owner, origin);",
                    "PsychAchievementsIntegration.installLua(host, owner, origin);",
                ),
                encoding="utf-8",
            )
            entries, routes = inspect()
            by_key = {(entry.dialect, entry.name): entry for entry in entries}
            self.assertEqual(routes["Psych Lua Language callbacks"]["status"], "not-wired")
            self.assertEqual(routes["Psych Lua Discord callbacks"]["status"], "not-wired")
            self.assertEqual(
                {by_key[("Psych Lua", name)].status
                 for name in (*PSYCH_LANGUAGE_LUA_NAMES, *PSYCH_DISCORD_LUA_NAMES)},
                {"missing"},
            )

            runtime_path.write_text(runtime_original, encoding="utf-8")
            standard_path.write_text(
                standard_original.replace(
                    "PsychLanguageBindings.installLua(interp, owner.language);",
                    "PsychDiscordBindings.installLua(interp, owner.language);",
                ),
                encoding="utf-8",
            )
            entries, routes = inspect()
            by_key = {(entry.dialect, entry.name): entry for entry in entries}
            self.assertEqual(routes["Psych Lua Language callbacks"]["status"], "not-wired")
            self.assertEqual(routes["Psych Lua Discord callbacks"]["status"], "wired")
            self.assertEqual(
                {by_key[("Psych Lua", name)].status for name in PSYCH_LANGUAGE_LUA_NAMES},
                {"missing"},
            )
            self.assertEqual(
                {by_key[("Psych Lua", name)].status for name in PSYCH_DISCORD_LUA_NAMES},
                {"implemented"},
            )

            standard_path.write_text(
                standard_original.replace(
                    "PsychLanguageBindings.install(evaluator, owner.language);",
                    "PsychDiscordBindings.install(evaluator, owner.language);",
                ),
                encoding="utf-8",
            )
            entries, routes = inspect()
            self.assertEqual(
                routes["Psych HScript Language import (plain HScript)"]["status"],
                "not-wired",
            )
            self.assertEqual(
                routes["Psych HScript DiscordClient import (plain HScript)"]["status"],
                "wired",
            )

            standard_path.write_text(standard_original, encoding="utf-8")
            language_path = engine / "source" / "PsychLanguageBindings.hx"
            language_original = language_path.read_text(encoding="utf-8")
            language_path.write_text(
                language_original.replace(
                    "interp.bindImport('backend.Language', type);",
                    "interp.bindImport('backend.OtherLanguage', type);",
                ),
                encoding="utf-8",
            )
            _, routes = inspect()
            self.assertEqual(
                routes["Psych HScript Language import (plain HScript)"]["status"],
                "not-wired",
            )
            language_path.write_text(language_original, encoding="utf-8")

    def test_psych_source_preset_requires_a_wired_interpreter_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, "source/PlayState.hx", '''
                class PlayState {
                    function makeHaxeState():Void {
                        var plainPsych = true;
                        var interp = plainPsych ? PluginManager.addVarsToInterp(new SourceIrisBridge(this)) : null;
                        seedEngineCompat(interp, null);
                    }
                    function seedEngineCompat(interp:Dynamic, extra:Dynamic):Void {
                        var runtime = new PsychRuntimeBindings(this, interp, 'chart.hx');
                        runtime.install();
                    }
                }
            ''')
            write(root, "source/PsychRuntimeBindings.hx", '''
                class PsychRuntimeBindings {
                    function install():Void {
                        if (Std.isOfType(owner, SourceIrisBridge)) installHscriptPreset(owner, null);
                        var run = function() return module();
                    }
                    function module():SourceIrisBridge {
                        embedded = new SourceIrisBridge(host);
                        installHscriptPreset(embedded, null);
                        return embedded;
                    }
                    function installHscriptPreset(scope:Dynamic, parent:Dynamic):Void {
                        attachCallbackScope(scope);
                        new PsychHscriptSourceBindings(host, scope, origin,
                            host.psychSourceCallbacks.bridge(ownerRoot, scope, origin, parent)).install();
                    }
                }
            ''')
            write(root, "source/PsychSourceCallbackRegistry.hx", '''
                class PsychSourceCallbackRegistry {
                    function bridge(ownerRoot:String, interp:Dynamic, origin:String, parent:Dynamic):Dynamic {
                        return {selfFacade:function(_origin:String, _interp:Dynamic, parentLua:Dynamic) return {}};
                    }
                }
            ''')
            write(root, "source/PsychHscriptSourceBindings.hx", '''
                class PsychHscriptSourceBindings {
                    function install():Void {
                        variables.set('PsychCamera', Camera);
                        variables.set('createCallback', callback);
                        variables.set('this', conditionalFacade);
                    }
                }
            ''')
            entries = [
                audit_api.ApiEntry("Psych HScript", "seeded globals", name, "value")
                for name in ("PsychCamera", "createCallback", "this")
            ]
            routes = audit_api._source_binding_audit(root)
            direct, mentions, dynamic, _ = audit_api._engine_inventory(
                root, {entry.name for entry in entries}, routes,
            )
            audit_api._apply_statuses(entries, root, direct, mentions, dynamic)
            self.assertEqual([entry.status for entry in entries], ["implemented"] * 3)
            route_by_name = {route["name"]: route for route in routes[1]}
            self.assertEqual(
                [route_by_name[name]["status"] for name in (
                    "Psych plain HScript owner preset", "Psych embedded runHaxeCode preset",
                    "Nightmare Vision chart owner globals", "Nightmare Vision chart-local globals",
                )], ["wired", "wired", "not-wired", "not-wired"]
            )
            self.assertEqual(route_by_name["Psych Lua achievements callbacks"]["status"], "not-wired")
            self.assertEqual(route_by_name["Psych HScript Achievements global"]["status"], "not-wired")
            for name in (
                "Psych Lua Language callbacks", "Psych Lua Discord callbacks",
                "Psych HScript Language import (plain HScript)",
                "Psych HScript Language import (embedded runHaxeCode)",
                "Psych HScript DiscordClient import (plain HScript)",
                "Psych HScript DiscordClient import (embedded runHaxeCode)",
            ):
                self.assertEqual(route_by_name[name]["status"], "not-wired")
            self.assertTrue(all(route["behavioral_verification"] == "unverified" for route in routes[1]))

            disconnected = root / "disconnected"
            write(disconnected, "source/PlayState.hx", '''
                class PlayState { function mentions():Void createCallback(); }
            ''')
            write(disconnected, "source/PsychHscriptSourceBindings.hx", '''
                class PsychHscriptSourceBindings {
                    function install():Void variables.set('createCallback', callback);
                }
            ''')
            write(disconnected, "source/PsychRuntimeBindings.hx", '''
                class PsychRuntimeBindings {
                    function install():Void new PsychHscriptSourceBindings().install();
                }
            ''')
            entry = audit_api.ApiEntry("Psych HScript", "seeded globals", "createCallback", "function")
            disconnected_routes = audit_api._source_binding_audit(disconnected)
            direct, mentions, dynamic, _ = audit_api._engine_inventory(
                disconnected, {entry.name}, disconnected_routes,
            )
            audit_api._apply_statuses([entry], disconnected, direct, mentions, dynamic)
            self.assertEqual(entry.status, "names-only")
            self.assertFalse(any(route["status"] == "wired" for route in disconnected_routes[1]))

    def test_nightmare_vision_binder_requires_chart_route_and_literal_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            donor = root / "donor"
            write(root, "source/PlayState.hx", '''
                class PlayState {
                    function initializeNightmareVisionScripts():Void {
                        var scripts = new NightmareVisionGameplayScripts(this, plan, read,
                            seedNightmareVision, report);
                        nightmareVisionScripts = scripts;
                        nightmareVisionScripts.loadScope('stage');
                    }
                    static function seedNightmareVisionCommon(interp:Dynamic):Void {
                        NightmareVisionSourceBindings.bindOwner(interp, root, modFolder);
                    }
                    function seedNightmareVision(interp:Dynamic):Void {
                        seedNightmareVisionCommon(interp);
                        var fields:Map<String, Dynamic> = [
                            'bpm' => 120, 'practice' => false
                        ];
                        NightmareVisionSourceBindings.bindGameplay(interp, this, true, fields,
                            function(path:String):Dynamic return null);
                    }
                }
            ''')
            write(root, "source/NightmareVisionGameplayScripts.hx", '''
                class NightmareVisionGameplayScripts {
                    function loadScope(scope:String):Void {
                        configure(interp, entry, null);
                    }
                }
            ''')
            write(root, "source/NightmareVisionSourceBindings.hx", '''
                class NightmareVisionSourceBindings {
                    static final gameplayNames:Array<String> = ['bpm', 'practice', 'weekRaw'];
                    static function bindOwner(interp:Dynamic, ownerRoot:String, modFolder:String,
                        ?scriptContext:Dynamic):Dynamic {
                        set(vars, 'Random', Random);
                        set(vars, 'keyToString', callback);
                        set(vars, 'newOption', callback);
                        set(vars, 'script', scriptContext);
                        set(vars, 'modFolder', modFolder);
                    }
                    static function bindGameplay(interp:Dynamic, state:Dynamic, inPlaystate:Bool,
                        fields:Map<String, Dynamic>, initScript:String->Dynamic):Void {
                        set(vars, 'inPlaystate', inPlaystate);
                        for (name in gameplayNames) if (fields != null && fields.exists(name))
                            set(vars, name, fields.get(name));
                        set(vars, 'initScript', callback);
                    }
                }
            ''')
            write(donor, "source/funkin/scripts/FunkinScript.hx", '''
                class FunkinScript {
                    function seed():Void {
                        set('Random', Random);
                        set('keyToString', callback);
                        set('newOption', callback);
                        set('script', this);
                        set('modFolder', folder);
                        set('inPlaystate', true);
                        set('initScript', callback);
                        set('bpm', 120);
                        set('practice', false);
                        set('weekRaw', 'week');
                    }
                }
            ''')
            entries = audit_api._nv_donor_entries(donor)
            direct, mentions, dynamic, _ = audit_api._engine_inventory(
                root, {entry.name for entry in entries}, audit_api._source_binding_audit(root),
            )
            audit_api._apply_statuses(entries, root, direct, mentions, dynamic)
            statuses = {entry.name: entry.status for entry in entries}
            self.assertEqual(statuses["Random"], "implemented")
            self.assertEqual(statuses["keyToString"], "implemented")
            self.assertEqual(statuses["newOption"], "implemented")
            self.assertEqual(statuses["modFolder"], "implemented")
            self.assertEqual(statuses["inPlaystate"], "implemented")
            self.assertEqual(statuses["initScript"], "implemented")
            self.assertEqual(statuses["bpm"], "implemented")
            self.assertEqual(statuses["practice"], "implemented")
            self.assertEqual(statuses["weekRaw"], "missing")
            self.assertEqual(statuses["script"], "missing")

            roots = {"Nightmare Vision HScript": donor}
            audit_api._build_contract_inventory(entries, roots, root)
            random_contract = next(entry.contract for entry in entries if entry.name == "Random")
            self.assertEqual(random_contract["coverage_evidence_kind"], "explicit-installed-source-binder")
            self.assertEqual(random_contract["behavioral_verification"], "unverified")

    def test_missing_donors_leave_a_readable_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root, "source/PlayState.hx", "class PlayState {}\n")
            examples = root / "Windows Examples"
            (examples / "psych").mkdir(parents=True)
            (examples / "nightmare vision").mkdir(parents=True)
            report = audit_api.audit(root, root / "absent-psych", root / "absent-nv", examples)
            self.assertFalse(report["metadata"][1]["available"])
            self.assertFalse(report["metadata"][2]["available"])
            rendered = audit_api.render_markdown(report)
            self.assertIn("No local donor inventory", rendered)
            self.assertIn("unavailable", rendered)
            self.assertTrue(report["example_corpora"]["available"])
            self.assertTrue(all(item["available"] for item in report["example_corpora"]["dialect_roots"]))
            self.assertEqual(report["contract_inventory"]["entries"], [])
            self.assertIn("neither name references nor semantic candidates are behavior proofs", rendered)


if __name__ == "__main__":
    unittest.main()
