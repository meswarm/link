# Link R2 Mobile Alignment Design

## Goal

Align the Link middleware with the mobile app's current R2 attachment protocol so
that both sides produce and consume the same R2 references for room-shared media.

This alignment covers:

- room-shared R2 prefix discovery from Matrix room state
- object key layout under the shared prefix
- removal of `?mime=` from newly generated `r2://` references
- media type detection by object-key directory first, extension second
- image-only multimodal conversion inside Link (`[image:path:mime]`)

This change does **not** add multimodal handling for video, audio, or generic
files. Those media types should interoperate over the protocol, but only images
will be converted into model-consumable local inputs in this phase.

## Background

The mobile app has moved to a new protocol:

- the room-shared object prefix is read from a Matrix state event
- uploaded objects are grouped under `imgs`, `videos`, `audios`, or `files`
- new `r2://` references no longer include a `?mime=` query parameter
- renderers infer media type from object-key structure and then file extension

The current Link middleware is not yet aligned:

- it uploads with a flat timestamp-based key and no room prefix
- it does not read `com.talk.r2_prefix` room state
- it still contains logic that reads MIME from the `r2://` query
- it only resolves image-style `r2://` Markdown references

## Source of Truth

The mobile-side protocol reference is documented in:

- `~/Code/meswarm/talk/talk/docs/r2-room-prefix-and-mime-alignment.md`

For this project, that document becomes the interoperability source of truth.

## Protocol Requirements

### 1. Room-shared prefix

Link must read the room-shared R2 prefix from Matrix room state:

- `type = "com.talk.r2_prefix"`
- `state_key = ""`
- `content.prefix = "<room-shared-prefix>"`

The prefix:

- does not include the bucket
- is shared by all participants in the room
- must be validated locally before use

### 2. Prefix validation

Link must use the same acceptance rules as the mobile app:

- trim whitespace before validation
- empty after trim means "not configured"
- reject `\`
- reject leading `/`
- reject trailing `/`
- reject empty path segments (`//`)
- reject `.` and `..` segments

If the prefix is absent or invalid, Link must treat room-scoped R2 upload as
blocked and must not silently generate a fallback prefix.

### 3. Bucket vs prefix

Bucket remains local client configuration and continues to come from Link's
environment configuration:

- `R2_BUCKET`

Prefix comes from room state and is not stored in Agent YAML or `.env`.

### 4. Object key layout

Every new uploaded object key must use this structure:

```text
{prefix}/{imgs|videos|audios|files}/{timestamp}-{safeFileName}
```

Examples:

```text
subhub/imgs/1776581000000-photo.png
subhub/videos/1776580034770-1000009240.mp4
team-a/A-room/files/1776581200000-report.pdf
```

### 5. MIME usage

MIME remains important, but its role changes.

Link must still use MIME for:

- the upload `Content-Type`
- attachment directory selection (`imgs/videos/audios/files`)
- Markdown generation on send

Link must no longer use MIME for:

- generating `?mime=` in `r2://` refs
- primary render-time media detection

### 6. New `r2://` ref format

New references must be generated as:

```text
r2://{bucket}/{objectKey}
```

Do not append:

```text
?mime=...
```

### 7. Markdown generation

Link-generated Markdown should match the mobile app:

- image -> `![name](r2://...)`
- video -> `![name（视频）](r2://...)`
- audio -> `![name（音频）](r2://...)`
- generic file -> `[name](r2://...)`

This is a protocol-level requirement even though only images will be promoted to
multimodal model input in this phase.

## Receiving and Local Processing

### 1. Media type detection

When Link receives an `r2://` reference, it must determine media type in this
order:

1. inspect object-key path segments:
  - `/imgs/`
  - `/videos/`
  - `/audios/`
  - `/files/`
2. if path segments are insufficient, fall back to file extension

New behavior must not depend on `?mime=`.

### 2. Local download targets

Link should continue using:

- `work_dir/media_cache/` for downloaded R2-backed files
- `work_dir/inbox/` for Matrix-native media downloads

This keeps the current storage separation:

- `inbox/` = Matrix-delivered raw media
- `media_cache/` = R2-resolved shared attachments

### 3. Image-only multimodal bridge

For image references only, after download Link should replace the original
Markdown image reference in the internal message text with:

