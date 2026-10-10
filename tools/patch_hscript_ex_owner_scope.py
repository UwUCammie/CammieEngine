#!/usr/bin/env python3
"""Apply the small owner-scope extension to the pinned hscript-ex source."""
from pathlib import Path
import os
import sys
import tempfile


PATCHES = {
    "InterpEx.hx": [
        ("""import hscript.Expr.ModuleDecl;""",
         """import hscript.Expr.ModuleDecl;
#if flixel
import PsychFlxColorScriptAccess;
#end""",
         "dp-psych-flxcolor-script-access-import"),
        ("""    private var _proxy:AbstractScriptClass = null;
    
    public function new(proxy:AbstractScriptClass = null) {
        super();
        _proxy = proxy;""",
         """    private var _proxy:AbstractScriptClass = null;
    /** Owner-local descriptors and symbols; null keeps upstream standalone behavior. */
    private var _classScope:ScriptClassScope = null;
    
    public function new(proxy:AbstractScriptClass = null, ?classScope:ScriptClassScope) {
        super();
        _proxy = proxy;
        _classScope = classScope; // dp-owner-class-scope-ctor""",
         "dp-owner-class-scope-ctor"),
        ("""    private var _classScope:ScriptClassScope = null;
    
    public function new(proxy:AbstractScriptClass = null, ?classScope:ScriptClassScope) {""",
         """    private var _classScope:ScriptClassScope = null;
    private var _staticInitializerRequester:ClassDeclEx = null; // dp-owner-static-field-init-context
    
    public function new(proxy:AbstractScriptClass = null, ?classScope:ScriptClassScope) {""",
         "dp-owner-static-field-init-context"),
        ("""        variables.set("Std", Std);
    }
    
    private static var _scriptClassDescriptors:Map<String, ClassDeclEx> = new Map<String, ClassDeclEx>();""",
         """        variables.set("Std", Std);
    }

    private var _alphaAccessDiagnostics:Map<String, Bool> = new Map(); // dp-smoke-hscript-ex-alpha-access

    /** Keep property probing out of normal launches; this identifies native
        HScript-ex receivers without changing the ordinary Reflect path. */
    private function diagnoseAlphaAccess(operation:String, object:Dynamic, field:String, ?value:Dynamic):Void {
        #if sys
        if (field != "alpha" || Sys.args().indexOf("--smoke-song") < 0) return;
        var classType = Type.getClass(object);
        var className = classType == null ? "<dynamic>" : Type.getClassName(classType);
        if (className == null) className = "<dynamic>";
        var owner = _proxy == null ? "<none>" : _proxy._c.name;
        var key = operation + ":" + owner + ":" + className + ":" + field;
        if (_alphaAccessDiagnostics.exists(key)) return;
        _alphaAccessDiagnostics.set(key, true);
        var current = "<unavailable>";
        try current = Std.string(Reflect.getProperty(object, field)) catch (_:Dynamic) {}
        var fields = Reflect.fields(object);
        var source = variables == null ? null : variables.get("__compatDiagnosticSource");
        var callback = variables == null ? null : variables.get("__compatDiagnosticCallback");
        var valueType = operation == "write" ? Std.string(Type.typeof(value)) : "<read>";
        Sys.println("[hscript-ex-alpha-access] op=" + operation
            + " source=" + (source == null ? "<unknown>" : Std.string(source))
            + " callback=" + (callback == null ? "<unknown>" : Std.string(callback))
            + " owner=" + owner + " receiver=" + className + " field=" + field
            + " rawField=" + (fields.indexOf(field) >= 0) + " current=" + current
            + " valueType=" + valueType);
        #end
    } // dp-smoke-hscript-ex-alpha-access-helper

    private static var _scriptClassDescriptors:Map<String, ClassDeclEx> = new Map<String, ClassDeclEx>();""",
         "dp-smoke-hscript-ex-alpha-access-helper"),
        ("""    override function cnew(cl:String, args:Array<Dynamic>):Dynamic {
        if (_scriptClassDescriptors.exists(cl)) {""",
         """    override function cnew(cl:String, args:Array<Dynamic>):Dynamic {
        if (_classScope != null) {
            var scoped = _classScope.createInstance(cl, args, _proxy == null ? null : _proxy._c);
            if (scoped != null) return scoped;
            if (_proxy != null && _proxy._c.imports != null && _proxy._c.imports.exists(cl)) {
                var importedName = _proxy._c.imports.get(cl).join(".");
                scoped = _classScope.createInstance(importedName, args);
                if (scoped != null) return scoped;
            }
            // Never fall through to hscript-ex's process-global class registry.
            return super.cnew(cl, args); // dp-owner-class-scope-cnew
        }
        if (_scriptClassDescriptors.exists(cl)) {""",
         "dp-owner-class-scope-cnew"),
        ("""            case EIdent(id):
                if (_proxy != null && _proxy.superClass != null && Reflect.hasField(_proxy.superClass, id)) {
                    Reflect.setProperty(_proxy.superClass, id, v);
                    return v;
                }""",
         """            case EIdent(id):
                if (_proxy != null && _proxy.superClass != null && _proxy.hasNativeSuperField(id, true)) {
                    Reflect.setProperty(_proxy.superClass, id, v);
                    return v;
                } else if (_proxy != null && _proxy.superClass == null
                    && _proxy._c.extend != null && !_proxy.hasDeclaredField(id)) {
                    // Haxe constructors may assign inherited fields before super().
                    _proxy.setPendingSuperField(id, v);
                    return v;
                } else if (_proxy != null && _proxy._c.extend != null && !_proxy.hasDeclaredField(id)) {
                    // Preserve dynamic script fields after super construction too.
                    _proxy.setPendingSuperField(id, v);
                    return v;
                }""",
         "dp-owner-class-scope-pending-write"),
        ("""            case EIdent(id):
                if (_proxy != null && _proxy.superClass != null && _proxy.hasNativeSuperField(id, true)) {
                    Reflect.setProperty(_proxy.superClass, id, v);
                    return v;
                } else if (_proxy != null && _proxy.superClass == null
                    && _proxy._c.extend != null && !_proxy.hasDeclaredField(id)) {
                    // Haxe constructors may assign inherited fields before super().
                    _proxy.setPendingSuperField(id, v);
                    return v;
                } else if (_proxy != null && _proxy._c.extend != null && !_proxy.hasDeclaredField(id)) {
                    // Preserve dynamic script fields after super construction too.
                    _proxy.setPendingSuperField(id, v);
                    return v;
                }""",
         """            case EIdent(id):
                // dp-owner-class-scope-pending-write
                // Function locals and arguments shadow inherited native fields
                // and must stay in the HScript frame.
                if (locals.get(id) == null && _classMethodLocals.indexOf(id) < 0) { // dp-owner-class-local-write-priority
                    if (_proxy != null && _proxy.superClass != null && _proxy.hasNativeSuperField(id, true)) {
                        Reflect.setProperty(_proxy.superClass, id, v);
                        return v;
                    } else if (_proxy != null && _proxy.superClass == null
                        && _proxy._c.extend != null && !_proxy.hasDeclaredField(id)) {
                        // Haxe constructors may assign inherited fields before super().
                        _proxy.setPendingSuperField(id, v);
                        return v;
                    } else if (_proxy != null && _proxy._c.extend != null && !_proxy.hasDeclaredField(id)) {
                        // Haxe constructors may assign inherited fields before super().
                        _proxy.setPendingSuperField(id, v);
                        return v;
                    }
                }""",
         "dp-owner-class-local-write-priority"),
        ("""    override function assign( e1 : Expr, e2 : Expr ) : Dynamic {
        var v = expr(e2);
        switch ( Tools.expr(e1) ) {
            case EIdent(id):
                // dp-owner-class-scope-pending-write
                // Function locals and arguments shadow inherited native fields
                // and must stay in the HScript frame.
                if (locals.get(id) == null && _classMethodLocals.indexOf(id) < 0) { // dp-owner-class-local-write-priority
                    if (_proxy != null && _proxy.superClass != null && _proxy.hasNativeSuperField(id, true)) {
                        Reflect.setProperty(_proxy.superClass, id, v);
                        return v;
                    } else if (_proxy != null && _proxy.superClass == null
                        && _proxy._c.extend != null && !_proxy.hasDeclaredField(id)) {
                        // Haxe constructors may assign inherited fields before super().
                        _proxy.setPendingSuperField(id, v);
                        return v;
                    } else if (_proxy != null && _proxy._c.extend != null && !_proxy.hasDeclaredField(id)) {
                        // Haxe constructors may assign inherited fields before super().
                        _proxy.setPendingSuperField(id, v);
                        return v;
                    }
                }
            case _:    
        }
        return super.assign(e1, e2);
    }""",
         """    override function assign( e1 : Expr, e2 : Expr ) : Dynamic {
        // dp-owner-assign-once: let the fallback interpreter evaluate RHS.
        switch ( Tools.expr(e1) ) {
            case EIdent(id):
                // dp-owner-class-scope-pending-write
                // Function locals and arguments shadow inherited native fields
                // and must stay in the HScript frame.
                if (locals.get(id) == null && _classMethodLocals.indexOf(id) < 0) { // dp-owner-class-local-write-priority
                    if (_proxy != null && _proxy.superClass != null && _proxy.hasNativeSuperField(id, true)) {
                        var v = expr(e2);
                        Reflect.setProperty(_proxy.superClass, id, v);
                        return v;
                    } else if (_proxy != null && _proxy.superClass == null
                        && _proxy._c.extend != null && !_proxy.hasDeclaredField(id)) {
                        // Haxe constructors may assign inherited fields before super().
                        var v = expr(e2);
                        _proxy.setPendingSuperField(id, v);
                        return v;
                    } else if (_proxy != null && _proxy._c.extend != null && !_proxy.hasDeclaredField(id)) {
                        // Haxe constructors may assign inherited fields before super().
                        var v = expr(e2);
                        _proxy.setPendingSuperField(id, v);
                        return v;
                    }
                }
            case _:    
        }
        return super.assign(e1, e2);
    }""",
         "dp-owner-assign-once"),
        ("""        // dp-owner-assign-once: let the fallback interpreter evaluate RHS.
        switch ( Tools.expr(e1) ) {""",
         """        // dp-owner-assign-once: let the fallback interpreter evaluate RHS.
        #if flixel
        switch (Tools.expr(e1)) {
            case EField(receiver, field):
                if (PsychFlxColorScriptAccess.hasSetter(field)) {
                    var target = captureLValue(receiver);
                    var object = target.value;
                    var assigned = expr(e2);
                    if (PsychFlxColorScriptAccess.isColorValue(object)) {
                        target.write(PsychFlxColorScriptAccess.set(object, field, assigned));
                        return assigned;
                    }
                    return set(object, field, assigned);
                }
            case _:
        }
        #end
        switch ( Tools.expr(e1) ) {""",
         "dp-psych-flxcolor-property-assign"),
        ("""    override function assign( e1 : Expr, e2 : Expr ) : Dynamic {""",
         """    #if flixel
    /** Evaluate an assignable expression once and retain a write-back target. */
    // dp-psych-flxcolor-capture-lvalue
    private function captureLValue(target:Expr):Dynamic {
        switch (Tools.expr(target)) {
            case EIdent(id):
                var local = locals.get(id);
                if (local != null) {
                    return {value:local.r, write:function(value:Dynamic) { local.r = value; }};
                }
                if (variables.exists(id)) {
                    return {value:variables.get(id), write:function(value:Dynamic) { variables.set(id, value); }};
                }
                var resolved = resolve(id);
                if (_proxy != null) {
                    return {value:resolved, write:function(value:Dynamic) { _proxy.setFieldValue(id, value); }};
                }
                return {value:resolved, write:function(value:Dynamic) { variables.set(id, value); }};
            case EField(objectExpr, field):
                var object = expr(objectExpr);
                return {value:get(object, field), write:function(value:Dynamic) { set(object, field, value); }};
            case EArray(arrayExpr, indexExpr):
                var array:Dynamic = expr(arrayExpr);
                var index:Dynamic = expr(indexExpr);
                var current = isMap(array) ? getMapValue(array, index) : array[index];
                return {value:current, write:function(value:Dynamic) {
                    if (isMap(array)) setMapValue(array, index, value); else array[index] = value;
                }};
            case _:
                error(EInvalidOp("="));
        }
        return null;
    }
    #end

    override function assign( e1 : Expr, e2 : Expr ) : Dynamic {""",
         "dp-psych-flxcolor-capture-lvalue"),
        ("""    #if flixel
    /** Evaluate an assignable expression once and retain a write-back target. */
    // dp-psych-flxcolor-capture-lvalue
    private function captureLValue(target:Expr):Dynamic {""",
         """    /** Resolve indexed native-group bridges to this owner scope's script objects. */
    override public function expr(e:Expr):Dynamic {
        switch (Tools.expr(e)) {
            case EArray(arrayExpr, indexExpr):
                var array:Dynamic = expr(arrayExpr);
                var index:Dynamic = expr(indexExpr);
                if (array == null) {
                    nullAccessDiagnose("index", Std.string(index));
                    return null;
                }
                var value:Dynamic = isMap(array) ? getMapValue(array, index) : array[index];
                return _classScope == null ? value : _classScope.unwrapIndexedMember(value);
            case _:
        }
        return super.expr(e);
    } // dp-owner-indexed-group-member-read

    #if flixel
    /** Evaluate an assignable expression once and retain a write-back target. */
    // dp-psych-flxcolor-capture-lvalue
    private function captureLValue(target:Expr):Dynamic {""",
         "dp-owner-indexed-group-member-read"),
        ("""        return super.assign(e1, e2);
    }""",
         """        return super.assign(e1, e2);
    }

    #if flixel
    override function evalAssignOp(op, fop, e1, e2):Dynamic {
        switch (Tools.expr(e1)) {
            case EField(receiver, field):
                if (PsychFlxColorScriptAccess.hasSetter(field)) {
                    var target = captureLValue(receiver);
                    var object = target.value;
                    nullOperandSeen = false;
                    var current = PsychFlxColorScriptAccess.isColorValue(object)
                        ? PsychFlxColorScriptAccess.get(object, field) : get(object, field);
                    var value = fop(current, expr(e2));
                    if (value != null || !nullOperandSeen) {
                        if (PsychFlxColorScriptAccess.isColorValue(object))
                            target.write(PsychFlxColorScriptAccess.set(object, field, value));
                        else
                            value = set(object, field, value);
                    }
                    nullOperandSeen = false;
                    return value;
                }
            case _:
        }
        return super.evalAssignOp(op, fop, e1, e2);
    } // dp-psych-flxcolor-compound-field-assignment
    #end""",
         "dp-psych-flxcolor-compound-field-assignment"),
        ("""            } else if (proxy.superClass != null && Reflect.hasField(proxy.superClass, f)) {
                return Reflect.getProperty(proxy.superClass, f);""",
         """            } else if (proxy.hasNativeSuperField(f, false)) {
                return Reflect.getProperty(proxy.superClass, f);""",
         "dp-owner-inherited-native-properties-get"),
        ("""            } else if (proxy.superClass != null && Reflect.hasField(proxy.superClass, f)) {
                Reflect.setProperty(proxy.superClass, f, v);""",
         """            } else if (proxy.hasNativeSuperField(f, true)) {
                Reflect.setProperty(proxy.superClass, f, v);""",
         "dp-owner-inherited-native-properties-set"),
        ("""            } else if (_proxy != null && _proxy.superClass != null && (Reflect.hasField(_proxy.superClass, id) || Reflect.getProperty(_proxy.superClass, id) != null)) {
                _nextCallObject = _proxy.superClass;
                return Reflect.getProperty(_proxy.superClass, id);
            } else if (_proxy != null) {""",
         """            } else if (_proxy != null && _proxy.hasNativeSuperField(id, false)) {
                _nextCallObject = _proxy.superClass;
                _nextCallMethod = id;
                return Reflect.getProperty(_proxy.superClass, id);
            } else if (_proxy != null && _proxy.hasPendingSuperField(id)) {
                return _proxy.getPendingSuperField(id);
            } else if (_proxy != null) {""",
         "dp-owner-class-scope-pending-read"),
        ("""    public function registerModule(module:Array<ModuleDecl>) {
        var pkg:Array<String> = null;""",
         """    public function registerModule(module:Array<ModuleDecl>) {
        if (_classScope != null) {
            _classScope.registerModule(module);
            return;
        }
        var pkg:Array<String> = null;""",
         "dp-owner-class-scope-module"),
        ("""    public function addModule(moduleContents:String) {
        var parser = new hscript.ParserEx();""",
         """    /**
     * Nested script-class methods share this InterpEx. Interp.execute resets
     * its locals and declared-variable stack, so save and restore the caller's
     * frame around a nested method execution.
     */
    private var _classMethodDepth:Int = 0;
    public function executeClassMethod(expr:Expr):Dynamic {
        var nested = _classMethodDepth > 0;
        var savedLocals = locals;
        var savedDeclared = declared;
        var savedDepth = depth;
        var savedReturnValue = returnValue;
        var savedInTry = inTry;
        #if hscriptPos
        var savedCurExpr = curExpr;
        #end
        _classMethodDepth++;
        var result:Dynamic = null;
        try {
            result = execute(expr);
        } catch (error:Dynamic) {
            _classMethodDepth--;
            if (nested) {
                locals = savedLocals;
                declared = savedDeclared;
                depth = savedDepth;
                returnValue = savedReturnValue;
                inTry = savedInTry;
                #if hscriptPos
                curExpr = savedCurExpr;
                #end
            }
            throw error;
        }
        _classMethodDepth--;
        if (nested) {
            locals = savedLocals;
            declared = savedDeclared;
            depth = savedDepth;
            returnValue = savedReturnValue;
            inTry = savedInTry;
            #if hscriptPos
            curExpr = savedCurExpr;
            #end
        }
        return result;
    }

    public function addModule(moduleContents:String) {
        var parser = new hscript.ParserEx();""",
         "dp-owner-class-nested-call-frame"),
        ("""    private var _classMethodDepth:Int = 0;
    public function executeClassMethod(expr:Expr):Dynamic {
        var nested = _classMethodDepth > 0;""",
         """    private var _classMethodDepth:Int = 0; // dp-owner-class-nested-call-frame
    private var _classMethodLocals:Array<String> = []; // dp-owner-class-method-argument-scope
    public function executeClassMethod(expr:Expr, ?localNames:Array<String>):Dynamic {
        var savedClassMethodLocals = _classMethodLocals;
        _classMethodLocals = localNames == null ? [] : localNames.copy();
        var nested = _classMethodDepth > 0;""",
         "dp-owner-class-method-argument-scope"),
        ("""        } catch (error:Dynamic) {
            _classMethodDepth--;
            if (nested) {""",
         """        } catch (error:Dynamic) {
            _classMethodDepth--;
            _classMethodLocals = savedClassMethodLocals;
            if (nested) {""",
         "dp-owner-class-method-argument-restore-error"),
        ("""        _classMethodDepth--;
        if (nested) {""",
         """        _classMethodDepth--;
        _classMethodLocals = savedClassMethodLocals;
        if (nested) {""",
         "dp-owner-class-method-argument-restore"),
        ("""    public function executeClassMethod(expr:Expr, ?localNames:Array<String>):Dynamic {
        var savedClassMethodLocals = _classMethodLocals;
        _classMethodLocals = localNames == null ? [] : localNames.copy();
        var nested = _classMethodDepth > 0;
        var savedLocals = locals;
        var savedDeclared = declared;
        var savedDepth = depth;
        var savedReturnValue = returnValue;
        var savedInTry = inTry;
        #if hscriptPos
        var savedCurExpr = curExpr;
        #end
        _classMethodDepth++;
        var result:Dynamic = null;
        try {
            result = execute(expr);
        } catch (error:Dynamic) {
            _classMethodDepth--;
            _classMethodLocals = savedClassMethodLocals;
            if (nested) {
                locals = savedLocals;
                declared = savedDeclared;
                depth = savedDepth;
                returnValue = savedReturnValue;
                inTry = savedInTry;
                #if hscriptPos
                curExpr = savedCurExpr;
                #end
            }
            throw error;
        }
        _classMethodDepth--;
        _classMethodLocals = savedClassMethodLocals;
        if (nested) {
            locals = savedLocals;
            declared = savedDeclared;
            depth = savedDepth;
            returnValue = savedReturnValue;
            inTry = savedInTry;
            #if hscriptPos
            curExpr = savedCurExpr;
            #end
        }
        return result;
    }""",
         """    public function executeClassMethod(expr:Expr, ?localNames:Array<String>,
        ?providedArgs:Array<Dynamic>, ?defaultValues:Array<Expr>):Dynamic {
        var savedClassMethodLocals = _classMethodLocals;
        _classMethodLocals = localNames == null ? [] : localNames.copy();
        var nested = _classMethodDepth > 0;
        var savedLocals = locals;
        var savedDeclared = declared;
        var savedDepth = depth;
        var savedReturnValue = returnValue;
        var savedInTry = inTry;
        #if hscriptPos
        var savedCurExpr = curExpr;
        #end
        _classMethodDepth++;
        var result:Dynamic = null;
        try {
            // Interp.execute clears the local frame, so seed method parameters
            // after that reset. This keeps `this.field` separate from a
            // same-named parameter in the HScript local namespace.
            #if haxe3
            locals = new Map();
            #else
            locals = new Hash();
            #end
            declared = new Array();
            depth = 0;
            if (localNames != null) for (index in 0...localNames.length) {
                var value:Dynamic = null;
                if (providedArgs != null && index < providedArgs.length) {
                    value = providedArgs[index];
                } else if (defaultValues != null && index < defaultValues.length
                    && defaultValues[index] != null) {
                    // Earlier parameters stay visible to later defaults.
                    value = super.expr(defaultValues[index]);
                }
                locals.set(localNames[index], {r:value});
            }
            result = exprReturn(expr);
        } catch (error:Dynamic) {
            _classMethodDepth--;
            _classMethodLocals = savedClassMethodLocals;
            if (nested) {
                locals = savedLocals;
                declared = savedDeclared;
                depth = savedDepth;
                returnValue = savedReturnValue;
                inTry = savedInTry;
                #if hscriptPos
                curExpr = savedCurExpr;
                #end
            }
            throw error;
        }
        _classMethodDepth--;
        _classMethodLocals = savedClassMethodLocals;
        if (nested) {
            locals = savedLocals;
            declared = savedDeclared;
            depth = savedDepth;
            returnValue = savedReturnValue;
            inTry = savedInTry;
            #if hscriptPos
            curExpr = savedCurExpr;
            #end
        }
        return result;
    }""",
         "dp-owner-class-method-local-argument-values"),
        ("""\toverride function fcall( o : Dynamic, f : String, args : Array<Dynamic> ) : Dynamic {
        if ((o is ScriptClass)) {""",
         """\toverride function fcall( o : Dynamic, f : String, args : Array<Dynamic> ) : Dynamic {
        // dp-owner-native-group-fcall-args
        if (_classScope != null) args = _classScope.unwrapNativeGroupArguments(o, f, args);
        if (_classScope != null) args = _classScope.unwrapNativeTweenArguments(o, f, args); // dp-owner-native-tween-target-args
        if ((o is ScriptClass)) {""",
         "dp-owner-native-group-fcall-args"),
        ("""        // dp-owner-native-group-fcall-args
        if (_classScope != null) args = _classScope.unwrapNativeGroupArguments(o, f, args);""",
         """        // dp-owner-native-group-fcall-args
        if (_classScope != null && f == "recycle") {
            var recycled = _classScope.recycleScriptClass(o, args);
            if (recycled.handled) return recycled.value;
        } // dp-owner-script-class-recycle
        if (_classScope != null) args = _classScope.unwrapNativeGroupArguments(o, f, args);""",
         "dp-owner-script-class-recycle-fcall"),
        ("""        if ((o is ScriptClass)) {
            _nextCallObject = null;
            var proxy:ScriptClass = cast(o, ScriptClass);
            return proxy.callFunction(f, args);
        }
		return super.fcall(o, f, args);""",
         """        if ((o is ScriptClass)) {
            _nextCallObject = null;
            var proxy:ScriptClass = cast(o, ScriptClass);
            return proxy.callFunction(f, args);
        }
        // Haxe's Function.bind is a compiler extension, not a reflected
        // member of a native closure. Source classes use it to register stage
        // callbacks; preserve partial application in the interpreter.
        if (f == "bind" && Reflect.isFunction(o)) { // dp-owner-function-bind-fcall
            var bound = args == null ? [] : args.copy();
            return Reflect.makeVarArgs(function(later:Array<Dynamic>):Dynamic {
                var combined = bound.copy();
                for (arg in later) combined.push(arg);
                return Reflect.callMethod(null, o, combined);
            });
        }
		return super.fcall(o, f, args);""",
         "dp-owner-function-bind-fcall"),
        ("""                return Reflect.callMethod(null, o, combined);
            });
        }
\t\treturn super.fcall(o, f, args);""",
         """                return Reflect.callMethod(null, o, combined);
            });
        }
        // Haxe's `using StringTools` is resolved at compile time. Imported
        // source classes run dynamically, so invoke the same extension only
        // when the live receiver is truly a String; native Array.contains and
        // unrelated object methods still use their normal reflected route.
        if (Std.isOfType(o, String)) { // dp-owner-stringtools-fcall
            var value:String = cast o;
            switch (f) {
                case "trim" if (args == null || args.length == 0): return StringTools.trim(value);
                case "ltrim" if (args == null || args.length == 0): return StringTools.ltrim(value);
                case "rtrim" if (args == null || args.length == 0): return StringTools.rtrim(value);
                case "startsWith" if (args != null && args.length == 1): return StringTools.startsWith(value, Std.string(args[0]));
                case "endsWith" if (args != null && args.length == 1): return StringTools.endsWith(value, Std.string(args[0]));
                case "contains" if (args != null && args.length == 1): return StringTools.contains(value, Std.string(args[0]));
                case "replace" if (args != null && args.length == 2):
                    return StringTools.replace(value, Std.string(args[0]), Std.string(args[1]));
                default:
            }
        }
\t\treturn super.fcall(o, f, args);""",
         "dp-owner-stringtools-fcall"),
        ("""\toverride function call( o : Dynamic, f : Dynamic, args : Array<Dynamic> ) : Dynamic {
        // TODO: not sure if this make sense !! seems hacky, but fn() in hscript wont resolve an object first (this.fn() or super.fn() would work fine)
        if (o == null && _nextCallObject != null) {
            o = _nextCallObject;
        }
\t\tvar r = super.call(o, f, args);
        _nextCallObject = null;
        return r;
\t}
""",
         """\toverride function call( o : Dynamic, f : Dynamic, args : Array<Dynamic> ) : Dynamic {
        // TODO: not sure if this make sense !! seems hacky, but fn() in hscript wont resolve an object first (this.fn() or super.fn() would work fine)
        var inheritedMethod = o == null && _nextCallObject != null ? _nextCallMethod : null;
        if (o == null && _nextCallObject != null) {
            o = _nextCallObject;
        }
        // dp-owner-native-group-call-args
        if (inheritedMethod != null && _classScope != null)
            args = _classScope.unwrapNativeGroupArguments(o, inheritedMethod, args);
\t\tvar r = super.call(o, f, args);
        _nextCallObject = null;
        _nextCallMethod = null;
        return r;
\t}
""",
         "dp-owner-native-group-call-args"),
        ("""    private var _nextCallObject:Dynamic = null;
    override function resolve(id:String):Dynamic {
        _nextCallObject = null;""",
         """    private var _nextCallObject:Dynamic = null;
    private var _nextCallMethod:String = null; // dp-owner-native-group-method-context
    override function resolve(id:String):Dynamic {
        _nextCallObject = null;
        _nextCallMethod = null;""",
         "dp-owner-native-group-method-context"),
        ("""                try {
                    var r = _proxy.resolveField(id);
                    _nextCallObject = _proxy;
                    return r;
                } catch (e:Dynamic) {}
                error(EUnknownVariable(id));""",
         """                try {
                    var r = _proxy.resolveField(id);
                    _nextCallObject = _proxy;
                    return r;
                } catch (e:Dynamic) {}
                if (_classScope != null) {
                    var classSymbol = _classScope.resolveClassSymbol(id, _proxy._c);
                    if (classSymbol != null) return classSymbol;
                } // dp-owner-imported-class-values
                error(EUnknownVariable(id));""",
         "dp-owner-imported-class-values"),
        ("""            } else {
                error(EUnknownVariable(id));
            }
        }
        return v;""",
         """            } else {
                if (_classScope != null) {
                    var classSymbol = _classScope.resolveClassSymbol(id);
                    if (classSymbol != null) return classSymbol;
                } // dp-owner-imported-class-values
                error(EUnknownVariable(id));
            }
        }
        return v;""",
         "dp-owner-imported-class-values-without-proxy"),
        ("""\t\tvar l = locals.get(id);
		if( l != null )
			return l.r;
		var v = variables.get(id);""",
         """\t\tvar l = locals.get(id);
		if( l != null )
			return l.r;
        if (_staticInitializerRequester != null && _classScope != null) {
            var staticValue = getOwnerStaticDuringInitialization(id);
            if (staticValue.handled) return staticValue.value;
        } // dp-owner-static-field-init-resolution
		var v = variables.get(id);""",
         "dp-owner-static-field-init-resolution"),
        ("""    override function get( o : Dynamic, f : String ) : Dynamic {
        if ( o == null ) error(EInvalidAccess(f));
        if ((o is ScriptClass)) {""",
         """    override function get( o : Dynamic, f : String ) : Dynamic {
        if ( o == null ) error(EInvalidAccess(f));
        diagnoseAlphaAccess("read", o, f); // dp-smoke-hscript-ex-alpha-get
        if ((o is ScriptClass)) {""",
         "dp-smoke-hscript-ex-alpha-get"),
        ("""        diagnoseAlphaAccess("read", o, f); // dp-smoke-hscript-ex-alpha-get
        if ((o is ScriptClass)) {""",
         """        diagnoseAlphaAccess("read", o, f); // dp-smoke-hscript-ex-alpha-get
        #if flixel
        if (PsychFlxColorScriptAccess.isColorValue(o)
            && PsychFlxColorScriptAccess.hasGetter(f))
            return PsychFlxColorScriptAccess.get(o, f);
        #end
        if ((o is ScriptClass)) { // dp-psych-flxcolor-property-get""",
         "dp-psych-flxcolor-property-get"),
        ("""    override function set( o : Dynamic, f : String, v : Dynamic ) : Dynamic {
        if ( o == null ) error(EInvalidAccess(f));
        if ((o is ScriptClass)) {""",
         """    override function set( o : Dynamic, f : String, v : Dynamic ) : Dynamic {
        if ( o == null ) error(EInvalidAccess(f));
        diagnoseAlphaAccess("write", o, f, v); // dp-smoke-hscript-ex-alpha-set
        if ((o is ScriptClass)) {""",
         "dp-smoke-hscript-ex-alpha-set"),
        ("""    private static var _scriptClassDescriptors:Map<String, ClassDeclEx> = new Map<String, ClassDeclEx>();""",
         """    private function evaluateOwnerStaticInitializer(symbol:ScriptClassSymbol, initializer:Expr):Dynamic { // dp-owner-static-field-init-helper
        var previousRequester = _staticInitializerRequester;
        _staticInitializerRequester = symbol.descriptor;
        try {
            var value = expr(initializer);
            _staticInitializerRequester = previousRequester;
            return value;
        } catch (error:Dynamic) {
            _staticInitializerRequester = previousRequester;
            throw error;
        }
    }

    private function getOwnerStaticDuringInitialization(field:String):{handled:Bool, value:Dynamic} {
        if (_staticInitializerRequester == null || _classScope == null)
            return {handled:false, value:null};
        var symbol = _classScope.resolveClassSymbol(_staticInitializerRequester.name,
            _staticInitializerRequester);
        if (symbol == null) return {handled:false, value:null};
        return _classScope.getStaticField(symbol, field,
            function(initializer:Expr):Dynamic return evaluateOwnerStaticInitializer(symbol, initializer));
    }

    private static var _scriptClassDescriptors:Map<String, ClassDeclEx> = new Map<String, ClassDeclEx>();""",
         "dp-owner-static-field-init-helper"),
        ("""        #end
        if ((o is ScriptClass)) { // dp-psych-flxcolor-property-get""",
         """        #end
        if (Std.isOfType(o, ScriptClassSymbol)) {
            var symbol:ScriptClassSymbol = cast o;
            if (_classScope != null) {
                var result = _classScope.getStaticField(symbol, f,
                    function(initializer:Expr):Dynamic return evaluateOwnerStaticInitializer(symbol, initializer));
                if (result.handled) return result.value;
            }
            error(EUnknownVariable(f));
        }
        if ((o is ScriptClass)) { // dp-psych-flxcolor-property-get""",
         "dp-owner-static-field-get"),
        ("""    override function set( o : Dynamic, f : String, v : Dynamic ) : Dynamic {
        if ( o == null ) error(EInvalidAccess(f));
        diagnoseAlphaAccess("write", o, f, v); // dp-smoke-hscript-ex-alpha-set
        if ((o is ScriptClass)) {""",
         """    override function set( o : Dynamic, f : String, v : Dynamic ) : Dynamic {
        if ( o == null ) error(EInvalidAccess(f));
        diagnoseAlphaAccess("write", o, f, v); // dp-smoke-hscript-ex-alpha-set
        if (Std.isOfType(o, ScriptClassSymbol)) {
            if (_classScope != null && _classScope.setStaticField(cast o, f, v)) return v;
            error(EUnknownVariable(f));
        }
        if ((o is ScriptClass)) {""",
         "dp-owner-static-field-set"),
    ],
    "ScriptClass.hx": [
        ("""    private var _c:ClassDeclEx;
    private var _interp:InterpEx;
    
    public var superClass:Dynamic = null;
    
    public function new(c:ClassDeclEx, args:Array<Dynamic>) {
        _c = c;
        _interp = new InterpEx(this);
        buildCaches();""",
         """    private var _c:ClassDeclEx;
    private var _interp:InterpEx;
    private var _classScope:ScriptClassScope;
    private var pendingSuperFields:Map<String, Dynamic> = new Map();
    
    public var superClass:Dynamic = null;
    
    public function new(c:ClassDeclEx, args:Array<Dynamic>, ?classScope:ScriptClassScope) {
        _c = c;
        _classScope = classScope; // dp-owner-class-scope-ctor
        _interp = new InterpEx(this, classScope);
        if (classScope != null) classScope.seedInterpreter(_interp);
        buildCaches();""",
         "dp-owner-class-scope-ctor"),
        ("""        var classDescriptor = InterpEx.findScriptClassDescriptor(extendString);
        if (classDescriptor != null) {
            var abstractSuperClass:AbstractScriptClass = new ScriptClass(classDescriptor, args);
            superClass = abstractSuperClass;
        } else {
            var c = Type.resolveClass(extendString);
            if (c == null) {
                @:privateAccess _interp.error(ECustom("could not resolve super class: " + extendString));
            }
            superClass = Type.createInstance(c, args);
        }
    }""",
         """        var classDescriptor = _classScope == null
            ? InterpEx.findScriptClassDescriptor(extendString)
            : _classScope.findDescriptor(extendString, _c);
        if (classDescriptor != null) {
            var abstractSuperClass:AbstractScriptClass = new ScriptClass(classDescriptor, args, _classScope);
            superClass = abstractSuperClass;
        } else {
            var c:Dynamic = _classScope == null ? Type.resolveClass(extendString)
                : _classScope.findBinding(extendString, _c);
            if (c == null && _classScope == null) c = Type.resolveClass(extendString);
            if (c == null) {
                @:privateAccess _interp.error(ECustom("could not resolve explicitly bound super class: " + extendString));
            }
            try superClass = Type.createInstance(c, args) catch (error:Dynamic)
                @:privateAccess _interp.error(ECustom("could not instantiate super class " + extendString + ": " + Std.string(error)));
        }
        applyPendingSuperFields();
    }

    public function hasDeclaredField(name:String):Bool {
        if (_c == null || _c.fields == null) return false;
        for (field in _c.fields) if (field.name == name) return true;
        return false;
    }

    /** hxcpp omits Haxe properties from Reflect.hasField; inspect accessors. */
    public function hasNativeSuperField(name:String, forWrite:Bool):Bool {
        if (superClass == null) return false;
        if (Reflect.hasField(superClass, name)) return true;
        var cls = Type.getClass(superClass);
        while (cls != null) {
            var fields = Type.getInstanceFields(cls);
            var hasName = fields.indexOf(name) >= 0;
            var hasGetter = fields.indexOf("get_" + name) >= 0;
            var hasSetter = fields.indexOf("set_" + name) >= 0;
            if (forWrite) {
                if (hasGetter) return hasSetter;
                if (hasSetter || hasName) return true;
            } else if (hasName || hasGetter) {
                return true;
            }
            cls = Type.getSuperClass(cls);
        }
        return false;
    }

    public function setPendingSuperField(name:String, value:Dynamic):Void pendingSuperFields.set(name, value);
    public function hasPendingSuperField(name:String):Bool return pendingSuperFields.exists(name);
    public function getPendingSuperField(name:String):Dynamic return pendingSuperFields.get(name);

    function applyPendingSuperFields():Void {
        if (pendingSuperFields == null || !pendingSuperFields.iterator().hasNext()) return;
        for (name in pendingSuperFields.keys()) {
            var value = pendingSuperFields.get(name);
            if (Std.isOfType(superClass, ScriptClass)) {
                var parent:ScriptClass = cast superClass;
                parent.setFieldValue(name, value);
            } else if (hasNativeSuperField(name, true)) {
                Reflect.setProperty(superClass, name, value);
            } else {
                @:privateAccess _interp.error(ECustom("cannot assign pre-super field: " + name));
            }
        }
        pendingSuperFields.clear();
    }

    public function setFieldValue(name:String, value:Dynamic):Void {
        if (findVar(name) != null) _interp.variables.set(name, value);
        else if (hasNativeSuperField(name, true)) Reflect.setProperty(superClass, name, value);
        else if (Std.isOfType(superClass, ScriptClass)) cast(superClass, ScriptClass).setFieldValue(name, value);
        else throw 'field ' + name + ' does not exist in script superclass';
    }""",
         "dp-owner-class-scope-super"),
        ("""                case KVar(v):
                    _cachedVarDecls.set(f.name, v);
                    if (v.expr != null) {
                        var varValue = this._interp.expr(v.expr);
                        this._interp.variables.set(f.name, varValue);
                    }""",
         """                case KVar(v):
                    _cachedVarDecls.set(f.name, v);
                    // Haxe fields without explicit initializers still exist
                    // and start as null; seed them so constructor writes to
                    // `this.field` work before the first read.
                    var varValue:Dynamic = v.expr == null ? null : this._interp.expr(v.expr);
                    this._interp.variables.set(f.name, varValue); // dp-owner-class-null-field-initializers""",
         "dp-owner-class-null-field-initializers"),
        ("""                case KVar(v):
                    _cachedVarDecls.set(f.name, v);
                    // Haxe fields without explicit initializers still exist
                    // and start as null; seed them so constructor writes to
                    // `this.field` work before the first read.
                    var varValue:Dynamic = v.expr == null ? null : this._interp.expr(v.expr);
                    this._interp.variables.set(f.name, varValue); // dp-owner-class-null-field-initializers""",
         """                case KVar(v):
                    if (f.access.indexOf(AStatic) < 0) {
                        _cachedVarDecls.set(f.name, v);
                        // Haxe fields without explicit initializers still exist
                        // and start as null; seed them so constructor writes to
                        // `this.field` work before the first read.
                        var varValue:Dynamic = v.expr == null ? null : this._interp.expr(v.expr);
                        this._interp.variables.set(f.name, varValue); // dp-owner-class-null-field-initializers
                    } // dp-owner-static-fields-once""",
         "dp-owner-static-fields-once"),
        ("""    public function callFunction(name:String, args:Array<Dynamic> = null) {
        var field = findField(name);""",
         """    public function callFunction(name:String, args:Array<Dynamic> = null) {
        if (_classScope != null && !_classScope.isActive())
            throw '[hscript-class-scope] owner class scope has been released';
        var field = findField(name);""",
         "dp-owner-class-scope-release-guard"),
        ("""        var field = findField(name);
        var r:Dynamic = null;
        
        if (field != null) {""",
         """        var field = findField(name);
        var r:Dynamic = null;

        // dp-owner-callable-field: source classes call function-valued fields
        // such as cutscene finishCallback through another owner class.
        if (field != null && findFunction(name) == null) {
            var callable = _interp.variables.get(name);
            if (!Reflect.isFunction(callable))
                throw '[hscript-class] field ' + name + ' is not callable';
            return Reflect.callMethod(null, callable, args == null ? [] : args);
        }
        
        if (field != null) {""",
         "dp-owner-callable-field"),
        ("""            r = _interp.execute(fn.expr);
            
            for (a in fn.args) {
                if (previousValues.exists(a.name)) {
                    _interp.variables.set(a.name, previousValues.get(a.name));
                } else {
                    _interp.variables.remove(a.name);
                }
            }""",
         """            try {
                r = _interp.executeClassMethod(fn.expr);
            } catch (error:Dynamic) {
                restoreArguments(fn, previousValues);
                throw error;
            }
            restoreArguments(fn, previousValues);""",
         "dp-owner-class-nested-call-frame"),
        ("""            try {
                r = _interp.executeClassMethod(fn.expr);
            } catch (error:Dynamic) {""",
         """            try {
                r = _interp.executeClassMethod(fn.expr, [for (arg in fn.args) arg.name]); // dp-owner-class-nested-call-frame dp-owner-class-method-argument-scope
            } catch (error:Dynamic) {""",
         "dp-owner-class-method-argument-scope"),
        ("""            var fn = findFunction(name);
            var previousValues:Map<String, Dynamic> = [];
            var i = 0;
            for (a in fn.args) {
                var value:Dynamic = null;
                
                if (args != null && i < args.length) {
                    value = args[i];
                } else if (a.value != null) {
                    value = _interp.expr(a.value);
                }
                
                if (_interp.variables.exists(a.name)) {
                    previousValues.set(a.name, _interp.variables.get(a.name));
                }
                _interp.variables.set(a.name, value);
                i++;
            }
            
            try {
                r = _interp.executeClassMethod(fn.expr, [for (arg in fn.args) arg.name]); // dp-owner-class-nested-call-frame dp-owner-class-method-argument-scope
            } catch (error:Dynamic) {
                restoreArguments(fn, previousValues);
                throw error;
            }
            restoreArguments(fn, previousValues);""",
         """            var fn = findFunction(name);
            r = _interp.executeClassMethod(fn.expr,
                [for (arg in fn.args) arg.name], args == null ? [] : args,
                [for (arg in fn.args) arg.value]); // dp-owner-class-nested-call-frame dp-owner-class-method-argument-scope dp-owner-class-local-argument-values""",
         "dp-owner-class-local-argument-values"),
        ("""        } else {
            var fixedArgs = [];
            for (a in args) {
                if ((a is ScriptClass)) {
                    fixedArgs.push(cast(a, ScriptClass).superClass);
                } else {
                    fixedArgs.push(a);
                }
            }
            r = Reflect.callMethod(superClass, Reflect.field(superClass, name), fixedArgs);
        }""",
         """        } else {
            // dp-owner-native-group-super-args
            var nativeArgs = _classScope == null ? args
                : _classScope.unwrapNativeGroupArguments(superClass, name, args);
            if (nativeArgs == null) nativeArgs = [];
            var fixedArgs = [];
            for (a in nativeArgs) {
                if ((a is ScriptClass)) {
                    fixedArgs.push(cast(a, ScriptClass).superClass);
                } else {
                    fixedArgs.push(a);
                }
            }
            r = Reflect.callMethod(superClass, Reflect.field(superClass, name), fixedArgs);
        }""",
         "dp-owner-native-group-super-args"),
        ("""            var nativeArgs = _classScope == null ? args
                : _classScope.unwrapNativeGroupArguments(superClass, name, args);
            if (nativeArgs == null) nativeArgs = [];
            var fixedArgs = [];
            for (a in nativeArgs) {
                if ((a is ScriptClass)) {
                    fixedArgs.push(cast(a, ScriptClass).superClass);
                } else {
                    fixedArgs.push(a);
                }
            }
            r = Reflect.callMethod(superClass, Reflect.field(superClass, name), fixedArgs);
        }""",
         """            // dp-owner-script-super-dispatch: a subclass may inherit a
            // HScript class before the first native superclass. Keep virtual
            // lookup inside that owner-scoped chain until a native method is
            // actually reached.
            if (Std.isOfType(superClass, ScriptClass)) {
                r = cast(superClass, ScriptClass).callFunction(name, args);
            } else {
                var nativeArgs = _classScope == null ? args
                    : _classScope.unwrapNativeGroupArguments(superClass, name, args);
                if (nativeArgs == null) nativeArgs = [];
                var fixedArgs = [];
                for (a in nativeArgs) {
                    if ((a is ScriptClass)) {
                        fixedArgs.push(cast(a, ScriptClass).superClass);
                    } else {
                        fixedArgs.push(a);
                    }
                }
                r = Reflect.callMethod(superClass, Reflect.field(superClass, name), fixedArgs);
            }
        }""",
         "dp-owner-script-super-dispatch"),
        ("""        }
        return r;
    }
    
    private function findFunction(name:String):FunctionDecl {""",
         """        }
        #if flixel
        if (name == "destroy" && _classScope != null)
            _classScope.noteScriptClassDestroy(this); // dp-owner-class-basic-destroy-hook
        #end
        return r;
    }
    
    private function findFunction(name:String):FunctionDecl {""",
         "dp-owner-class-basic-destroy-hook"),
        ("""    private function findFunction(name:String):FunctionDecl {""",
         """    private function restoreArguments(fn:FunctionDecl,
        previousValues:Map<String, Dynamic>):Void {
        for (a in fn.args) {
            if (previousValues.exists(a.name)) {
                _interp.variables.set(a.name, previousValues.get(a.name));
            } else {
                _interp.variables.remove(a.name);
            }
        }
    }

    private function findFunction(name:String):FunctionDecl {""",
         "dp-owner-class-restore-args"),
    ],
    "AbstractScriptClass.hx": [
        ("""                } else if (Reflect.hasField(this.superClass, name)) {
                    return Reflect.field(this.superClass, name);""",
         """                } else if (this.hasNativeSuperField(name, false)) {
                    return Reflect.getProperty(this.superClass, name);""",
         "dp-owner-inherited-native-properties-read"),
        ("""                } else if (Reflect.hasField(this.superClass, name)) {
                    Reflect.setProperty(this.superClass, name, value);""",
         """                } else if (this.hasNativeSuperField(name, true)) {
                    Reflect.setProperty(this.superClass, name, value);""",
         "dp-owner-inherited-native-properties-write"),
        ("""                } else if (this.findVar(name) != null) {
                    var v = this.findVar(name);""",
         """                } else if (this.hasPendingSuperField(name)) {
                    return this.getPendingSuperField(name);
                } else if (this.findVar(name) != null) {
                    var v = this.findVar(name);""",
         "dp-owner-class-scope-pending-field"),
        ("""                if (this.findVar(name) != null) {
                    this._interp.variables.set(name, value);""",
         """                if (this.hasPendingSuperField(name)) {
                    this.setPendingSuperField(name, value);
                    return value;
                } else if (this.findVar(name) != null) {
                    this._interp.variables.set(name, value);""",
         "dp-owner-class-scope-pending-field-write"),
    ],
}


