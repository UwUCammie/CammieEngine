# Cammie Engine multiplayer protocol (v1)

Shared contract between the engine client (this repo) and the uwucammie.com
server (`Burnout-3-Recomp/server/site`). Both sides implement exactly this; any
change bumps `PROTOCOL` and is made on both sides together.

## Product summary

- Score-race lobbies: 2 to 16 players play the same chart at the same time,
  each on the player side, with a live scoreboard and a shared results screen.
- Identity is the shared uwucammie.com account. The game never sees a password.
- Songs the joiner lacks are relayed from the host's game through the server.
  The server never writes song content to disk.
- Downloaded content lives in a separate multiplayer cache on the joiner and
  always runs sandboxed.
- Scores are computed by the server from streamed inputs (input replay judging).
- Match history, profiles and per-song global leaderboards are stored.

## Constants

| Name | Value |
|---|---|
| `PROTOCOL` | 1 |
| Endpoint | `wss://play.uwucammie.com/cammie-engine/mp` (DNS-only host, nginx WebSocket proxy to the site app) |
| HTTP API base | `https://uwucammie.com/api/` |
| Local testing | `CAMMIE_MP_ENDPOINT=http://127.0.0.1:<port>` (loopback only) points the game at `tools/mp_local_server.py` |
| Project id | `cammie-engine` |
| Max players per lobby | 16 |
| Max package size per song | 250 MiB (sum of unique file sizes) |
| Max file count per package | 4096 |
| Max single file | 250 MiB |
| Chunk size | 256 KiB binary frames |
| Relay rate per lobby | 12 MiB/s aggregate outbound, server-wide cap 60 MiB/s |
| Max JSON frame | 64 KiB |
| Score frame rate | 4 Hz per player |

## 1. Sign-in (HTTP, reuses game-auth)