```text
[image:/absolute/local/path:image/<subtype>]
```

This is an internal Link-to-LLM bridge format, not a cross-client protocol
format.

It exists so Link can:

- download the remote shared attachment locally
- hand the local image to the model as multimodal input
- keep the user-facing protocol in pure Markdown + `r2://` refs

### 4. Non-image media in this phase

Video, audio, and generic files should be recognized and cached consistently,
but they should not be converted into multimodal model payloads in this phase.

If needed, Link may preserve them as textual attachment descriptions for the LLM.

## Middleware Changes by Area

### 1. Protocol utility layer

Add a shared R2 protocol helper layer responsible for:

- prefix validation
- MIME-to-directory mapping
- filename sanitization
- object-key construction
- `r2://` parsing
- media-kind inference from object key and extension

This avoids duplicating protocol logic across Agent, Matrix, and media storage
layers.

### 2. Matrix integration

Add room-state access so Link can fetch `com.talk.r2_prefix` per room.

Requirements:

- retrieve the current state event on demand or via cache
- validate `content.prefix`
- surface missing/invalid prefix as an actionable error

### 3. R2 upload flow

Change upload behavior from flat timestamp naming to room-scoped object-key
generation using:

- room prefix
- MIME-derived directory
- sanitized filename

Upload must keep the original MIME as `Content-Type`.

### 4. Outbound message generation

When Link sends R2-backed attachments, it must generate mobile-aligned Markdown
instead of relying on query-string MIME hints.

### 5. Inbound parsing

Replace image-query-centric parsing with protocol-driven parsing:

- recognize supported R2-backed Markdown links
- infer media type from path/extension
- download to `media_cache/`
- only convert image references into `[image:...]`

## Error Handling

### Prefix errors

If room prefix is absent or invalid:

- block room-scoped R2 upload
- log a clear diagnostic
- notify the caller with a message that the room's `com.talk.r2_prefix` must be
configured or fixed

### Download errors

If an R2-backed image cannot be downloaded:

- do not crash the main message flow
- degrade to a textual attachment placeholder
- preserve enough text for the LLM to continue the conversation

### MIME uncertainty

If MIME cannot be determined from directory or extension:

- treat the attachment as a generic file for protocol/rendering purposes
- for downloaded content, fall back to `application/octet-stream` where needed

## Compatibility Policy

This change targets the new protocol and does not prioritize legacy
`?mime=`-based behavior.

Implications:

- newly generated Link refs must never include `?mime=`
- legacy refs are not the primary compatibility target
- any temporary compatibility logic for old refs should be isolated and optional,
not central to the new flow

## Out of Scope

This phase does not include:

- video understanding by the model
- audio understanding by the model
- generic file understanding by the model
- backward-compatibility guarantees for legacy `?mime=` refs
- changing bucket ownership rules or moving bucket config into room state

## Test Plan Requirements

The implementation plan must include tests for:

- prefix validation parity with the mobile rules
- MIME-to-directory mapping
- sanitized filename behavior
- object-key construction
- new `r2://bucket/objectKey` generation without query params
- outbound Markdown generation for image/video/audio/file
- inbound media-kind inference by directory then extension
- image-only conversion to `[image:path:mime]`
- non-image handling staying non-multimodal

## Risks

### 1. Room state access complexity

Reading room state introduces new Matrix integration complexity.

Mitigation:

- isolate state-fetching logic behind a focused helper
- cache per room where safe

### 2. Partial protocol alignment

Changing only the receive path or only the upload path would leave Link out of
sync with the mobile client.

Mitigation:

- implement upload and receive alignment in the same feature set

### 3. Over-expanding scope into full multimodal media

It is tempting to add video/audio processing now that protocol work is underway.

Mitigation:

- explicitly keep multimodal conversion image-only in this phase
- keep non-image paths protocol-correct but text-oriented

## Success Criteria

The work is successful when:

1. Link uploads R2 objects under the room-shared prefix using the same directory
  scheme as mobile
2. Link emits `r2://bucket/objectKey` refs with no MIME query parameter
3. Link can consume new mobile-generated image refs and convert them to
  `[image:local-path:mime]` for the LLM
4. Link no longer relies on `?mime=` as the primary media-typing mechanism
5. Link remains image-only for multimodal processing in this phase