# Construction hooks are scoped to the importing owner. Existing native classes
# keep Type.createInstance; only explicitly registered adapters observe super().
PATCHES["ScriptClass.hx"].extend([
    ("    public var superClass:Dynamic = null;",
     """    public var superClass:Dynamic = null;
    private var derivedClass:ScriptClass; // dp-owner-construction-root
    public function constructionRoot():ScriptClass {
        return derivedClass == null ? this : derivedClass.constructionRoot();
    }""", "dp-owner-construction-root"),
    ("public function new(c:ClassDeclEx, args:Array<Dynamic>, ?classScope:ScriptClassScope) {",
     """public function new(c:ClassDeclEx, args:Array<Dynamic>, ?classScope:ScriptClassScope, ?derived:ScriptClass) {
        derivedClass = derived; // dp-owner-construction-link
        if (derived != null) derived.superClass = this;""", "dp-owner-construction-link"),
    ("new ScriptClass(classDescriptor, args, _classScope);",
     "new ScriptClass(classDescriptor, args, _classScope, this); // dp-owner-super-construction-link",
     "dp-owner-super-construction-link"),
    ("            try superClass = Type.createInstance(c, args) catch (error:Dynamic)",
     """            try {
                // dp-owner-native-construction-hooks
                if (_classScope == null) superClass = Type.createInstance(c, args);
                else _classScope.constructNativeSuper(this, c, args);
            } catch (error:Dynamic)""", "dp-owner-native-construction-hooks"),
])
PATCHES["InterpEx.hx"].append((
    '        } else if (id == "this" && _proxy != null) {\n            return _proxy;',
    '        } else if (id == "this" && _proxy != null) {\n            return _proxy.constructionRoot(); // dp-owner-derived-this-identity',
    'dp-owner-derived-this-identity'))