Every POST must send `Origin: https://uwucammie.com` and `Content-Type: application/json`
(the site's security middleware refuses anything else). Bodies stay under 16 KiB.

1. `POST /api/game-auth/start {"project":"cammie-engine","version":"<engine version>"}`
   returns `device_id, device_secret, user_code, verification_uri, expires_in, interval`.
   The game opens `verification_uri` (`https://uwucammie.com/account/?device=XXXX-XXXX`)
   in the system browser and shows `user_code`. Burnout keeps working unchanged: no
   `project` means `burn3`, which keeps its exact version check.
2. The account page asks the signed-in user to approve; the reply names the game.
3. `POST /api/game-auth/poll {"device_id","device_secret"}` every `interval` seconds until
   `status` is `approved`; it then returns `session_id`, `session_secret` (30 days), `name`
   and `account_id`. The game keeps the session in its save, never in `options.json`.
4. Each connection: `POST /api/game-auth/resume {"project":"cammie-engine","version",
   "session_id","session_secret"}` returns a one-use ticket `{ticket, secret, name,
   account_id}` valid for 180 s. 401 `session_revoked` means sign in again.

Tickets carry their project: Burnout's matchmaker refuses a Cammie Engine ticket and the
other way round. Sessions show on the account page's Sessions screen as "Cammie Engine";
revoking one closes the sockets admitted through it.

## 2. WebSocket transport

Text frames carry one JSON object `{"t": "<type>", ...}`. Binary frames carry
content chunks (section 5). Unknown `t` values are ignored by clients and
rejected by the server with `error`. The server pings every 15 s; 45 s of
silence closes the socket.

### Handshake

1. Server -> `{"t":"challenge","nonce":"<32 hex>","protocol":1}`
2. Client -> `{"t":"hello","protocol":1,"version":"<engine version>","ticket":"<id>",
   "proof":"<hex HMAC-SHA256(ticket_secret, 'CE-MP-AUTH\n'+ticket+'\n'+nonce+'\n'+version)>"}`
3. Server -> `{"t":"welcome","account_id","name","server_time_ms"}` or `{"t":"error","code"}` and close.

Error codes: `protocol_mismatch`, `version_mismatch`, `signin_required`,
`signin_expired`, `signin_invalid`, `session_revoked`, `rate_limited`,
`lobby_full`, `lobby_not_found`, `lobby_password`, `not_host`, `bad_request`,
`package_too_large`, `content_unavailable`, `server_busy`.

### Clock

`{"t":"time","client_ms"}` -> `{"t":"time","client_ms","server_ms"}`. Clients
estimate offset from the lowest-RTT of 8 samples and refresh every 30 s.

## 3. Lobbies

- `{"t":"lobby_list"}` -> `{"t":"lobby_list","lobbies":[{id,name,host,players,capacity,locked,state,song}]}`
- `{"t":"lobby_create","name","password"?,"capacity"}` -> `lobby_state`
- `{"t":"lobby_join","id"|"code","password"?}` -> `lobby_state`
- `{"t":"lobby_leave"}`
- Host only: `{"t":"lobby_settings","name"?,"capacity"?,"password"?,"allowed_modifiers":[...]}`,
  `{"t":"lobby_kick","account_id"}`, `{"t":"lobby_transfer_host","account_id"}`.
- `lobby_state` (broadcast on every change):
  `{id, code, name, host, capacity, locked, state: "idle"|"preparing"|"countdown"|"playing"|"results",
    song: SongSelection|null, players:[{account_id,name,ready,has_song,progress,modifiers}]}`
- Host leaving transfers host to the longest-present player; empty lobbies close.
- Join codes are 6 characters from `ABCDEFGHJKMNPQRSTUVWXYZ23456789`.

### Song selection

Host -> `{"t":"song_select","selection":SongSelection}`

```
SongSelection = {
  "title": string, "difficulty": string,
  "package": PackageManifest,      // section 5
  "chart_sha256": string,          // sha256 of the chart file bytes as stored
  "judge": string,                 // judge preset id, lobby-wide
  "scripted": bool                 // song has scripts that may alter the note timeline
}
```

Each player's `modifiers` may only contain ids from the lobby's
`allowed_modifiers`, which may only contain the visual-only set:
`flipped`, `vanish`, `invis`, `snake`, `drunk`. The server rejects anything else.
Practice, demo, solo, duo, opponent play, health and speed modifiers are never
allowed online. Personal options that are not modifiers (scroll speed, downscroll,
offsets, note skins) stay personal.

Players -> `{"t":"ready","ready":bool,"modifiers":[...]}`. Ready requires
`has_song` (all package files present and verified).

### Start

When the host sends `{"t":"start"}` and every present player is ready, the server
broadcasts `{"t":"countdown","start_server_ms","seed"}`; `start_server_ms` is at
least 3 s ahead. `seed` (uint32) seeds `FlxG.random` and every script-visible RNG
for the match so scripted timelines are reproducible. Each client starts song
position 0 at `start_server_ms` converted through its clock offset.

## 4. Gameplay streams

All times are song-position milliseconds as the client's judge sees them (after the
player's personal audio offset, reported once and clamped to +-500 ms).

- `{"t":"play_begin","offset_ms","length_ms","windows":{"sick","good","bad","shit"},"modifiers"}`.
  `windows` are the ms limits the song is judged with (a wayoff hit counts as shit, so
  `shit` is the wayoff limit). Wider than Classic's sick/good/bad (45/90/135) or Judge 1's
  wayoff (270) makes the play unranked. In a lobby `modifiers` must equal the ready ones.
- `{"t":"notes","seq","notes":[[time_ms,lane,length_ms],...]}`: the effective judgeable
  timeline as notes are generated or added, in timeline order (index = position in this
  stream). A note with `length_ms > 0` also owes a hold-end judgement.
- `{"t":"input","seq","events":[[time_ms,lane,down],...]}`: every key press and release.
- `{"t":"judge","seq","items":[[note_index,part,judgement,offset_ms],...]}`: part 0 is the
  head, 1 the hold end; judgement 4 sick, 3 good, 2 bad, 1 shit, 0 miss; `offset_ms` is
  signed (positive late) and null for a miss or a hold end.
- `{"t":"score","score","acc","combo","miss"}` at most 4 Hz: display only, relayed as
  `{"t":"scores","players":[{account_id,score,acc,combo,miss,quit}]}`.
- `{"t":"play_end","failed":bool}`, sent when the song ends or the player dies, before any end screen a
  script shows.
- Server -> `{"t":"results","players":[ResultRow],"ranked":bool,"reason":string|null}` once
  every player has ended, quit or timed out (the longest `length_ms` reported so far + 30 s after the start).

`ResultRow = {account_id, name, score, accuracy, max_combo, rank, modifiers, failed, quit,
judgements:{sick,good,bad,shit,miss}}`, all computed by the server.

Solo plays use the same streams outside a lobby: `play_begin` carries
`"solo":{"chart_sha256","difficulty","title"}` and `play_end` is answered with
`{"t":"solo_result","result":ResultRow,"ranked","reason","board","placed"}`.

## 5. Content packages and relay

```
PackageManifest = {
  "files": [{"path": string, "size": int, "sha256": string}],   // sorted by path
  "total": int,                                                 // sum of unique sizes
  "id": string                                                  // sha256 of the canonical JSON of files
}
```

- `path` is a forward-slash relative path inside the engine's asset root
  (`assets/...`). Server and client reject absolute paths, `..`, backslashes,
  drive letters, NUL, control characters, reserved Windows names, and paths
  longer than 240 characters. Allowed extensions are data/media only:
  `json jsonc txt xml png ogg wav mp3 mp4 webm ttf otf frag vert hx hxs hscript lua fnt`
  (scripts allowed, but they only ever run sandboxed on joiners).
- The host builds the manifest from a static dependency resolver (chart, its
  folder, audio, registered characters, stage, UI pack, note types, preload.txt)
  plus the asset paths the host's engine recorded while playing that song before.
- Joiners compare against their multiplayer cache (content-addressed by file
  sha256) and their own installed library (by path + hash), then request only
  what is missing:
  `{"t":"want","package_id","sha256":[...]}`.
- Server forwards wants to the host. Host sends
  `{"t":"chunk_begin","sha256","size"}` then binary frames
  `[32-byte sha256][8-byte big-endian offset][payload <= 256 KiB]`.
  The server forwards each frame immediately to the requesting players, holds
  no more than 4 MiB per lobby in memory, applies the rate limits, never writes
  to disk, and drops the lobby's transfer if a host exceeds the package total.
- Joiners write chunks to a temp file, verify sha256 on completion, then move it
  into `mpcache/files/<sha256[0:2]>/<sha256>`. Hash mismatch discards the file
  and re-requests once, then reports `content_unavailable`.
- Progress: `{"t":"progress","received","total","complete"}` from joiner, reflected in
  `lobby_state.players[].progress`; `complete: true` (every file present and verified) sets `has_song`.
- The cache has a user-set size limit (option, default 2 GiB) with LRU eviction
  by last match use. Cache content is mounted as a read-only overlay only while
  that match's song plays, and every script loaded from it is sandboxed.

## 6. Timelines, judging and ranking

The server never runs the song and never parses charts. It checks each play against the
player's own streams (`cammie_scoring.verify` on the server):

- every judgeable head and hold end is judged exactly once (a failed run may stop early);
- each hit's tier fits its offset under the declared windows (1 ms tolerance);
- each hit is backed by a press in that lane at `note time + offset` (4 ms tolerance), and
  one press pays for one note only;
- a hold end judged sick was held until at most 120 ms before its end;
- 50 or more hits with an unstable rate under 3.0 count as autoplay.

The score is then computed by the server from the verified judgements in object-time
order with the engine's standardised formula (golden values shared with
`tools/tests/test_standard_score.py`). A play that fails a check still shows, marked
unranked with the reason.

Timeline consensus covers every song, scripted or not:

- in a match, every player's timeline hash (sha256 of the canonical `notes` stream) must
  be equal, otherwise the match is unranked (`the players' songs did not match`);
- a leaderboard is keyed by `sha256(chart_sha256 | difficulty | window signature)` and
  opens once 3 distinct verified accounts have reported the same timeline hash for it;
  from then on only plays with that timeline count, and a later different report from
  another account flags the board for review.

## 7. Persistence (SpacetimeDB records)

- `ce-match:<id>`: lobby name, title, difficulty, time, ResultRows.
- `ce-history:<account_id>`: `{ids}`, the last 100 match ids.
- `ce-timeline:<board key>`: `{reports:{account: hash}, reference, flagged}`.
- `ce-best:<account_id>:<board key>`: the account's best row on that board.
- `ce-board:<board key>`: `{title, difficulty, rows}`, top 100, best per account.
- Public reads: `GET /api/cammie-engine/lobbies`, `GET /api/cammie-engine/leaderboards/<key>`,
  `GET /api/cammie-engine/profiles/<account_id>`.
