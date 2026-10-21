#!/usr/bin/env python3
"""Local end-to-end multiplayer run against the real site app, without touching uwucammie.com.

The site app (Burnout-3-Recomp/server/site) runs on loopback with in-memory storage. A scripted
host player creates a lobby and offers a song the engine does not have: a copy of one of the
engine's own songs under a new folder, so every file is relayed, cached, mounted and played
sandboxed on the engine side. The engine joins as the second player through the loopback
override (MpEndpoint: CAMMIE_MP_ENDPOINT, CAMMIE_MP_TEST_SESSION, CAMMIE_MP_SMOKE_JOIN).

Run it with the server's Python environment (aiohttp, argon2, cryptography):
  python tools/mp_local_server.py --site <server/site> --state tmp/mp-e2e/state.json --song tutorial

It writes the state file ({endpoint, session, code}) once the lobby exists, waits for the
engine to finish the song, prints a JSON summary and exits 0 only when the engine's play was
received in full and verified by the server.
"""
import argparse
import asyncio
import hashlib
import hmac
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SMOKE_FOLDER = "mpsmoke"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--site", required=True, type=Path, help="Burnout-3-Recomp/server/site")
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--song", default="tutorial", help="engine song folder to offer under a new name")
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--start-delay", type=float, default=0, help="seconds the lobby waits with everyone ready")
    return parser.parse_args()