PATCHES["ScriptClass.hx"].append((
    "    public function hasDeclaredField(name:String):Bool {",
    """    // dp-owner-virtual-method-owner
    public function virtualMethodOwner(name:String):ScriptClass {
        var lexical:ScriptClass = this;
        while (lexical != null) {
            var field = lexical.findField(name);
            if (field != null) {
                if (lexical.findFunction(name) == null) return null;
                if (field.access.indexOf(AStatic) >= 0 || name == "new") return lexical;
                break;
            }
            lexical = Std.isOfType(lexical.superClass, ScriptClass) ? cast lexical.superClass : null;
        }
        if (lexical == null) return null;
        var current = constructionRoot();
        while (current != null) {
            if (current.findFunction(name) != null) return current;
            current = Std.isOfType(current.superClass, ScriptClass) ? cast current.superClass : null;
        }
        return lexical;
    }

    public function hasDeclaredField(name:String):Bool {""",
    "dp-owner-virtual-method-owner"))
PATCHES["InterpEx.hx"].append((
    """            if (_proxy != null && _proxy.findFunction(id) != null) {
                _nextCallObject = _proxy;
                return _proxy.resolveField(id);""",
    """            var methodOwner:AbstractScriptClass = _proxy == null ? null : _proxy.virtualMethodOwner(id);
            if (methodOwner != null) { // dp-owner-virtual-bare-method
                _nextCallObject = methodOwner;
                return methodOwner.resolveField(id);""",
    "dp-owner-virtual-bare-method"))
