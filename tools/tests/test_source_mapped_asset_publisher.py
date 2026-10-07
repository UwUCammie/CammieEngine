"""Composite receipt-bound planning for owner runtime asset classes."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP

from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


MAIN = r'''import ImportIO;
import ImportSourceSnapshot;
import PsychAssetProfile.PsychAssetProfileCandidate;
import PsychAssetProfile.PsychAssetProfileBuild;
import PsychAssetProfile.PsychAssetProfileMappedFile;
import SourceMappedAssetPublisher;
import SourceMappedAssetPublisher.SourceMappedAssetPolicy;
import SourceMappedAssetPublisher.SourceMappedAssetPlan;
import SourceMappedAssetPublisher.SourceMappedAssetPolicyView;
import SourceMappedMediaPolicy;
import SourceMappedMediaPublisher;
import haxe.Json;
import haxe.io.Path;
import sys.io.File as RawFile;
using StringTools;

class Main {
  static function check(value:Bool, message:String):Void if (!value) throw message;
  static function lower(value:String):String return value == null ? "" : value.toLowerCase();
  static function ends(value:String, suffix:String):Bool return lower(value).endsWith(suffix);
  static function starts(value:String, prefix:String):Bool return lower(value).startsWith(prefix);

  static function langPolicy():SourceMappedAssetPolicy {
    return {
      label:"language",
      beforeHash:function(source:String, mapped:String):Bool
        return ends(source, ".lang") || ends(mapped, ".lang"),
      classify:function(event:PsychAssetProfileMappedFile) {
        return ends(event.sourceRelative, ".lang") || ends(event.mappedPath, ".lang")
          ? {state:"accept"} : {state:"ignore"};
      },
      managedOutputPredicate:function(relative:String):Bool return ends(relative, ".lang"),
      classifyProjection:function(source:Null<String>, owner:Null<String>) {
        if (owner != null && (ends(owner, ".lang") || starts(owner, "translations") || owner == ""))
          return {state:"defer", ownerRelative:owner};
        if (source != null && (ends(source, ".lang") || starts(source, "assets/translations") || source == ""))
          return {state:"defer", ownerRelative:owner};
        return {state:"ignore"};
      }
    };
  }

  static function mediaPolicy(label:String, duplicate:Bool = false, ?route:String):SourceMappedAssetPolicy {
    return {
      label:label,
      beforeHash:function(source:String, mapped:String):Bool
        return ends(source, ".png") || ends(mapped, ".png"),
      classify:function(event:PsychAssetProfileMappedFile) {
        if (duplicate && ends(event.mappedPath, ".png")) return {state:"accept"};
        if ((event.type == "image" || event.type == "") && ends(event.mappedPath, ".png"))
          return route == null ? {state:"accept"} : {state:"accept", ownerRelative:route};
        return {state:"ignore"};
      },
      managedOutputPredicate:function(relative:String):Bool
        return ((relative == "images" || starts(relative, "images/"))
          || starts(relative, "libraries/ui/")) && ends(relative, ".png"),
      classifyProjection:function(source:Null<String>, owner:Null<String>) {
        if (owner != null && (owner == "" || owner == "images" || starts(owner, "images/")))
          return {state:"defer", ownerRelative:owner};
        if (source != null && (source == "" || starts(source, "assets/images")))
          return {state:"defer", ownerRelative:owner};
        return {state:"ignore"};
      }
    };
  }

  static function acceptsFirstToForeignLeaf():SourceMappedAssetPolicy {
    return {
      label:"accept-first",
      beforeHash:function(source:String, mapped:String):Bool return ends(mapped, ".png"),
      classify:function(event:PsychAssetProfileMappedFile) {
        return starts(event.sourceRelative, "assets/first/")
          ? {state:"accept", ownerRelative:"foreign/opaque.bin"} : {state:"ignore"};
      },
      managedOutputPredicate:function(relative:String):Bool return ends(relative, ".png")
    };
  }

  static function defersLaterToForeignLeaf():SourceMappedAssetPolicy {
    return {
      label:"defer-later",
      beforeHash:function(source:String, mapped:String):Bool return ends(mapped, ".png"),
      classify:function(event:PsychAssetProfileMappedFile) {
        return starts(event.sourceRelative, "assets/later/")
          ? {state:"defer", ownerRelative:"foreign/opaque.bin", reason:"fixture deferred leaf"}
          : {state:"ignore"};
      },
      managedOutputPredicate:function(relative:String):Bool return ends(relative, ".png")
    };
  }

  static function typedImagePolicy():SourceMappedAssetPolicy {
    return {
      label:"typed-image",
      beforeHash:function(source:String, mapped:String):Bool return false,
      beforeHashCandidate:function(source:String, mapped:String,
          candidate:PsychAssetProfileCandidate):Bool
        return candidate != null && candidate.type == "image" && ends(mapped, ".bin"),
      classify:function(event:PsychAssetProfileMappedFile) {
        return event.type == "image" && ends(event.mappedPath, ".bin")
          ? {state:"accept"} : {state:"ignore"};
      },
      managedOutputPredicate:function(relative:String):Bool return starts(relative, "custom/")
    };
  }

  static function unresolvedOwnerScopePolicy():SourceMappedAssetPolicy {
    return {
      label:"unresolved-owner-scope",
      beforeHash:function(source:String, mapped:String):Bool return ends(mapped, ".png"),
      classify:function(event:PsychAssetProfileMappedFile) {
        return ends(event.mappedPath, ".png")
          ? {state:"defer", ownerRelative:"", reason:"runtime package/core selection is unresolved"}
          : {state:"ignore"};
      },
      managedOutputPredicate:function(relative:String):Bool
        return starts(relative, "images/") || starts(relative, "__nmv_core/images/")
    };
  }

  static function typedProjectionPolicy():SourceMappedAssetPolicy {
    return SourceMappedMediaPolicy.psych();
  }

  static function main():Void {
    var config:Dynamic = Json.parse(RawFile.getContent("config.json"));
    var capture = ImportSourceSnapshot.capture(config.sourceRoot, config.cacheRoot,
      "Psych Engine", "0.0.17", {workerCount:1});
    check(capture.status == "complete" && capture.complete,
      "snapshot capture failed: " + capture.error);
    ImportSourceSnapshot.verify(capture.snapshotRoot, capture.snapshotId, null, null, 1);
    var content = Path.join([capture.snapshotRoot, "content"]);
    var selected = Path.join([content, config.rootRelative]);
    var buildFlags:Array<Dynamic> = (config.mode == "disabled-overlap"
      || config.mode == "typed-disabled-projection")
      ? [{name:"DISABLED_FLAG", state:"disabled", provenance:"fixture"}]
      : config.mode == "identity-legacy-deferred"
        ? [{name:"UNKNOWN_FLAG", state:"unresolved", provenance:"fixture"}] : [];
    var build:PsychAssetProfileBuild = cast {command:"", flagsComplete:false, flags:buildFlags};
    var profile = PsychAssetProfile.resolveRetained(content, capture.snapshotId,
      config.rootRelative, "Psych Engine", config.namespace, build);
    var install:String = config.install;
    var stage:String = config.stage;
    var masked:Array<String> = cast config.masked;
    var io = ImportIO.begin(install, stage, masked, true);
    io.setNamespace(selected, "Psych Engine", config.namespace);
    io.setAssetProfile(selected, content, capture.snapshotId, config.rootRelative,
      "Psych Engine", config.namespace, profile);
    if (config.mode == "tampered-file" || config.mode == "candidate-aware")
      RawFile.saveContent(Path.join([selected, config.tamperRelative]), "tampered retained file bytes");
    var owner = "assets/imported_mods/" + config.namespace;
    var destinationRoot:String = config.destinationRoot == null ? owner : config.destinationRoot;
    var language = langPolicy();
    var media = mediaPolicy("media");
    var policies:Array<SourceMappedAssetPolicy> = [];
    switch (config.mode) {
      case "dedup": policies = [media, mediaPolicy("media-shadow", true)];
      case "collision", "incomplete", "deferred", "unknown-scope", "unknown-unrelated": policies = [language, media];
      case "language", "language-unresolved", "single": policies = [language];
      case "fanout": policies = [media];
      case "route": policies = [mediaPolicy("media", false, "libraries/ui/icon.png")];
      case "disabled-overlap": policies = [media];
      case "deferred-order", "deferred-order-reversed":
        policies = [acceptsFirstToForeignLeaf(), defersLaterToForeignLeaf()];
      case "tampered-file": policies = [media];
      case "candidate-aware": policies = [typedImagePolicy()];
      case "typed-deferred-projection", "typed-disabled-projection": policies = [typedProjectionPolicy()];
      case "typed-unknown-owner-projection": policies = [typedProjectionPolicy()];
      case "identity-index": policies = [mediaPolicy("media"),
        SourceMappedMediaPolicy.limeIdentity("Psych Engine", "package")];
      case "identity-legacy", "identity-legacy-deferred": policies = [
        SourceMappedMediaPolicy.limeIdentity("Psych Engine", "package")];
      case "identity-runtime-types": policies = [];
      case "unknown-owner-scope": policies = [unresolvedOwnerScopePolicy()];
      case "cancel": policies = [language, media];
      case "publish-cancel": policies = [media];
      default: throw "unknown mode " + config.mode;
    }
    var cancelled:Void->Bool = config.mode == "cancel" ? function() return true : function() return false;
    var plan:SourceMappedAssetPlan = config.mode == "identity-runtime-types"
      ? SourceMappedMediaPublisher.prepare(selected, "Psych Engine", destinationRoot)
      : SourceMappedAssetPublisher.prepareMany(selected, "Psych Engine", destinationRoot, policies, cancelled);
    var singleView:Null<SourceMappedAssetPolicyView> = config.mode == "single"
      ? SourceMappedAssetPublisher.prepare(selected, "Psych Engine", destinationRoot, language, cancelled)
      : null;
    var languageView = SourceMappedAssetPublisher.policyView(plan, "language");
    var mediaView = SourceMappedAssetPublisher.policyView(plan, "media");
    var published = 0;
    if (config.mode == "identity-legacy") {
      var acceptedSource = Path.join([selected, "assets/images/icon.png"]);
      check(SourceMappedMediaPublisher.skipIdentityLegacy(plan, acceptedSource,
        Path.join([owner, "images/icon.png"])),
        "an accepted Lime identity source remained eligible for the broad raw tree copy");
      check(!SourceMappedMediaPublisher.skipIdentityLegacy(plan,
        Path.join([selected, "outside/unmapped.png"]), Path.join([owner, "outside/unmapped.png"])),
        "an unrelated raw source was suppressed by identity planning");
      check(SourceMappedMediaPublisher.skipIdentityLegacy(null,
        Path.join([selected, ".cammie-asset-identities/psych.json"]), ""),
        "a donor sidecar path was not reserved from raw copying");
      check(SourceMappedMediaPublisher.skipIdentityLegacy(null, "",
        Path.join([owner, ".cammie-asset-identities/psych.json"])),
        "an owner sidecar destination was not reserved from raw copying");
    }
    if (config.mode == "identity-legacy-deferred") {
      check(SourceMappedMediaPublisher.skipIdentityLegacy(plan,
        Path.join([selected, "outside/unmapped.png"]),
        Path.join([owner, "deferred/blob.weird"])),
        "a deferred Lime identity destination remained eligible for raw copying");
      check(!SourceMappedMediaPublisher.skipIdentityLegacy(plan,
        Path.join([selected, "outside/unmapped.png"]), Path.join([owner, "outside/unmapped.png"])),
        "identity uncertainty suppressed an unrelated raw destination");
    }
    if (config.mode == "identity-runtime-types") {
      check(!plan.failed && plan.authoritative && plan.identityPublication != null,
        "the complete Lime identity/media plan failed before publication: " + plan.diagnostics.join("\n"));
      check(plan.files.length == 5 && plan.identityPublication.index.entries.length == 5,
        "known shader, video, binary, text, or aliased image was deferred by identity typing");
      var index = plan.identityPublication.index;
      function entry(id:String):Dynamic {
        for (item in index.entries) if (item.id == id) return item;
        return null;
      }
      check(entry("icon-alias") != null && entry("icon-alias").type == "IMAGE",
        "a distinct Lime ID did not retain the mapped image identity");
      check(entry("assets/shaders/glow.frag") != null
        && entry("assets/shaders/glow.frag").type == "TEXT",
        "hxp.System.isText did not capture the shader's effective Lime type");
      check(entry("assets/videos/intro.mp4") != null
        && entry("assets/videos/intro.mp4").type == "BINARY",
        "binary video bytes did not retain their exact effective Lime type");
      check(entry("assets/data/binary.dat") != null && entry("assets/data/binary.dat").type == "BINARY"
        && entry("assets/data/text.dat") != null && entry("assets/data/text.dat").type == "TEXT",
        "unknown-extension binary/text assets were not classified by the retained byte probe");
      SourceMappedMediaPublisher.publish(plan, function(source:String, destination:String):Void {
        io.copy(source, destination);
        published++;
      }, function() return false, function(path:String, content:String):Void {
        RawFile.saveContent(io.writePath(path), content);
      });
      check(published == 5 && !plan.cancelled && !plan.failed,
        "the source-backed media outputs were not published alongside the identity index");
    }
    if (config.mode == "dedup" || config.mode == "fanout" || config.mode == "incomplete"
      || config.mode == "language"
      || config.mode == "publish-cancel")
      SourceMappedAssetPublisher.publish(plan, function(source:String, destination:String):Void {
        io.copy(source, destination);
        published++;
      }, config.mode == "publish-cancel" ? function() return true : function() return false);
    if (config.mode == "identity-index") {
      var missingWriterCalls = 0;
      var missingWriterFailed = false;
      try SourceMappedAssetPublisher.publish(plan, function(source:String, destination:String):Void {
        missingWriterCalls++;
      }) catch (_:Dynamic) missingWriterFailed = true;
      check(missingWriterFailed && missingWriterCalls == 0,
        "an identity plan without a sidecar writer did not fail before copying");
      SourceMappedAssetPublisher.publish(plan, function(source:String, destination:String):Void {
        io.copy(source, destination);
        published++;
      }, function() return false, function(path:String, content:String):Void {
        RawFile.saveContent(io.writePath(path), content);
      });
      check(!plan.failed && !plan.cancelled && plan.identityPublication != null,
        "identity sidecar was not prepared for the exact owner plan");
      check(plan.identityPublication.path == owner + "/.cammie-asset-identities/psych.json",
        "identity sidecar path is not the full install-relative destination");
      check(published == plan.files.length && published == 1,
        "raw identity file was not deduplicated with the media policy output");
      check(plan.identityPublication.index.entries.length == 1
        && plan.identityPublication.index.entries[0].id == "assets/images/icon.png"
        && plan.identityPublication.index.entries[0].ownerRelative == "images/icon.png",
        "Lime ID and physical owner path were not kept separate");
      var sidecar = haxe.Json.parse(RawFile.getContent(io.readPath(plan.identityPublication.path)));
      check(sidecar.complete == false,
        "an incomplete retained mapping was falsely certified complete");
    }
    if (config.mode == "single")
      SourceMappedAssetPublisher.publishView(singleView, function(source:String, destination:String):Void {
        io.copy(source, destination);
        published++;
      });
    if (config.mode == "dedup") {
      check(!plan.failed && plan.files.length == 1, "one event accepted by two policies was not deduplicated");
      check(plan.files[0].policyLabels.length == 2, "deduplicated output lost its policy labels");
      check(languageView.files.length == 0 && mediaView.files.length == 1,
        "policy view exposed an output to an unrelated policy");
      check(published == 1, "composite publish wrote the same output more than once");
      check(SourceMappedAssetPublisher.blocksLegacySource(mediaView,
        plan.files[0].sourcePath), "accepted source was not reserved from legacy fallback");
      check(SourceMappedAssetPublisher.isExplicitlyBlockedSource(mediaView,
        plan.files[0].sourcePath), "accepted source was not recorded as an explicit source block");
    } else if (config.mode == "collision") {
      check(plan.failed && plan.files.length == 0,
        "cross-policy owner collision did not fail the complete batch: " + Json.stringify({
          failed:plan.failed, files:[for (file in plan.files) {
            source:file.sourceRelative, owner:file.ownerRelative, type:file.event.type,
            policies:file.policyLabels
          }], diagnostics:plan.diagnostics
        }));
      check(languageView.ambiguousDestinations.keys().hasNext()
        && mediaView.ambiguousDestinations.keys().hasNext(),
        "collision was not reflected in both involved policy views");
      check(RawFile.getContent(Path.join([install, config.priorRelative])) == "prior-managed-media",
        "collision modified prior managed output");
    } else if (config.mode == "language") {
      check(!plan.failed && plan.authoritative && plan.files.length == 1
        && plan.files[0].ownerRelative == "translations/source.lang",
        "language mapping did not retain its original target contract: " + Json.stringify({
          profileComplete:profile.complete, failed:plan.failed,
          files:[for (file in plan.files) {source:file.sourceRelative, owner:file.ownerRelative}],
          diagnostics:plan.diagnostics
        }));
      check(published == 1 && RawFile.getContent(io.readPath(plan.files[0].destinationPath)) == "language bytes",
        "receipt-verified language bytes were not published exactly once");
      check(SourceMappedAssetPublisher.blocksLegacySource(languageView,
        Path.join([selected, "misc/unrelated.lang"]))
        && !SourceMappedAssetPublisher.isExplicitlyBlockedSource(languageView,
          Path.join([selected, "misc/unrelated.lang"])),
        "authoritative language policy was not separated from explicit source blocks");
    } else if (config.mode == "single") {
      check(singleView != null && !singleView.failed && singleView.files.length == 1,
        "single-policy compatibility adapter did not return a scoped view");
      check(published == 1, "single-policy view did not publish its planned file");
    } else if (config.mode == "language-unresolved") {
      check(!plan.failed && languageView.files.length == 0,
        "enabled language source was selected despite an unresolved competitor");
      check(SourceMappedAssetPublisher.skipLegacy(languageView,
        Path.join([selected, "assets/enabled/same.lang"]),
        Path.join([owner, "data/same.lang"])),
        "unresolved language owner path remained eligible for legacy fallback");
    } else if (config.mode == "incomplete") {
      check(!plan.failed && !plan.authoritative && languageView.legacyAllowed && mediaView.legacyAllowed,
        "incomplete but scoped mappings unexpectedly disabled legacy compatibility");
      check(plan.files.length == 1 && mediaView.files.length == 1,
        "enabled media mapping was not published additively");
      check(SourceMappedAssetPublisher.blocksLegacySource(mediaView, plan.files[0].sourcePath),
        "mapped media source remained eligible for a second legacy output");
      check(SourceMappedAssetPublisher.isExplicitlyBlockedSource(mediaView, plan.files[0].sourcePath),
        "mapped source was not exposed to the generic tree-copy filter");
      check(!SourceMappedAssetPublisher.blocksLegacySource(mediaView,
        Path.join([selected, "misc/unmapped.png"])), "unrelated legacy source was blocked");
      check(published == 1, "incomplete profile mapping did not publish once");
    } else if (config.mode == "deferred") {
      check(plan.failed && mediaView.failed,
        "deferred media scope did not protect a prior managed output");
      check(SourceMappedAssetPublisher.skipLegacy(mediaView,
        Path.join([selected, "assets/images/hidden/icon.png"]),
        Path.join([owner, "images/hidden/icon.png"])),
        "deferred media source or destination remained eligible for legacy fallback");
      check(!languageView.blockAllLegacy,
        "unrelated language policy inherited the media-only uncertainty");
      check(RawFile.getContent(Path.join([install, config.priorRelative])) == "prior-managed-media",
        "deferred scope changed the prior managed media bytes");
    } else if (config.mode == "unknown-scope") {
      check(plan.failed && mediaView.blockAllLegacy,
        "unknown mapping scope failed to protect managed media outputs");
      check(SourceMappedAssetPublisher.blocksLegacySource(mediaView,
        Path.join([selected, "misc/unrelated.png"]))
        && !SourceMappedAssetPublisher.isExplicitlyBlockedSource(mediaView,
          Path.join([selected, "misc/unrelated.png"])),
        "class-wide legacy uncertainty was confused with an explicit source projection");
      check(RawFile.getContent(Path.join([install, config.priorRelative])) == "prior-managed-media",
        "unknown scope changed prior managed media bytes");
    } else if (config.mode == "unknown-unrelated") {
      check(!plan.failed && mediaView.blockAllLegacy,
        "unknown mapping scope failed because an unrelated owner output exists");
    } else if (config.mode == "fanout") {
      check(!plan.failed && plan.files.length == 2,
        "one source mapped to two distinct valid targets was deduplicated or rejected");
      check(plan.files[0].sourcePath == plan.files[1].sourcePath
        && plan.files[0].destinationPath != plan.files[1].destinationPath,
        "fan-out plan did not retain source identity and distinct targets");
      check(published == 2, "both distinct runtime targets were not published");
    } else if (config.mode == "route") {
      check(!plan.failed && plan.files.length == 1
        && plan.files[0].ownerRelative == "libraries/ui/icon.png",
        "policy runtime ownerRelative override was not applied");
    } else if (config.mode == "disabled-overlap") {
      check(!plan.failed && !plan.authoritative && plan.files.length == 1
        && plan.files[0].ownerRelative == "images/icon.png",
        "disabled source projection suppressed a disjoint enabled mapping of the same source");
      check(SourceMappedAssetPublisher.blocksLegacySource(mediaView, plan.files[0].sourcePath),
        "disabled and enabled source collision did not suppress only the legacy path");
    } else if (config.mode == "deferred-order" || config.mode == "deferred-order-reversed") {
      var acceptedView = SourceMappedAssetPublisher.policyView(plan, "accept-first");
      var deferredView = SourceMappedAssetPublisher.policyView(plan, "defer-later");
      check(acceptedView.files.length == 0 && plan.files.length == 0,
        "an accepted output survived a deferred projection for the same owner path");
      check(SourceMappedAssetPublisher.isExplicitlyBlockedDestination(deferredView,
        Path.join([owner, "foreign/opaque.bin"])),
        "deferred destination was not exposed as an explicit legacy block");
      if (config.priorRelative != null && config.priorRelative != "") {
        check(plan.failed,
          "an exact deferred leaf did not protect previously owned output with a non-policy extension");
        check(RawFile.getContent(Path.join([install, config.priorRelative])) == "prior-managed-media",
          "deferred cross-policy leaf changed the prior owned output");
      } else {
        check(!plan.failed,
          "a deferred path without prior owned data failed the complete plan");
      }
    } else if (config.mode == "tampered-file") {
      check(plan.failed && plan.files.length == 0 && published == 0,
        "receipt hash verification failure left mapped files publishable");
      check(RawFile.getContent(Path.join([install, config.priorRelative])) == "prior-managed-media",
        "receipt hash verification failure modified previously owned bytes");
    } else if (config.mode == "candidate-aware") {
      check(!plan.failed && plan.files.length == 1
        && plan.files[0].ownerRelative == "custom/icon.bin",
        "candidate-aware prehash selection did not preserve a typed asset with an arbitrary target");
    } else if (config.mode == "typed-deferred-projection") {
      var typedView = SourceMappedAssetPublisher.policyView(plan, SourceMappedMediaPolicy.PSYCH_LABEL);
      check(plan.failed && plan.files.length == 0,
        "an unresolved typed arbitrary-target projection did not protect its prior owner output");
      check(SourceMappedAssetPublisher.isExplicitlyBlockedDestination(typedView,
        Path.join([owner, "custom/icon.bin"])),
        "typed unresolved target was not exposed as an exact legacy destination block");
      check(RawFile.getContent(Path.join([install, config.priorRelative])) == "prior-managed-media",
        "typed unresolved target changed prior owner bytes");
    } else if (config.mode == "typed-disabled-projection") {
      var typedView = SourceMappedAssetPublisher.policyView(plan, SourceMappedMediaPolicy.PSYCH_LABEL);
      check(!plan.failed && plan.files.length == 0,
        "a known disabled typed target was treated as unresolved or remained publishable");
      check(SourceMappedAssetPublisher.blocksLegacySource(typedView,
        Path.join([selected, "assets/image-source/icon.bin"])),
        "known disabled typed source remained eligible for legacy fallback");
      check(SourceMappedAssetPublisher.isExplicitlyBlockedDestination(typedView,
        Path.join([owner, "custom/icon.bin"])),
        "known disabled typed target remained eligible for legacy fallback");
      check(RawFile.getContent(Path.join([install, config.priorRelative])) == "prior-managed-media",
        "planning a disabled typed target changed prior owner bytes");
    } else if (config.mode == "typed-unknown-owner-projection") {
      var typedView = SourceMappedAssetPublisher.policyView(plan, SourceMappedMediaPolicy.PSYCH_LABEL);
      check(plan.failed && typedView.blockAllLegacy && typedView.suppressAllMapped
        && plan.files.length == 0,
        "an unresolved symbolic typed target did not close its unknown owner scope");
      check(RawFile.getContent(Path.join([install, config.priorRelative])) == "prior-managed-media",
        "unresolved symbolic target changed custom prior owner bytes");
    } else if (config.mode == "unknown-owner-scope") {
      var unresolvedView = SourceMappedAssetPublisher.policyView(plan, "unresolved-owner-scope");
      check(unresolvedView.blockAllLegacy && unresolvedView.suppressAllMapped
        && unresolvedView.files.length == 0,
        "unresolved package/core scope guessed a mapped path or left legacy copying open");
      check(plan.failed == (config.priorRelative != null && config.priorRelative != ""),
        "unknown runtime scope did not fail exactly when prior scoped output existed");
    } else if (config.mode == "cancel") {
      check(plan.cancelled && plan.files.length == 0 && published == 0,
        "cancelled planning selected or published files");
    } else if (config.mode == "publish-cancel") {
      check(plan.cancelled && plan.files.length == 1 && published == 0,
        "publication cancellation did not stop before copying the planned output");
    }
    ImportIO.end();
    RawFile.saveContent("result.json", Json.stringify({
      profileComplete:profile.complete,
      failed:plan.failed, cancelled:plan.cancelled, authoritative:plan.authoritative,
      published:published, files:[for (file in plan.files) {
        sourceRelative:file.sourceRelative, ownerRelative:file.ownerRelative,
        destinationPath:file.destinationPath, policyLabels:file.policyLabels
      }], diagnostics:plan.diagnostics
    }));
  }
}'''


BASE_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/images" rename="assets/images" />
  <assets path="assets/translations" rename="assets/translations" />
</project>
'''

COLLISION_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/media" rename="assets">
    <image name="source.png" rename="images/shared.png" />
  </assets>
  <assets path="assets/translations" rename="assets">
    <template name="source.lang" rename="images/shared.png" />
  </assets>
</project>
'''

INCOMPLETE_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/images" rename="assets/images" />
  <assets path="assets/hidden" rename="assets/images/hidden" if="UNKNOWN_FLAG" />
</project>
'''

LANGUAGE_UNRESOLVED_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/enabled" rename="assets/data" />
  <assets path="assets/unresolved" rename="assets/data" if="UNKNOWN_FLAG" />
</project>
'''

DISABLED_OVERLAP_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/images" rename="assets/images" />
  <assets path="assets/images" rename="assets/disabled" if="DISABLED_FLAG" />
  <assets path="assets/missing" rename="assets/images/missing" if="UNKNOWN_FLAG" />
</project>
'''

UNKNOWN_SCOPE_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/$UNKNOWN_SOURCE" rename="assets" />
</project>
'''

FANOUT_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/images" rename="assets/one/images" />
  <assets path="assets/images" rename="assets/two/images" />
</project>
'''

CANDIDATE_AWARE_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/image-source" rename="assets/custom" type="image" />
  <assets path="assets/audio-source" rename="assets/sounds" type="sound" />
</project>
'''

DEFERRED_ORDER_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/first" rename="assets">
    <image name="source.png" rename="images/shared.png" />
  </assets>
  <assets path="assets/later" rename="assets">
    <image name="source.png" rename="images/shared.png" />
  </assets>
</project>
'''

DEFERRED_ORDER_REVERSED_PROJECT = '''<?xml version="1.0"?>
<project>
  <assets path="assets/later" rename="assets">
    <image name="source.png" rename="images/shared.png" />
  </assets>
  <assets path="assets/first" rename="assets">
    <image name="source.png" rename="images/shared.png" />
  </assets>
</project>
'''


def write_bytes(root, relative, data):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


class SourceMappedAssetPublisherTest(unittest.TestCase):
    def run_fixture(self, mode, project, files, *, masked=(), destination_root=None,
                    tamper_relative="assets/audio-source/theme.ogg"):
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="source-mapped-assets-", dir=TEST_TMP)
        self.addCleanup(temporary.cleanup)
        work = Path(temporary.name)
        source = work / "donor"
        source.mkdir()
        (source / "Project.xml").write_text(project, encoding="utf-8", newline="\n")
        for relative, data in files.items():
            write_bytes(source, relative, data)
        install = work / "install"
        stage = install / "import-cache/staging/session"
        stage.mkdir(parents=True)
        masked_paths = []
        prior_relative = ""
        for relative in masked:
            prior_relative = relative
            prior = install / relative
            prior.parent.mkdir(parents=True, exist_ok=True)
            prior.write_bytes(b"prior-managed-media")
            masked_paths.append(relative)
        config = {
            "mode": mode,
            "sourceRoot": str(source),
            "cacheRoot": str(install / "import-cache/sources"),
            "rootRelative": "",
            "namespace": "source-mapped-assets-fixture",
            "install": str(install),
            "stage": str(stage),
            "masked": masked_paths,
            "priorRelative": prior_relative,
            "destinationRoot": destination_root,
            "tamperRelative": tamper_relative,
        }
        (work / "Main.hx").write_text(MAIN, encoding="utf-8", newline="\n")
        (work / "config.json").write_text(json.dumps(config), encoding="utf-8", newline="\n")
        tjson = work / "tjson"
        tjson.mkdir()
        (tjson / "TJSON.hx").write_text('''package tjson;
class TJSON {}
enum EncodeStyle { Full; }
class TJSONEncoder {
 public function new() {}
 public function doEncode(value:Dynamic, ?style:String):String return haxe.Json.stringify(value);
 public function encodeValue(value:Dynamic, style:EncodeStyle, depth:Int):String return haxe.Json.stringify(value);
}''', encoding="utf-8", newline="\n")
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        result = subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--run", "Main"],
            cwd=work, env=env, text=True, capture_output=True, timeout=90,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads((work / "result.json").read_text(encoding="utf-8"))

    def test_single_verified_event_is_shared_between_policies_and_published_once(self):
        result = self.run_fixture("dedup", BASE_PROJECT, {
            "assets/images/icon.png": b"image bytes",
        })
        self.assertFalse(result["failed"])
        self.assertEqual(result["published"], 1)
        self.assertEqual(len(result["files"]), 1)
        self.assertEqual(set(result["files"][0]["policyLabels"]), {"media", "media-shadow"})

    def test_lime_identity_index_shares_the_union_walk_and_requires_staged_writer(self):
        result = self.run_fixture("identity-index", BASE_PROJECT, {
            "assets/images/icon.png": b"image bytes",
        })
        self.assertFalse(result["failed"], result["diagnostics"])
        self.assertEqual(result["published"], 1)
        self.assertEqual(len(result["files"]), 1)

    def test_identity_global_filter_suppresses_only_claimed_paths_and_reserved_sidecars(self):
        result = self.run_fixture("identity-legacy", BASE_PROJECT, {
            "assets/images/icon.png": b"image bytes",
            "outside/unmapped.png": b"unmapped bytes",
        })
        self.assertFalse(result["failed"])

    def test_identity_global_filter_honors_deferred_destination_without_blanket_suppression(self):
        project = '''<project><assets path="assets/deferred" rename="assets/deferred"
          if="UNKNOWN_FLAG" /></project>'''
        result = self.run_fixture("identity-legacy-deferred", project, {
            "assets/deferred/blob.weird": b"unresolved identity bytes",
            "outside/unmapped.png": b"unmapped bytes",
        })
        self.assertFalse(result["failed"])

    def test_composite_identity_keeps_media_and_unknown_extension_asset_types(self):
        project = '''<project>
  <assets path="assets/images/icon.png" rename="assets/images/icon.png" id="icon-alias" />
  <assets path="assets/shaders/glow.frag" rename="assets/shaders/glow.frag" />
  <assets path="assets/videos/intro.mp4" rename="assets/videos/intro.mp4" />
  <assets path="assets/data/binary.dat" rename="assets/data/binary.dat" />
  <assets path="assets/data/text.dat" rename="assets/data/text.dat" />
</project>'''
        result = self.run_fixture("identity-runtime-types", project, {
            "assets/images/icon.png": b"png fixture bytes",
            "assets/shaders/glow.frag": b"void main() { gl_FragColor = vec4(1.0); }\n",
            "assets/videos/intro.mp4": b"\x00" * 128,
            "assets/data/binary.dat": b"\x00" * 128,
            "assets/data/text.dat": b"text content with an unknown extension\n",
        })
        self.assertFalse(result["failed"], result["diagnostics"])
        self.assertEqual(len(result["files"]), 5)

    def test_language_policy_view_preserves_exact_mapped_target_and_bytes(self):
        result = self.run_fixture("language", BASE_PROJECT, {
            "assets/translations/source.lang": b"language bytes",
        })
        self.assertFalse(result["failed"])
        self.assertEqual(result["published"], 1)
        self.assertEqual(result["files"][0]["ownerRelative"], "translations/source.lang")

    def test_single_policy_adapter_returns_publishable_scoped_view(self):
        result = self.run_fixture("single", BASE_PROJECT, {
            "assets/translations/source.lang": b"language bytes",
        })
        self.assertFalse(result["failed"])
        self.assertEqual(result["published"], 1)

    def test_unresolved_language_competitor_blocks_owner_path_before_legacy_fallback(self):
        result = self.run_fixture("language-unresolved", LANGUAGE_UNRESOLVED_PROJECT, {
            "assets/enabled/same.lang": b"enabled bytes",
            "assets/unresolved/same.lang": b"unresolved bytes",
        })
        self.assertFalse(result["failed"])
        self.assertEqual(result["files"], [])

    def test_cross_policy_collision_is_found_before_write_and_preserves_prior_bytes(self):
        result = self.run_fixture("collision", COLLISION_PROJECT, {
            "assets/media/source.png": b"image bytes",
            "assets/translations/source.lang": b"mapped language bytes",
        }, masked=("assets/imported_mods/source-mapped-assets-fixture/images/shared.png",))
        self.assertTrue(result["failed"])
        self.assertEqual(result["published"], 0)
        self.assertEqual(result["files"], [])

    def test_incomplete_profile_adds_mapping_and_blocks_only_mapped_source_fallback(self):
        result = self.run_fixture("incomplete", INCOMPLETE_PROJECT, {
            "assets/images/icon.png": b"image bytes",
            "assets/hidden/icon.png": b"unresolved bytes",
            "misc/unmapped.png": b"unrelated bytes",
        })
        self.assertFalse(result["failed"])
        self.assertFalse(result["authoritative"])
        self.assertEqual(result["published"], 1)
        self.assertEqual(result["files"][0]["ownerRelative"], "images/icon.png")

    def test_deferred_media_projection_protects_managed_media_without_blocking_language(self):
        result = self.run_fixture("deferred", INCOMPLETE_PROJECT, {
            "assets/images/icon.png": b"image bytes",
            "assets/hidden/icon.png": b"unresolved bytes",
        }, masked=("assets/imported_mods/source-mapped-assets-fixture/images/hidden/icon.png",))
        self.assertTrue(result["failed"])
        self.assertEqual(result["published"], 0)

    def test_unenumerable_scope_fails_only_when_prior_media_output_is_owned(self):
        result = self.run_fixture("unknown-scope", UNKNOWN_SCOPE_PROJECT, {},
            masked=("assets/imported_mods/source-mapped-assets-fixture/images/stale.png",))
        self.assertTrue(result["failed"])

    def test_unenumerable_scope_does_not_fail_for_unrelated_prior_owner_output(self):
        result = self.run_fixture("unknown-unrelated", UNKNOWN_SCOPE_PROJECT, {},
            masked=("assets/imported_mods/source-mapped-assets-fixture/data/registry.json",))
        self.assertFalse(result["failed"])

    def test_owner_relative_override_routes_a_verified_file_to_runtime_library_path(self):
        result = self.run_fixture("route", BASE_PROJECT, {
            "assets/images/icon.png": b"image bytes",
        })
        self.assertEqual(len(result["files"]), 1)
        self.assertEqual(result["files"][0]["ownerRelative"], "libraries/ui/icon.png")

    def test_disabled_projection_blocks_legacy_but_keeps_disjoint_enabled_mapping(self):
        result = self.run_fixture("disabled-overlap", DISABLED_OVERLAP_PROJECT, {
            "assets/images/icon.png": b"image bytes",
            "assets/missing/icon.png": b"unresolved bytes",
        })
        self.assertFalse(result["failed"])
        self.assertEqual(result["files"][0]["ownerRelative"], "images/icon.png")

    def test_late_cross_policy_deferred_leaf_removes_earlier_accept_and_protects_exact_owned_path(self):
        result = self.run_fixture("deferred-order", DEFERRED_ORDER_PROJECT, {
            "assets/first/source.png": b"accepted source",
            "assets/later/source.png": b"deferred source",
        }, masked=("assets/imported_mods/source-mapped-assets-fixture/foreign/opaque.bin",))
        self.assertTrue(result["failed"])
        self.assertEqual(result["published"], 0)
        self.assertEqual(result["files"], [])

    def test_early_cross_policy_deferred_leaf_still_removes_later_accept(self):
        result = self.run_fixture("deferred-order-reversed", DEFERRED_ORDER_REVERSED_PROJECT, {
            "assets/first/source.png": b"accepted source",
            "assets/later/source.png": b"deferred source",
        })
        self.assertFalse(result["failed"])
        self.assertEqual(result["published"], 0)
        self.assertEqual(result["files"], [])

    def test_receipt_hash_failure_fails_batch_without_changing_prior_owned_bytes(self):
        result = self.run_fixture("tampered-file", BASE_PROJECT, {
            "assets/images/icon.png": b"original source image bytes",
        }, masked=("assets/imported_mods/source-mapped-assets-fixture/images/icon.png",),
            tamper_relative="assets/images/icon.png")
        self.assertTrue(result["failed"])
        self.assertEqual(result["published"], 0)
        self.assertEqual(result["files"], [])

    def test_candidate_aware_filter_keeps_typed_arbitrary_target_and_skips_unrelated_hash(self):
        result = self.run_fixture("candidate-aware", CANDIDATE_AWARE_PROJECT, {
            "assets/image-source/icon.bin": b"typed image bytes",
            "assets/audio-source/theme.ogg": b"audio not selected",
        }, tamper_relative="assets/audio-source/theme.ogg")
        self.assertFalse(result["failed"])
        self.assertEqual(len(result["files"]), 1)
        self.assertEqual(result["files"][0]["ownerRelative"], "custom/icon.bin")

    def test_unresolved_typed_arbitrary_target_preserves_prior_owner_output(self):
        project = '''<project><assets path="assets/image-source" rename="assets/custom"
          type="image" if="UNKNOWN_FLAG" /></project>'''
        result = self.run_fixture("typed-deferred-projection", project, {
            "assets/image-source/icon.bin": b"typed image bytes",
        }, masked=("assets/imported_mods/source-mapped-assets-fixture/custom/icon.bin",))
        self.assertTrue(result["failed"])
        self.assertEqual(result["published"], 0)
        self.assertEqual(result["files"], [])

    def test_disabled_typed_arbitrary_target_blocks_legacy_without_failing_clean_prune(self):
        project = '''<project><assets path="assets/image-source" rename="assets/custom"
          type="image" if="DISABLED_FLAG" /></project>'''
        result = self.run_fixture("typed-disabled-projection", project, {
            "assets/image-source/icon.bin": b"typed image bytes",
        }, masked=("assets/imported_mods/source-mapped-assets-fixture/custom/icon.bin",))
        self.assertFalse(result["failed"])
        self.assertEqual(result["published"], 0)
        self.assertEqual(result["files"], [])

    def test_unresolved_symbolic_typed_target_preserves_any_prior_owner_output(self):
        project = '''<project><assets path="assets/image-source"
          rename="assets/${UNKNOWN_TARGET}" type="image" /></project>'''
        result = self.run_fixture("typed-unknown-owner-projection", project, {
            "assets/image-source/blob.bin": b"typed image bytes",
        }, masked=("assets/imported_mods/source-mapped-assets-fixture/custom/blob.bin",))
        self.assertTrue(result["failed"])
        self.assertEqual(result["published"], 0)
        self.assertEqual(result["files"], [])

    def test_unresolved_owner_scope_preserves_either_runtime_subtree(self):
        result = self.run_fixture("unknown-owner-scope", BASE_PROJECT, {
            "assets/images/icon.png": b"source image",
        }, masked=("assets/imported_mods/source-mapped-assets-fixture/__nmv_core/images/icon.png",))
        self.assertTrue(result["failed"])
        self.assertEqual(result["published"], 0)
        self.assertEqual(result["files"], [])

    def test_one_source_can_map_to_two_distinct_owner_targets(self):
        result = self.run_fixture("fanout", FANOUT_PROJECT, {
            "assets/images/icon.png": b"image bytes",
        })
        self.assertFalse(result["failed"])
        self.assertEqual(result["published"], 2)
        self.assertEqual({file["ownerRelative"] for file in result["files"]},
            {"one/images/icon.png", "two/images/icon.png"})

    def test_cancelled_walk_returns_no_publishable_files(self):
        result = self.run_fixture("cancel", BASE_PROJECT, {
            "assets/images/icon.png": b"image bytes",
        })
        self.assertTrue(result["cancelled"])
        self.assertEqual(result["published"], 0)
        self.assertEqual(result["files"], [])

    def test_cancelled_publication_does_not_copy_a_planned_file(self):
        result = self.run_fixture("publish-cancel", BASE_PROJECT, {
            "assets/images/icon.png": b"image bytes",
        })
        self.assertTrue(result["cancelled"])
        self.assertEqual(result["published"], 0)


if __name__ == "__main__":
    unittest.main()