def song_package(song):
    """The offered song: the engine song's data and audio under SMOKE_FOLDER, chart renamed to match."""
    files = {}
    data_dir, audio_dir = ROOT / "assets/data" / song, ROOT / "assets/songs" / song
    chart = data_dir / f"{song}.json"
    if not chart.is_file():
        raise SystemExit(f"no chart {chart}")
    for path in sorted(audio_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in (".ogg", ".mp3", ".wav"):
            files[f"assets/songs/{SMOKE_FOLDER}/{path.name}"] = path.read_bytes()
    raw = chart.read_text(encoding="utf-8").strip()
    parsed = json.loads(raw[:raw.rindex("}") + 1])
    parsed["song"]["song"] = SMOKE_FOLDER
    chart_bytes = json.dumps(parsed).encode()
    files[f"assets/data/{SMOKE_FOLDER}/{SMOKE_FOLDER}.json"] = chart_bytes
    return files, hashlib.sha256(chart_bytes).hexdigest()


async def main():
    args = parse_args()
    sys.path.insert(0, str(args.site))
    sys.path.insert(0, str(args.site / "tests"))
    os.environ["COOKIE_SECURE"] = "0"
    from aiohttp import ClientSession, web
    from cryptography.fernet import Fernet
    import app as site
    import cammie_mp
    from storage import Record
    from test_sessions import FakeStorage, Browser, FAST_HASHER, FIREFOX

    site.HASHER = FAST_HASHER
    verdicts = {}
    original_judge = cammie_mp.CammieMultiplayer.judge

    def judge(self, player, play):
        row, reason = original_judge(self, player, play)
        verdicts[player.account_id] = {"reason": reason, "notes": len(play.notes), "inputs": len(play.inputs),
                                       "judges": len(play.judges), "score": row["score"], "rank": row["rank"]}
        return row, reason

    cammie_mp.CammieMultiplayer.judge = judge
    app = site.create_app()
    app.cleanup_ctx.clear()
    db = app["db"] = FakeStorage()
    app["mail_cipher"] = Fernet(Fernet.generate_key())
    for ident, name in (("engine", "Engine Tester"), ("host", "Smoke Host")):
        email = f"{ident}@example.com"
        account = {"id": ident, "name": name, "email": email, "verified": True, "created": 1, "epoch": 1,
                   "password": FAST_HASHER.hash("fixture-password-long")}
        await db.transact(Record(f"account:{ident}", {}, 0).change(account),
                          Record("email:" + site.digest(email), {}, 0).change({"id": ident}))
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", args.port).start()
    base = f"http://127.0.0.1:{args.port}"

    class Case:
        class server:
            @staticmethod
            def make_url(path):
                from yarl import URL
                return URL(base + path)

        @staticmethod
        def assertEqual(a, b, message=None):
            if a != b:
                raise AssertionError(f"{a!r} != {b!r}: {message}")

    async def game_session(ident):
        browser = Browser(Case, FIREFOX)
        await browser.call("POST", "/login", {"email": f"{ident}@example.com", "password": "fixture-password-long"})
        device = await browser.call("POST", "/start", {"project": "cammie-engine", "version": "local"}, prefix="/api/game-auth")
        await browser.call("POST", "/approve", {"code": device["user_code"]}, prefix="/api/game-auth")
        grant = await browser.call("POST", "/poll", {"device_id": device["device_id"], "device_secret": device["device_secret"]},
                                   prefix="/api/game-auth")
        await browser.http.close()
        return grant

    engine_grant = await game_session("engine")
    host_grant = await game_session("host")
    http = ClientSession()
    async with http.post(base + "/api/game-auth/resume", headers={"Origin": site.ORIGIN},
                         json={"project": "cammie-engine", "version": "local", "session_id": host_grant["session_id"],
                               "session_secret": host_grant["session_secret"]}) as response:
        ticket = await response.json()
    ws = await http.ws_connect(base + "/cammie-engine/mp", max_msg_size=8 << 20)
    challenge = await ws.receive_json()
    proof = hmac.new(ticket["secret"].encode(), f"CE-MP-AUTH\n{ticket['ticket']}\n{challenge['nonce']}\nlocal".encode(),
                     hashlib.sha256).hexdigest()
    await ws.send_json({"t": "hello", "protocol": 1, "version": "local", "ticket": ticket["ticket"], "proof": proof})
    welcome = await ws.receive_json()
    assert welcome["t"] == "welcome", welcome

    async def next_message(kind, check=lambda m: True, timeout=args.timeout):
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            message = await asyncio.wait_for(ws.receive(), max(0.1, deadline - loop.time()))
            if message.type.name != "TEXT":
                if message.type.name in ("CLOSE", "CLOSED", "ERROR"):
                    raise SystemExit("host socket closed")
                continue
            data = json.loads(message.data)
            if data.get("t") == "want":
                await send_files(data["sha256"])
                continue
            if data.get("t") == kind and check(data):
                return data

    files, chart_sha = song_package(args.song)
    by_sha = {hashlib.sha256(blob).hexdigest(): blob for blob in files.values()}
    sent_bytes = 0

    async def send_files(hashes):
        nonlocal sent_bytes
        for digest in hashes:
            blob = by_sha[digest]
            await ws.send_json({"t": "chunk_begin", "sha256": digest, "size": len(blob)})
            for offset in range(0, len(blob), 256 * 1024):
                piece = blob[offset:offset + 256 * 1024]
                await ws.send_bytes(bytes.fromhex(digest) + offset.to_bytes(8, "big") + piece)
                sent_bytes += len(piece)

    await ws.send_json({"t": "lobby_create", "name": "Local smoke", "capacity": 2})
    lobby = await next_message("lobby_state")
    args.state.parent.mkdir(parents=True, exist_ok=True)
    args.state.write_text(json.dumps({"endpoint": base, "code": lobby["code"], "session": {
        "id": engine_grant["session_id"], "secret": engine_grant["session_secret"], "name": engine_grant["name"],
        "accountId": engine_grant["account_id"]}}), encoding="utf-8")
    print(f"lobby {lobby['code']} on {base}", flush=True)

    await next_message("lobby_state", lambda m: len(m["players"]) == 2)
    entries = sorted(({"path": p, "size": len(b), "sha256": hashlib.sha256(b).hexdigest()} for p, b in files.items()),
                     key=lambda e: e["path"])
    unique = {e["sha256"]: e["size"] for e in entries}
    manifest = {"files": entries, "total": sum(unique.values()),
                "id": hashlib.sha256(cammie_mp.canonical_manifest(entries).encode()).hexdigest()}
    await ws.send_json({"t": "song_select", "selection": {"title": "Local smoke", "difficulty": "normal", "package": manifest,
                                                          "chart_sha256": chart_sha, "judge": "classic", "scripted": False}})
    await ws.send_json({"t": "ready", "ready": True, "modifiers": []})
    await next_message("lobby_state", lambda m: all(p["ready"] for p in m["players"]) and len(m["players"]) == 2)
    await asyncio.sleep(args.start_delay)
    await ws.send_json({"t": "start"})
    countdown = await next_message("countdown")
    # The host gives up at once; the match then waits for the engine's whole song.
    await ws.send_json({"t": "play_begin", "offset_ms": 0, "length_ms": 1000,
                        "windows": {"sick": 45, "good": 90, "bad": 135, "shit": 203}, "modifiers": []})
    await ws.send_json({"t": "play_end", "failed": True})
    results = await next_message("results")
    await ws.close()
    await http.close()
    await runner.cleanup()
    engine = verdicts.get(engine_grant["account_id"], {})
    summary = {"relayed_bytes": sent_bytes, "package_bytes": manifest["total"], "seed": countdown["seed"],
               "engine": engine, "rows": results["players"], "ranked": results["ranked"], "note": results["reason"]}
    print(json.dumps(summary, indent=1), flush=True)
    ok = engine.get("notes", 0) > 0 and engine.get("reason") in (None, "failed") and sent_bytes == manifest["total"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