PATCHES["AbstractScriptClass.hx"].append((
    """                    var fn = this.findFunction(name);
                    var nargs = 0;
                    if (fn.args != null) {
                        nargs = fn.args.length;
                    }
                    switch (nargs) {
                        case 0:     return this.callFunction0.bind(name);
                        case 1:     return this.callFunction1.bind(name, _);
                        case 2:     return this.callFunction2.bind(name, _, _);
                        case 3:     return this.callFunction3.bind(name, _, _, _);
                        case 4:     return this.callFunction4.bind(name, _, _, _, _);
                        case _:     @:privateAccess this._interp.error(ECustom("only 4 params allowed in script class functions (.bind limitation)"));
                    }""",
    """                    // dp-owner-method-reference-arity
                    return Reflect.makeVarArgs(function(args:Array<Dynamic>):Dynamic {
                        return this.callFunction(name, args);
                    });""",
    "dp-owner-method-reference-arity"))


PATCHES["InterpEx.hx"].append((
    '            // Never fall through to hscript-ex\'s process-global class registry.',
    """            var native = _classScope.tryConstructNative(cl, args, _proxy == null ? null : _proxy._c);
            if (native.handled) return native.value; // dp-owner-native-direct-factory
            // Never fall through to hscript-ex's process-global class registry.""",
    'dp-owner-native-direct-factory'))



PATCHES["InterpEx.hx"].extend([
    ("    private function getOwnerStaticDuringInitialization(field:String):{handled:Bool, value:Dynamic} {",
     """    private function ownerStaticSymbol(field:String):Null<ScriptClassSymbol> {
        if (_classScope == null) return null;
        var requester = _staticInitializerRequester != null ? _staticInitializerRequester
            : _proxy == null ? null : _proxy._c;
        return _classScope.findStaticFieldSymbol(field, requester);
    }

    override function setVar(name:String, value:Dynamic) {
        var symbol = ownerStaticSymbol(name);
        if (symbol != null && _classScope.setStaticField(symbol, name, value)) return;
        super.setVar(name, value);
    } // dp-owner-lexical-static-write

    private function getOwnerStaticDuringInitialization(field:String):{handled:Bool, value:Dynamic} {""",
     "dp-owner-lexical-static-write"),
    ("""        if (_staticInitializerRequester == null || _classScope == null)
            return {handled:false, value:null};
        var symbol = _classScope.resolveClassSymbol(_staticInitializerRequester.name,
            _staticInitializerRequester);""",
     """        var symbol = ownerStaticSymbol(field); // dp-owner-lexical-static-symbol""",
     "dp-owner-lexical-static-symbol"),
    ('        if (_staticInitializerRequester != null && _classScope != null) {',
     '        if (_classScope != null && (_staticInitializerRequester != null || _proxy != null)) { // dp-owner-lexical-static-read',
     'dp-owner-lexical-static-read'),
    ("""                if (locals.get(id) == null && _classMethodLocals.indexOf(id) < 0) { // dp-owner-class-local-write-priority
                    if (_proxy != null""",
     """                if (locals.get(id) == null && _classMethodLocals.indexOf(id) < 0) { // dp-owner-class-local-write-priority
                    if (ownerStaticSymbol(id) != null) {
                        var value = expr(e2);setVar(id, value);return value;
                    } // dp-owner-lexical-static-assignment
                    if (_proxy != null""",
     "dp-owner-lexical-static-assignment"),
    ("""                if (variables.exists(id)) {
                    return {value:variables.get(id), write:function(value:Dynamic) { variables.set(id, value); }};
                }""",
     """                if (ownerStaticSymbol(id) != null) {
                    return {value:resolve(id), write:function(value:Dynamic) {setVar(id, value);}};
                } // dp-owner-lexical-static-lvalue
                if (variables.exists(id)) {
                    return {value:variables.get(id), write:function(value:Dynamic) { variables.set(id, value); }};
                }""",
     "dp-owner-lexical-static-lvalue"),
])



# A caller comparing a source result to an Int must not specialize every
# interpreted method's return type on hxcpp. This is a dynamic API boundary.
for arity in range(5):
    args = ''.join(f', arg{i}:Dynamic' for i in range(arity))
    old = f'private inline function callFunction{arity}(name:String{args}) {{'
    new = f'private inline function callFunction{arity}(name:String{args}):Dynamic {{ // dp-owner-dynamic-result-{arity}'
    PATCHES["ScriptClass.hx"].append((old, new, f'dp-owner-dynamic-result-{arity}'))
PATCHES["ScriptClass.hx"].append((
    'public function callFunction(name:String, args:Array<Dynamic> = null) {',
    'public function callFunction(name:String, args:Array<Dynamic> = null):Dynamic { // dp-owner-dynamic-call-result dp-owner-class-scope-release-guard',
    'dp-owner-dynamic-call-result'))


def patch_file(path: Path, patches: list[tuple[str, str, str]]) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text
    if "dp-owner-static-field-init-helper" not in text and "private function evaluateOwnerStaticInitializer" in text:
        text = text.replace("private function evaluateOwnerStaticInitializer(symbol:ScriptClassSymbol, initializer:Expr):Dynamic {",
                            "private function evaluateOwnerStaticInitializer(symbol:ScriptClassSymbol, initializer:Expr):Dynamic { // dp-owner-static-field-init-helper", 1)
    # Add a durable marker to owner-scope installs made before this marker
    # existed, so later focused patch additions remain safely idempotent.
    if ("dp-owner-class-scope-ctor" not in text
        and ("private var _classScope:ScriptClassScope = null;" in text
             or "private var _classScope:ScriptClassScope;" in text)
        and "_classScope = classScope;" in text):
        text = text.replace("_classScope = classScope;", "_classScope = classScope; // dp-owner-class-scope-ctor", 1)
    if ("dp-psych-flxcolor-property-get" not in text
        and "PsychFlxColorScriptAccess.isColorValue(o)" in text):
        color_access = text.index("PsychFlxColorScriptAccess.isColorValue(o)")
        script_branch = text.find("if ((o is ScriptClass)) {", color_access)
        if script_branch >= 0:
            text = text[:script_branch] + text[script_branch:].replace(
                "if ((o is ScriptClass)) {",
                "if ((o is ScriptClass)) { // dp-psych-flxcolor-property-get", 1)
    if ("dp-smoke-hscript-ex-alpha-access-helper" not in text
        and "private function diagnoseAlphaAccess" in text):
        text = text.replace("\n    }\n\n    private static var _scriptClassDescriptors",
                            "\n    } // dp-smoke-hscript-ex-alpha-access-helper\n\n    private static var _scriptClassDescriptors", 1)
    # A previous local patch run inserted the capture helper twice because
    # the indexed-read hook split its replacement string and the helper patch
    # had no durable marker. Collapse only exact duplicate helper blocks.
    capture_start = "    #if flixel\n    /** Evaluate an assignable expression once and retain a write-back target. */\n"
    capture_end = "    #end\n"
    first_capture = text.find(capture_start)
    if first_capture >= 0:
        next_capture = text.find(capture_start, first_capture + len(capture_start))
        while next_capture >= 0:
            first_end = text.find(capture_end, first_capture)
            next_end = text.find(capture_end, next_capture)
            if first_end < 0 or next_end < 0:
                break
            first_block = text[first_capture:first_end + len(capture_end)]
            next_block = text[next_capture:next_end + len(capture_end)]
            if first_block == next_block:
                text = text[:next_capture] + text[next_end + len(capture_end):]
                continue
            first_capture = next_capture
            next_capture = text.find(capture_start, first_capture + len(capture_start))
        if "dp-psych-flxcolor-capture-lvalue" not in text:
            text = text.replace(
                capture_start,
                capture_start + "    // dp-psych-flxcolor-capture-lvalue\n",
                1,
            )
    # Repair an install produced by the immediately preceding migration bug.
    # The new cnew body was inserted after the old scope block, duplicating
    # only the function header. Keep the body and collapse that exact duplicate.
    cnew_header = "    override function cnew(cl:String, args:Array<Dynamic>):Dynamic {\n"
    if cnew_header + cnew_header in text:
        text = text.replace(cnew_header + cnew_header, cnew_header, 1)
    # Upgrade installs that also staged unknown writes after the native
    # superclass was already constructed. That owner bridge is useful for
    # script fields, but it must not capture HScript locals or parameters.
    prior_pending_write = """            case EIdent(id):
                if (_proxy != null && _proxy.superClass != null && _proxy.hasNativeSuperField(id, true)) {
                    Reflect.setProperty(_proxy.superClass, id, v);
                    return v;
                } else if (_proxy != null && _proxy.superClass == null
                    && _proxy._c.extend != null && !_proxy.hasDeclaredField(id)) {
                    // Haxe constructors may assign inherited fields before super().
                    _proxy.setPendingSuperField(id, v);
                    return v;
                } else if (_proxy != null && _proxy._c.extend != null && !_proxy.hasDeclaredField(id)) {
                    // Haxe constructors may assign inherited fields before super().
                    _proxy.setPendingSuperField(id, v);
                    return v;
                }"""
    canonical_pending_write = """            case EIdent(id):
                // dp-owner-class-scope-pending-write
                // Function locals and arguments shadow inherited native fields
                // and must stay in the HScript frame.
                if (locals.get(id) == null && _classMethodLocals.indexOf(id) < 0) { // dp-owner-class-local-write-priority
                    if (_proxy != null && _proxy.superClass != null && _proxy.hasNativeSuperField(id, true)) {
                        Reflect.setProperty(_proxy.superClass, id, v);
                        return v;
                    } else if (_proxy != null && _proxy.superClass == null
                        && _proxy._c.extend != null && !_proxy.hasDeclaredField(id)) {
                        // Haxe constructors may assign inherited fields before super().
                        _proxy.setPendingSuperField(id, v);
                        return v;
                    } else if (_proxy != null && _proxy._c.extend != null && !_proxy.hasDeclaredField(id)) {
                        // Haxe constructors may assign inherited fields before super().
                        _proxy.setPendingSuperField(id, v);
                        return v;
                    }
                }"""
    if prior_pending_write in text:
        text = text.replace(prior_pending_write, canonical_pending_write, 1)
    canonical_fcall = """\toverride function fcall( o : Dynamic, f : String, args : Array<Dynamic> ) : Dynamic {
        // dp-owner-native-group-fcall-args
        if (_classScope != null) args = _classScope.unwrapNativeGroupArguments(o, f, args);
        if (_classScope != null) args = _classScope.unwrapNativeTweenArguments(o, f, args); // dp-owner-native-tween-target-args
        if ((o is ScriptClass)) {"""
    prior_fcall_variants = [
        """\toverride function fcall( o : Dynamic, f : String, args : Array<Dynamic> ) : Dynamic {
        // dp-owner-native-group-args
        if (_classScope != null) args = _classScope.unwrapNativeGroupArguments(o, f, args);
        if (_classScope != null) args = _classScope.unwrapNativeTweenArguments(o, f, args); // dp-owner-native-tween-target-args
        if ((o is ScriptClass)) {""",
        """\toverride function fcall( o : Dynamic, f : String, args : Array<Dynamic> ) : Dynamic {
        // dp-owner-native-group-args
        if (_classScope != null) args = _classScope.unwrapNativeGroupArguments(o, f, args);
        if ((o is ScriptClass)) {""",
    ]
    for prior_fcall in prior_fcall_variants:
        if prior_fcall in text:
            text = text.replace(prior_fcall, canonical_fcall, 1)
            break
    for old, new, marker in patches:
        if marker in text or new in text:
            continue
        if marker == "dp-owner-native-group-method-context":
            # Upgrade the earlier group bridge replacement, which introduced
            # the method context before the replacement carried a marker.
            prior_method_context = """    private var _nextCallObject:Dynamic = null;
    private var _nextCallMethod:String = null;
    override function resolve(id:String):Dynamic {
        _nextCallObject = null;
        _nextCallMethod = null;"""
            if prior_method_context in text:
                text = text.replace(prior_method_context, new, 1)
                continue
        if marker == "dp-owner-class-scope-cnew":
            # Upgrade installs patched by the immediately preceding revision.
            prior_scope = """        if (_classScope != null) {
            var scoped = _classScope.createInstance(cl, args, _proxy == null ? null : _proxy._c);
            if (scoped != null) return scoped;
            if (_proxy != null && _proxy._c.imports != null && _proxy._c.imports.exists(cl)) {
                var importedName = _proxy._c.imports.get(cl).join(".");
                scoped = _classScope.createInstance(importedName, args);
                if (scoped != null) return scoped;
            }
        }
        if (_scriptClassDescriptors.exists(cl)) {"""
            if prior_scope in text:
                scoped_branch = new.split("        if (_classScope != null) {", 1)[1]
                scoped_branch = "        if (_classScope != null) {" + scoped_branch.split(
                    "        if (_scriptClassDescriptors.exists(cl)) {", 1
                )[0]
                text = text.replace(
                    prior_scope,
                    scoped_branch + "        if (_scriptClassDescriptors.exists(cl)) {",
                    1,
                )
                continue
        if marker == "dp-owner-class-scope-pending-read":
            # Upgrade the pre-property-bridge patch, which already inserted
            # pending-field lookup after its superclass read check.
            prior_scoped_read = """            } else if (_proxy != null && _proxy.hasNativeSuperField(id, false)) {
                _nextCallObject = _proxy.superClass;
                return Reflect.getProperty(_proxy.superClass, id);
            } else if (_proxy != null && _proxy.hasPendingSuperField(id)) {
                return _proxy.getPendingSuperField(id);
            } else if (_proxy != null) {"""
            if prior_scoped_read in text:
                text = text.replace(prior_scoped_read, new, 1)
                continue
            prior_read = """            } else if (_proxy != null && _proxy.superClass != null && (Reflect.hasField(_proxy.superClass, id) || Reflect.getProperty(_proxy.superClass, id) != null)) {
                _nextCallObject = _proxy.superClass;
                return Reflect.getProperty(_proxy.superClass, id);
            } else if (_proxy != null && _proxy.hasPendingSuperField(id)) {
                return _proxy.getPendingSuperField(id);
            } else if (_proxy != null) {"""
            if prior_read in text:
                text = text.replace(prior_read, new, 1)
                continue
        if marker == "dp-owner-class-scope-super":
            # Migrate hscript-ex sources that already received the original
            # owner-scope patch before inherited native properties were
            # supported. The old patch inserted pending-field helpers, so the
            # original upstream block above no longer exists verbatim.
            if "public function hasNativeSuperField(name:String, forWrite:Bool)" in text:
                continue
            prior_declared = """    public function hasDeclaredField(name:String):Bool {
        if (_c == null || _c.fields == null) return false;
        for (field in _c.fields) if (field.name == name) return true;
        return false;
    }
"""
            native_field_helper = """    /** hxcpp omits Haxe properties from Reflect.hasField; inspect accessors. */
    public function hasNativeSuperField(name:String, forWrite:Bool):Bool {
        if (superClass == null) return false;
        if (Reflect.hasField(superClass, name)) return true;
        var cls = Type.getClass(superClass);
        while (cls != null) {
            var fields = Type.getInstanceFields(cls);
            var hasName = fields.indexOf(name) >= 0;
            var hasGetter = fields.indexOf("get_" + name) >= 0;
            var hasSetter = fields.indexOf("set_" + name) >= 0;
            if (forWrite) {
                if (hasGetter) return hasSetter;
                if (hasSetter || hasName) return true;
            } else if (hasName || hasGetter) {
                return true;
            }
            cls = Type.getSuperClass(cls);
        }
        return false;
    }
"""
            if prior_declared in text:
                text = text.replace(prior_declared,
                                    prior_declared + native_field_helper, 1)
                old_pending = """            } else if (superClass != null && (Reflect.hasField(superClass, name)
                || Reflect.getProperty(superClass, name) != null)) {"""
                new_pending = """            } else if (hasNativeSuperField(name, true)) {"""
                old_set = """        else if (superClass != null && Reflect.hasField(superClass, name)) Reflect.setProperty(superClass, name, value);"""
                new_set = """        else if (hasNativeSuperField(name, true)) Reflect.setProperty(superClass, name, value);"""
                if text.count(old_pending) == 1 and text.count(old_set) == 1:
                    text = text.replace(old_pending, new_pending, 1)
                    text = text.replace(old_set, new_set, 1)
                    continue
                raise RuntimeError(f"{path}: cannot migrate prior owner-scope superclass block")
        count = text.count(old)
        if count != 1:
            raise RuntimeError(f"{path}: expected one unpatched target for {marker}, found {count}")
        text = text.replace(old, new, 1)
    if text == original:
        return False
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return True


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".haxelib/hscript-ex/git/src/hscript")
    changed = []
    for filename, patches in PATCHES.items():
        path = source / filename
        if not path.is_file():
            raise SystemExit(f"hscript-ex class-scope patch target is missing: {path}")
        if patch_file(path, patches):
            changed.append(filename)
    print("patched hscript-ex owner-scoped script classes" if changed
          else "hscript-ex owner-scoped script classes already patched")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"hscript-ex owner-scope patch failed: {error}")
