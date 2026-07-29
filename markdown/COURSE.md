# Protocol Stack Architecture Course

**Self-contained study guide for airplane use.** Open the companion HTML at `html/index.html` for animated diagrams.

Analyzed implementations: **rodbus** (Modbus), **dnp3** (Distributed Network Protocol 3), **libIEC61850** (International Electrotechnical Commission 61850).

---

# Chapter 1 — Why Protocol Stacks Exist

## The problem in plain language

Industrial plants speak many “languages” at once. A relay may publish events on Ethernet using one standard. A remote terminal unit on a serial line may answer register reads using another. A master station may poll devices using a third. Your job, as someone building a **protocol translation service**, is to sit between these dialects and move meaning safely from one wire format to another — without corrupting values, losing events, or locking up under bad traffic.

A **protocol** is an agreed set of rules for:

1. How bytes are framed on the wire
2. Who may speak when
3. How requests and replies are matched
4. What the bytes *mean* (coils, analogs, structured data objects, files, …)

A **protocol stack** is the software layered like a sandwich so each rule lives in one place. The bottom layer deals with sockets and serial ports. The middle layers deal with framing and reliability. The top layers deal with application meaning and with the callbacks your product exposes to users.

## What a translation service does

Think of a translation service as a bilingual operator:

```
Device A (Modbus registers)  ──►  Internal model  ──►  Device B (DNP3 points)
         wire bytes                    meaning              wire bytes
```

The middle is the valuable part. Good translators do **not** copy raw bytes from one protocol into another. They:

- Decode inbound frames into a **canonical domain model** (points, quality, timestamps, datasets)
- Apply policy (scaling, deadbands, access control, rate limits)
- Encode outbound frames in the other protocol’s rules

That middle model is what keeps your product from becoming a tangle of special cases.

## Why not one big function?

A single function that “reads from the socket and writes Modbus” works for a weekend demo and fails in production because:

| Concern | What goes wrong without layers |
|---------|--------------------------------|
| Partial reads | Transmission Control Protocol delivers arbitrary chunks, not whole messages |
| Noise on serial | One bad byte desynchronizes the entire stream |
| Reconnects | Socket death and protocol session death are different events |
| Concurrent clients | Shared mutable state races |
| Observability | You cannot tell *which layer* failed |
| Testing | You cannot unit-test framing without a live device |

Layers turn those concerns into separate, testable machines.

## The three libraries in this course (preview)

| Stack | Complexity | Signature idea |
|-------|------------|----------------|
| **rodbus** | Low–medium | One application data unit, two coats (Transmission Control Protocol header versus Remote Terminal Unit checksum) |
| **dnp3** | Medium–high | Classic three protocol layers (link, transport, application) plus master/outstation session actors |
| **libIEC61850** | High | Abstract services over a live data tree, plus a separate publisher/subscriber plane for fast Ethernet messages |

You will see the same recurring shapes in all three: **physical input/output**, **frame parsers as state machines**, **session tasks as actors**, and **handlers as the product’s extension points**.

## Learning goals for this course

By the end you should be able to:

1. Draw a layer diagram for a new protocol before writing code
2. Choose a parsing strategy (sync hunt, length prefix, checksum, schema-driven) with clear trade-offs
3. Design a session actor that correlates requests and replies safely
4. Sketch a translation service with a canonical model between two stacks
5. Explain why **rodbus**, **dnp3**, and **libIEC61850** made the choices they did

## Vocabulary for chapter 1

| Term | Meaning |
|------|---------|
| Frame | A delimited group of bytes with a header and often a checksum |
| Payload | The inner bytes a layer carries for the layer above |
| Session | Long-lived protocol state for one connection or channel |
| Canonical model | Your product’s internal representation of process data |
| Translation service | Software that maps meaning between two or more protocols |

## Self-check

1. Why is “copy bytes from protocol A to protocol B” usually wrong?
2. Name three failures that appear when framing and session logic share one function.
3. What sits in the middle of a good translator?



---


# Chapter 2 — Mental Models

Mental models are the pictures you keep in your head while coding. The wrong picture leads to tangled modules. The three libraries in this course share a small set of pictures. Learn them once; reuse them forever.

## Model 1 — The layered sandwich

Every industrial stack in this folder is a vertical sandwich:

```
┌──────────────────────────────────────┐
│ Application / session / handlers     │  meaning, timers, user callbacks
├──────────────────────────────────────┤
│ Framing / transport assembly         │  length, sequence, checksum
├──────────────────────────────────────┤
│ Physical input and output            │  sockets, serial, Ethernet, Transport Layer Security
└──────────────────────────────────────┘
```

**Rules of the sandwich:**

- A layer may talk only to the layers next to it.
- Lower layers never know about “coils” or “logical nodes”.
- Upper layers never hunt for sync bytes.

**rodbus** makes this especially clear with three decode levels for logging: physical, frame, and application. **dnp3** uses the same idea across link, transport, and application. **libIEC61850** stretches the sandwich taller (Transport Packet, Connection-Oriented Transport Protocol, session, presentation, Association Control, Manufacturing Message Specification, then the abstract service interface).

## Model 2 — The byte pipeline

Bytes flow upward as they are decoded, and downward as they are encoded:

```
read socket → buffer → frame parser → application parse → handler
handler → application serialize → frame writer → write socket
```

This is a **pipeline**. Each stage either:

- needs more bytes (wait),
- produces a complete unit for the next stage, or
- fails and resets / closes.

Never let a stage “peek into” a later stage’s types.

## Model 3 — The session actor

Both **rodbus** and **dnp3** (Rust, Tokio) use this model:

- One asynchronous task **owns** the socket (or serial port) and all protocol state.
- Outside code holds a cheap **handle** that only sends messages into a mailbox (multi-producer single-consumer channel).
- Dropping the handle eventually shuts the task down.

This avoids sharing mutable protocol state across threads. **libIEC61850** often uses one thread per Transmission Control Protocol connection instead — same idea, different runtime.

**Remember:** the actor owns the truth. Handlers and application programming interfaces are guests.

## Model 4 — Half-duplex conversation

Modbus and classic Distributed Network Protocol 3 masters behave like polite conversations:

1. Ask one question
2. Wait for the answer (or timeout)
3. Ask the next question

Even on Transmission Control Protocol, **rodbus** and **dnp3** masters typically run **one outstanding request at a time per channel**. That simplifies correlation and matches serial-bus physics.

Pipelining many requests on one connection is possible in theory and painful in practice for these protocols. Prefer a queue of work with serial execution unless you have a strong reason not to.

## Model 5 — Two planes (International Electrotechnical Commission 61850)

IEC 61850 splits the world:

| Plane | Style | Typical use |
|-------|-------|-------------|
| Client / server | Connection-oriented, rich services | Configuration, control, buffered reports over Transmission Control Protocol |
| Publisher / subscriber | Connectionless multicast on Ethernet | Fast events (Generic Object Oriented Substation Event) and Sampled Values |

A translation service that only understands the client/server plane will miss the time-critical plane. Design for both when the field uses both.

## Model 6 — The model is the database

In **libIEC61850**, the live tree of logical devices, logical nodes, data objects, and data attributes *is* the process image. Services mostly walk that tree, encode values, and fire side effects (reports, goose publications).

In **dnp3** outstations, a point database (static + event buffers) plays a similar role. In **rodbus** servers, your `RequestHandler` *is* the database façade.

Internalize: **wire codecs are boring; the domain model is the product.**

## Model 7 — Fail closed versus fail soft

| Mode | Behavior | Used when |
|------|----------|-----------|
| Fail closed | Bad frame → close session → reconnect | Stream protocols where desync is fatal (Transmission Control Protocol Modbus, often Distributed Network Protocol 3 over Transmission Control Protocol) |
| Fail soft | Bad frame → discard byte → resync | Noisy serial streams |

**dnp3** exposes this as an explicit link error mode (`Close` versus `Discard`). Choosing wrong destroys either reliability or availability.

## Choosing a model for a new project

Ask, in order:

1. Is there one connection with serialized requests? → **session actor**
2. Are there distinct framing and meaning rules? → **layered sandwich**
3. Is there a rich process image? → **model-as-database**
4. Are there connectionless fast paths? → **two planes**
5. Is the medium noisy? → **fail soft at the framer**

Write those answers on a whiteboard before creating folders.

## Self-check

1. What may a framing layer never know about?
2. Why do Modbus clients often forbid concurrent outstanding requests?
3. What is the “second plane” in IEC 61850?



---


# Chapter 3 — How to Split the Problem into Layers

This chapter is the practical folder map you should recreate when starting a stack or a translator.

## Recommended layer list

For almost any industrial protocol:

| Layer name | Responsibility | Does not do |
|------------|----------------|-------------|
| **Physical adapter** | Read/write bytes; apply Transport Layer Security; serial timing | Parse headers |
| **Frame codec** | Delimit messages; checksums; length fields; sync hunt | Interpret registers or points |
| **Transport / segmentation** (if needed) | Reassemble multi-frame application messages | Session policy |
| **Application codec** | Function codes, object headers, data payloads | Socket reconnect |
| **Session / association** | Sequence numbers, timeouts, retries, unsolicited rules | Byte buffering |
| **Domain model** | Points, quality, timestamps, datasets | Wire encoding |
| **Service / product application programming interface** | User callbacks, polls, controls | Framing |

Optional siblings (not in the vertical path):

- **Diagnostics / decode logging** (mirror every layer)
- **Security policy** (authorization after decode, before side effects)
- **Foreign-function interface** façade (language bindings)

## How the three libraries map

### rodbus

```
PhysLayer
   ↑↓
FrameWriter / FramedReader  (Transmission Control Protocol header OR Remote Terminal Unit checksum)
   ↑↓
Request / response Protocol Data Unit parse
   ↑↓
ClientLoop or SessionTask
   ↑↓
Channel handle / RequestHandler
```

Folders: `common/phys`, `tcp/frame`, `serial/frame`, `client/`, `server/`.

### dnp3

```
PhysLayer (Transmission Control Protocol / Transport Layer Security / serial / User Datagram Protocol)
   ↑↓
Link (sync 0x05 0x64, cyclic redundancy check blocks, frame count bit)
   ↑↓
Transport (first/final flags + sequence assembly)
   ↑↓
Application fragment parse (zero-copy cursors)
   ↑↓
MasterSession / OutstationSession
   ↑↓
ReadHandler / ControlHandler / database
```

Folders: `util/phys`, `link/`, `transport/`, `app/`, `master/`, `outstation/`.

### libIEC61850

```
Hardware Abstraction Layer sockets / Ethernet / threads
   ↑↓
Transport Packet + Connection-Oriented Transport Protocol
   ↑↓
ISO session / presentation / Association Control Service Element
   ↑↓
Manufacturing Message Specification (Abstract Syntax Notation One Basic Encoding Rules)
   ↑↓
Mapping onto the International Electrotechnical Commission data model
   ↑↓
Abstract Communication Service Interface (IedServer / IedConnection)
```

Plus a **side stack** for Generic Object Oriented Substation Event and Sampled Values on Ethernet (or routable session over User Datagram Protocol).

## Folder hygiene rules

1. **Name folders after layers**, not after features. Prefer `link/` over `stuff/`.
2. **Keep wire types private** when possible. Public application programming interfaces expose domain types (ranges, measurements), not raw frame structs.
3. **Put reconnect loops beside physical adapters**, not inside application parsers. Both Rust stacks do this: a client connectivity state machine wraps a session that only runs while connected.
4. **Generate the boring tables.** Distributed Network Protocol 3 object variations and Manufacturing Message Specification schemas are large. Code generation beats hand-written mega-switches when the standard is stable.
5. **Feature-gate optional media.** Serial and Transport Layer Security behind compile features keeps footprints small.

## Designing layers for a *translation* service

A translator has **two stacks plus a middle**:

```
┌──────── Stack A ────────┐     ┌──── Canonical core ────┐     ┌──────── Stack B ────────┐
│ phys → frame → app      │────►│ points / quality /     │────►│ app → frame → phys      │
│ session A               │     │ timestamps / events    │     │ session B               │
└─────────────────────────┘     │ mapping & policy       │     └─────────────────────────┘
                                └────────────────────────┘
```

**Do not** let Stack A’s frame types appear in Stack B’s modules. Convert at the canonical boundary only.

Suggested core modules for a translator:

| Module | Contents |
|--------|----------|
| `model/` | Point identifiers, value types, quality, time |
| `map/` | Configuration: protocol A address ↔ canonical id ↔ protocol B address |
| `policy/` | Scaling, clamps, deadbands, write authorization |
| `ingress_a/`, `ingress_b/` | Session wiring into the core |
| `egress_a/`, `egress_b/` | Encode and send |
| `clock/` | Time sync strategy |
| `obs/` | Metrics and structured logs per layer |

## Interface contracts between layers

Write the contracts as types before code:

```text
Physical:
  read(buffer) -> bytes_read | error
  write(bytes) -> ok | error

Framer:
  push(bytes) -> None | Frame | FrameError
  reset()

ApplicationCodec:
  decode(frame.payload) -> Message | CodecError
  encode(message) -> bytes | CodecError

Session:
  on_message(message)
  poll_timeouts(now)
```

If a function needs both a socket and an object header, your layers have leaked.

## Vertical slice versus horizontal layer

When building, it is fine to implement a **vertical slice** (one happy-path request through all layers) first. Keep the *folder boundaries* even if some files are thin. Horizontal “finish all framing before any application” often produces unusable scaffolding.

Order that works well:

1. Physical mock + frame encode/decode unit tests
2. Application encode/decode unit tests on byte arrays
3. Session happy path with mock physical layer
4. Real sockets
5. Reconnect and chaos tests

## Self-check

1. Where should reconnect logic live?
2. What is the canonical core forbidding?
3. Name the extra layer Distributed Network Protocol 3 has that Modbus typically does not.



---


# Chapter 4 — Parsing Payloads: State Machines and Friends

Parsing industrial protocols is mostly about **turning a stream of bytes into structured messages without allocating blindly or trusting the peer**. This chapter compares the mechanisms you will actually use.

## The four jobs of a parser

1. **Synchronize** — find where a message starts
2. **Delimit** — know where it ends
3. **Validate** — checksums, lengths, protocol identifiers
4. **Interpret** — map bytes to typed fields

Different layers own different jobs. Link/frame layers do 1–3. Application layers do 4 (and more validation).

## Mechanism A — Incremental state machine (best for streams)

Used heavily in:

- **dnp3** link parser (`FindSync1` → `FindSync2` → `ReadHeader` → `ReadBody`)
- **rodbus** Transmission Control Protocol header parser (`Begin` → `Header`)
- **rodbus** Remote Terminal Unit parser (`Start` → length discovery → `ReadFullBody`)
- **libIEC61850** Transport Packet reader (`WAITING` → `COMPLETE` / `ERROR`)

### Pattern

```text
state = START
loop:
  if not enough bytes for this state: return NeedMore
  consume / validate
  state = NEXT or emit Frame and state = START
```

### Pros

- Handles partial reads naturally
- Constant memory if you bound frame size
- Easy to reset after errors
- Matches how Transmission Control Protocol and serial actually behave

### Cons

- States proliferate for complex headers
- Easy to forget a reset path
- Hand-written machines need careful review for off-by-one bugs

### Best practice

Store only what the next state needs (for example, a parsed header and expected body length). Cap maximum length **before** allocating or copying into a body buffer.

## Mechanism B — Length-prefixed framing

The peer tells you the size.

**Example:** Modbus Application Protocol header on Transmission Control Protocol — a 16-bit length field tells how many bytes follow (including unit identifier).

### Pros

- Simple, fast, no sync hunt
- Works perfectly on reliable streams

### Cons

- Useless alone on raw serial (no “start of message” if you join mid-stream)
- A corrupted length field can request absurd sizes — **must clamp**

**rodbus** rejects lengths outside `(0, 254]` and requires protocol identifier zero.

## Mechanism C — Sync hunt + cyclic redundancy check

Used by Distributed Network Protocol 3 link layer (`0x05 0x64` start bytes, cyclic redundancy check every 16 bytes) and Modbus Remote Terminal Unit (cyclic redundancy check over address + protocol data unit).

### Pros

- Recovers from noise (with fail-soft policy)
- Detects corruption

### Cons

- More central processing unit cost
- Sync bytes can appear inside payloads (false starts) — checksum saves you
- On Transmission Control Protocol, many stacks still keep sync/checksum for compatibility even though the stream is reliable

## Mechanism D — Function-code-driven length tables

**rodbus** Remote Terminal Unit does **not** primarily wait for 3.5 character times of silence to find frame ends on receive. Instead it:

1. Reads unit identifier and function code
2. Looks up how long that function’s body must be (different tables for requests versus responses)
3. Reads that many bytes
4. Checks the cyclic redundancy check

### Pros

- Deterministic in software without relying on timing jitter
- Works well with asynchronous runtimes

### Cons

- Unknown function codes cannot be delimited → hard error
- Custom or unusual function codes need table updates

Silence/timing is still applied on **transmit** for bus turnaround (3.5 character times).

## Mechanism E — Zero-copy cursor parsing

After a complete application fragment exists in a buffer, **rodbus** and **dnp3** parse with a cursor (`scursor::ReadCursor`):

- Read fixed-size integers
- Borrow slices for sequences
- Iterators yield measurements without allocating vectors per point

### Pros

- Fast, cache-friendly
- Fewer heap surprises under load
- Ideal for high-rate polling

### Cons

- Borrowed data lifetime tied to the buffer — do not store references past the handler call unless you copy
- Harder for bindings in garbage-collected languages (often copy at the foreign-function interface boundary)

## Mechanism F — Schema-generated codecs (Abstract Syntax Notation One)

**libIEC61850** Manufacturing Message Specification messages use codecs generated from Abstract Syntax Notation One modules (asn1c), encoding with Basic Encoding Rules (tag, length, value).

For Generic Object Oriented Substation Event and Sampled Values, the library often uses **hand-rolled** Basic Encoding Rules walkers for speed and control.

### Pros

- Faithful to large standards
- Reduces hand-written protocol bugs for huge message catalogs

### Cons

- Generated code is bulky and opaque
- Security review is harder; bugs appear in both generated and hand paths
- Allocating full decode trees can be expensive — watch embedded budgets

## Mechanism G — Parser combinators / declarative grammars

Libraries like `nom` in Rust are popular in some ecosystems. **None of the three stacks studied here rely on them for the hot path.** They chose explicit state machines + cursors instead.

### When combinators help

- Quick prototypes
- File formats with clear recursive structure

### When they hurt

- Streaming partial input (unless carefully designed)
- Strict no-alloc environments
- Teams that must audit every state transition for safety certification

## Choosing a mechanism — decision table

| Medium / problem | Prefer |
|------------------|--------|
| Transmission Control Protocol with explicit length | Length-prefixed state machine |
| Noisy serial with known sync | Sync hunt + checksum, fail soft |
| Serial Modbus-like known function layouts | Function-code length table + checksum |
| Multi-segment application messages | Transport assembler state machine (see Distributed Network Protocol 3 first/final flags) |
| Dense measurement lists | Zero-copy cursors over a completed fragment |
| Huge structured standards | Schema-generated codecs + careful memory policy |
| Multicast Ethernet snapshots | Hand parsers with hard size limits |

## A reference frame-reader loop

This is the shape shared by **rodbus** `FramedReader` and friends:

```text
loop:
  match parser.parse(buffer):
    Ok(None) ->
      read more bytes from physical layer into buffer
      if read fails: return InputOutputError
    Ok(Some(frame)) ->
      return frame
    Err(e) ->
      parser.reset()
      return e   # or discard-and-continue on serial fail-soft
```

Keep **parse** pure relative to the socket: it only consumes a buffer. That makes unit tests trivial (feed byte slices).

## Application parsing tips

1. **Expect emptiness** after fixed protocol data units — trailing garbage is an error.
2. **Validate ranges early** (maximum registers per request, maximum fragment size).
3. **Separate “bad frame” from “exception response”.** A Modbus illegal-function exception is valid framing; a bad cyclic redundancy check is not.
4. **Log with layer tags.** Decode levels in **rodbus** / **dnp3** let you enable physical hex, frame headers, or application objects independently.
5. **Fuzz the framer.** Partial headers, max-length frames, and truncated cyclic redundancy checks catch most production panics.

## State machine versus “just buffer until newline”

Industrial protocols almost never use text delimiters. If you find yourself buffering until a magic character, stop and re-read the specification’s framing section. Binary length and checksums are the norm.

## Self-check

1. Why must length fields be clamped?
2. When is fail-soft resync better than closing the socket?
3. Why does zero-copy parsing complicate language bindings?



---


# Chapter 5 — Sessions, Actors, and Correlation

Framing gives you messages. **Sessions** give you conversations that survive time.

## What session state includes

| Concern | Examples |
|---------|----------|
| Sequence / transaction identifiers | Modbus transaction identifier; Distributed Network Protocol 3 application sequence (4 bits); unsolicited sequence |
| Outstanding work | Current request; select-before-operate stage; file transfer offset |
| Timers | Response timeout; reconnect backoff; integrity poll period; Generic Object Oriented Substation Event retransmission |
| Peer identity | Link addresses; unit identifiers; association parameters |
| Caches | Last response for duplicate detection; selected control |
| Enabled flag | Communications administratively down while configured |

## The actor pattern (Rust stacks)

```
User code                      Session task
────────                       ────────────
Channel.handle ──mailbox──►   read physical layer
   enable/disable              parse frames
   read/write requests         run state machines
   settings                    write replies
                               complete promises
```

Properties:

- **Single owner** of protocol mutable state → fewer races
- **Serialized requests** on one channel → simple correlation
- **Handles are cloneable**; the task is not

**libIEC61850** often mirrors this with **one thread per connection** and a server accept loop, plus an event worker for periodic reporting and goose timing.

## Correlation strategies

### Strategy 1 — Single in-flight request

**rodbus** client and **dnp3** master (per channel) wait for the matching reply before starting the next user request.

Correlation keys:

- **Modbus Transmission Control Protocol:** transaction identifier (+ ignore mismatched identifiers as stale)
- **Modbus Remote Terminal Unit:** “the next valid frame” (half-duplex assumption)
- **Distributed Network Protocol 3:** application sequence number + link address match

**Pros:** Simple, correct for serial, easy timeouts.  
**Cons:** Lower throughput on high-latency links unless you open multiple channels.

### Strategy 2 — Echo identifiers

Servers copy the request’s transaction identifier / sequence into the response. The client checks equality.

### Strategy 3 — Duplicate detection by hash

**dnp3** outstations may hash the raw fragment and compare with the last valid request sequence. Retransmissions can reuse the cached response — important on unreliable networks.

### Strategy 4 — Multi-step procedure state machines

Controls often need nested states:

```
Idle → Select → Operate → Done
```

File transfers, time sync, and integrity-then-unsolicited enable sequences are the same idea. Keep them as explicit enums inside the session, not as scattered booleans.

## Timeouts and backoff

Distinguish:

| Timer | Meaning |
|-------|---------|
| Request timeout | Peer did not answer this transaction |
| Session death | Too many timeouts / bad frames → tear down connection |
| Reconnect delay | Wait before dialing again (often exponential after failures, shorter after clean disconnects) |
| Application schedules | Poll periods, unsolicited retry, goose retransmit |

**rodbus** can kill a Transmission Control Protocol session after consecutive response timeouts, then reconnect. Queued user requests fail with “no connection” while offline rather than hanging forever.

## Unsolicited / spontaneous messages

Distributed Network Protocol 3 and IEC 61850 reporting break the pure ask-answer model. Design rules:

1. While waiting for a solicited reply, **still read the socket**.
2. Route unsolicited messages to handlers **without** completing the pending solicited promise.
3. Confirmations (if required) are separate short transactions with their own sequence rules.

If your session loop only reads after writing a request, you will deadlock when the peer speaks first.

## Connectivity versus protocol

Both Step Function stacks separate:

```
Client connectivity state machine          Protocol session
Disabled → Connecting → Connected    →     Master/Outstation/ClientLoop runs
         ↘ WaitAfterFail ↗                 (only while Connected)
```

Benefits:

- Protocol code assumes a live byte pipe
- Reconnect policy can change without touching parsers
- Administrative disable stops traffic without destroying configuration

## Threadless and embedded modes

**libIEC61850** can compile as:

- Multi-threaded (default)
- Single-threaded
- Threadless (application polls incoming data and periodic tasks)

Mental model: the **same state machines**, driven either by threads or by your scheduler’s `tick()`. When integrating with a real-time operating system, prefer an explicit tick over hidden threads.

## Promises and foreign-function interfaces

Rust stacks complete user operations with oneshot channels or callbacks (`Promise`). If the task dies, dropping the promise fails the caller. That pattern is essential when generating C / C# / Java bindings: the binding layer must not assume the native task lives forever.

## Anti-patterns

| Anti-pattern | Failure mode |
|--------------|--------------|
| Shared parser + socket across threads without a lock hierarchy | Heisenbugs, double sends |
| Blocking inside a handler that the session calls | Stall entire channel |
| Correlating only by “last function code” | Mis-associate replies under delay |
| Infinite buffering of inbound data | Memory exhaustion from slow handlers |
| Treating application exceptions as session fatals | Flapping reconnects |

## Self-check

1. What does a Modbus Remote Terminal Unit client use as a correlation key?
2. Why must a master still read while waiting for a solicited response?
3. What belongs in connectivity state versus session state?



---


# Chapter 6 — Case Study: Modbus with rodbus

**Library:** Step Function I/O **rodbus** (Rust)  
**Path studied:** `rodbus-main/rodbus-main/rodbus`

Modbus is the gentlest industrial stack still used everywhere. Study it first. The architectural moves you learn here reappear, enlarged, in Distributed Network Protocol 3.

## What Modbus is (expanded)

Modbus is a request/reply protocol for reading and writing **coils** (bits) and **registers** (16-bit words) on a device addressed by a **unit identifier**.

Two common wire coats:

| Coat | Medium | Framing |
|------|--------|---------|
| Modbus Application Protocol | Transmission Control Protocol (and Transport Layer Security) | 7-byte header: transaction identifier, protocol identifier (0), length, unit identifier — then the protocol data unit |
| Remote Terminal Unit | Serial lines | unit identifier + protocol data unit + cyclic redundancy check 16 |

The **protocol data unit** (function code + data) is shared.

## Layer map in rodbus

```
Channel / ServerHandle          (public application programming interface)
        │ mailbox
        ▼
ClientLoop / SessionTask        (session actor)
        │
        ▼
FrameWriter / FramedReader      (Application Data Unit framing)
        │
        ▼
PhysLayer                       (Transmission Control Protocol / serial / Transport Layer Security / mock)
```

### Physical layer

`PhysLayer` abstracts async read/write. Remote Terminal Unit writes insert an inter-frame delay (≥ 3.5 character times; at least about 1750 microseconds above 19200 baud) so slaves can turn the bus around.

### Framing layer

Shared types in `common/frame.rs`:

- `Frame` = header + protocol data unit bytes (max Application Data Unit length **253**)
- `FrameHeader` = destination (unit identifier or broadcast) + optional transaction identifier

Parsers:

- `MbapParser` — length-prefixed state machine for Transmission Control Protocol
- `RtuParser` — function-code length table + cyclic redundancy check; **separate** request and response variants

### Application layer

Function codes implemented: `0x01`–`0x06`, `0x0F`, `0x10` (classic coils/registers). Unknown functions become exceptions or frame errors depending on side.

Parsing uses cursors; responses can expose zero-copy iterators over bits and registers.

## Client behavior

1. Create a channel task (`spawn_tcp_client_task` or serial/Transport Layer Security variants).
2. Call `enable()` — channels start **disabled** so you can attach listeners first.
3. Issue reads/writes on the handle; each becomes a mailbox `Command::Request` with a promise.
4. `ClientLoop` assigns a transaction identifier (Transmission Control Protocol), writes the frame, and waits until timeout.
5. Mismatched transaction identifiers are discarded; matching frames are decoded; promises complete.
6. On session errors (input/output, bad framing, too many timeouts), the connectivity loop reconnects using a retry strategy.

**Design choice:** only one request in flight. This is a feature for correctness.

## Server behavior

1. Map unit identifiers to `RequestHandler` trait objects.
2. Accept Transmission Control Protocol connections (with address filters and max session caps) or own one serial port.
3. For each frame: parse function → authorize (optional Transport Layer Security role) → call handler → write reply.
4. Broadcast unit identifier (0) on Remote Terminal Unit: apply writes to all handlers, **send no reply**.

Handlers run under a mutex — keep them short. Streaming writers pack coil/register payloads without giant intermediate buffers.

## Mental model summary

> One Application Data Unit, two coats; one actor per channel; fail closed on bad framing; exceptions are application-level, not session-level.

## Pros of this approach

- Clear teaching architecture for translators
- Excellent diagnostics (three decode levels)
- Safe Rust (`unsafe` forbidden in workspace)
- Foreign-function interface friendly (`MaybeAsync`, promises)
- Gateway-friendly multi unit-identifier map on one connection

## Cons / limits

- Limited function-code coverage versus some older C libraries
- No client pipelining (throughput on fat pipes needs multiple channels)
- Remote Terminal Unit unknown functions cannot be framed (by design)

## Lessons to steal for your translator

1. Put Transmission Control Protocol versus serial differences **only** in the framer.
2. Keep a mock physical layer for tests.
3. Separate “no connection” failures from Modbus exception codes in your canonical error model.
4. Administrative enable/disable is worth copying.

## Self-check

1. Where does the transaction identifier live — Application Data Unit coat or protocol data unit?
2. Why are there two Remote Terminal Unit parsers?
3. Does a cyclic redundancy check failure reconnect or return an exception code?



---


# Chapter 7 — Case Study: Distributed Network Protocol 3 with dnp3

**Library:** Step Function I/O **dnp3** (Rust)  
**Path studied:** `dnp3-main/dnp3-main/dnp3`  
**Standard family:** Institute of Electrical and Electronics Engineers 1815

Distributed Network Protocol 3 is what you reach for when Modbus’s flat register map is not enough: event buffers, unsolicited reports, freeze operations, file transfer, and a real layered link/transport/application design.

## Roles

| Role | Meaning |
|------|---------|
| **Master** | Client that polls, issues controls, receives unsolicited data |
| **Outstation** | Server that owns a point database and event buffers |

One Transmission Control Protocol channel may talk to multiple outstation link addresses (multi-drop associations). Serial and User Datagram Protocol transports are also supported.

## Layer map

```
MasterChannel / OutstationHandle
            │ mailbox
            ▼
MasterTask / OutstationTask          (Tokio session actor)
            │
            ▼
TransportReader / TransportWriter    (first/final flags, sequence, 249-byte segments)
            │
            ▼
Link Layer / Reader / Parser         (0x05 0x64, cyclic redundancy check blocks, frame count bit)
            │
            ▼
PhysLayer                            (Transmission Control Protocol / Transport Layer Security / serial / User Datagram Protocol)
```

### Link layer highlights

- Sync hunt state machine: `FindSync1` → `FindSync2` → `ReadHeader` → `ReadBody`
- Header + data protected with cyclic redundancy check in 16-byte blocks
- Secondary state tracks reset and expected frame count bit for confirmed user data
- `LinkErrorMode::Discard` (serial resync) versus `Close` (Transmission Control Protocol fail closed)
- `LinkReadMode::Stream` versus `Datagram` (User Datagram Protocol must not span packets)

### Transport layer highlights

Application messages may span multiple link frames. Each transport header carries:

- **First** flag
- **Final** flag
- **Sequence** number

Assembler states: `Empty` → `Running` → `Complete`. Unexpected sequence or peer change drops the partial fragment.

### Application layer highlights

`ParsedFragment::parse` reads control fields, function code, internal indication bits, then walks object headers (group / variation / qualifier). Values are borrowed from the fragment buffer — **zero-copy**. Large variation tables are code-generated under `app/gen/`.

## Master session behavior

`MasterSession` prioritizes automatic tasks (clear restart, disable unsolicited, integrity poll, enable unsolicited, time sync, …) ahead of or alongside user-queued tasks. Execution is still **one application transaction at a time** per channel.

Idle loop uses `tokio::select!` among:

- mailbox messages
- inbound transport reads (including unsolicited)
- sleep until next scheduled work

Association state tracks the 4-bit application sequence and per-outstation configuration.

## Outstation session behavior

Owns:

- Static database + event buffers
- Select-before-operate control state
- Unsolicited null-required versus ready states
- Duplicate request detection (`xxhash` of raw fragment + sequence)
- Deferred reads and confirmation series

On disconnect, teardown resets link/database session pieces so the next connection starts clean.

## Comparison to Modbus (same vendor lineage)

| Topic | rodbus | dnp3 |
|-------|--------|------|
| Framing coats | Two (Transmission Control Protocol / Remote Terminal Unit) | Link always; physical varies |
| Segmentation | Rarely needed | First/final transport assembly |
| Correlation | Transaction identifier or “next frame” | Application sequence + address |
| Spontaneous data | No (except you poll) | Unsolicited responses |
| Complexity of application parse | Function code bodies | Object header algebra |
| Mental cost | Low | Medium–high |

If you understood **rodbus**, treat **dnp3** as “the same actor + physical layer idea” with two extra protocol layers and a much richer application schema.

## Pros

- Industrially complete master/outstation behavior
- Explicit layering matches the standard — easy to teach and audit
- Configurable resilience (discard versus close)
- Strong test doubles (mock physical, mock transport)
- Structured per-layer decode logging

## Cons / costs

- Steeper learning curve than Modbus
- Commercial licensing for production use
- Application object model requires either generation or large tables
- 4-bit sequence space and fragment rules demand careful session logic

## Lessons to steal

1. **Transport assembly is its own module** — do not merge it into link or application.
2. **Unsolicited is a first-class citizen** in the read loop.
3. **Duplicate detection** belongs on the server/outstation.
4. **Codegen the catalog**; hand-write the session.
5. **Association maps** let one socket serve many logical peers — useful for gateway translators.

## Self-check

1. What do the first and final flags accomplish?
2. Why might serial use discard-and-resync while Transmission Control Protocol uses close?
3. Name two automatic master tasks that typically run before normal polling.



---


# Chapter 8 — Case Study: International Electrotechnical Commission 61850 with libIEC61850

**Library:** MZ Automation **libIEC61850** (C99)  
**Paths studied:**

- Prefer: `libiec61850-1.6_develop/libiec61850-1.6_develop` (version **1.6.2**)
- Older sibling: `Library_IEC61850-1.6/Library_IEC61850-1.6` (version **1.6.0**, same architecture, plus local Portuguese documents)

IEC 61850 is not “another register map.” It is a **substation data model** plus abstract services, mapped onto Manufacturing Message Specification for client/server traffic, with a separate Ethernet publisher/subscriber plane for fast messages.

## Expand the names once

| Short name | Expanded meaning |
|------------|------------------|
| IEC 61850 | International Electrotechnical Commission standard series for power-utility communications |
| ACSI | Abstract Communication Service Interface — the abstract operations (get data, report, control, …) |
| MMS | Manufacturing Message Specification — the ISO messaging protocol used on Transmission Control Protocol for many IEC 61850 services |
| SCL | Substation Configuration Language — XML engineering files (ICD/CID/SCD) |
| GOOSE | Generic Object Oriented Substation Event — fast multicast event messages |
| SV | Sampled Values — multicast streams of sampled measurements |
| BER | Basic Encoding Rules — tag/length/value encoding for Abstract Syntax Notation One |
| HAL | Hardware Abstraction Layer |
| COTP | Connection-Oriented Transport Protocol (ISO 8073) over Transport Packet (RFC 1006) |
| ACSE | Association Control Service Element — association request/response |

## Two planes

```
                    ┌──────────────────────────────┐
   Engineering      │  Substation Configuration     │
   time             │  Language → static C model    │
                    └──────────────┬───────────────┘
                                   ▼
                           Live IedModel tree
                     (logical devices / nodes / data)
                                   │
           ┌───────────────────────┼───────────────────────┐
           ▼                                               ▼
   Client/server plane                            Publisher/subscriber plane
   Transmission Control Protocol                  Ethernet multicast (or routable session)
   Manufacturing Message Specification            Generic Object Oriented Substation Event
   Abstract Communication Service Interface       Sampled Values
```

A translator that only bridges Manufacturing Message Specification reads will miss protection-speed events on the Ethernet plane.

## Vertical stack (client/server)

```
Your application
    → IedServer / IedConnection  (Abstract Communication Service Interface façade)
    → Manufacturing Message Specification mapping (IedModel ↔ MmsDevice)
    → Manufacturing Message Specification services (read/write/report/file/…)
    → Association Control Service Element
    → ISO presentation / session
    → Connection-Oriented Transport Protocol + Transport Packet
    → Hardware Abstraction Layer sockets (+ optional Transport Layer Security)
```

## Parsing approach

| Traffic | Technique |
|---------|-----------|
| Manufacturing Message Specification protocol data units | asn1c-generated Basic Encoding Rules codecs |
| Association Control, presentation pieces, goose, many sampled-value headers | Hand-written Basic Encoding Rules walkers with size/depth limits |
| Sampled value sample payload | Raw binary layout, not nested Abstract Syntax Notation structures |
| Transport Packet | Small three-state length assembler |

**Lesson:** large catalogs → generated codecs; hot/simple paths → hand parsers. Expect to maintain **both** carefully for security.

## Data model as database

```
IedModel
 └── LogicalDevice
      └── LogicalNode          (example: XCBR1, LLN0)
           └── DataObject      (may nest / array)
                └── DataAttribute   (+ functional constraint, type, live MmsValue)
```

Control blocks (report, goose, sampled value, setting group, log) sit beside the tree and decide **when** and **how** values leave the device.

Object references on the wire use Manufacturing Message Specification naming with `$` separators and functional constraints — handled in mapping code, not by your application if you stay at the Abstract Communication Service Interface.

## Configuration paths

1. **Static model (field devices):** Java/.NET generator reads Substation Configuration Language → emits `static_model.c` linked into the binary.
2. **Dynamic model:** build the tree with C application programming interfaces at runtime (simulators, tools).
3. **Text config file:** generator emits a simple text form; C parser rebuilds the tree (still not a full XML Substation Configuration Language parser in the core).

Online discovery uses Manufacturing Message Specification directory services against the mapped model — the device does not parse Substation Configuration Language on the wire.

## Threading modes

Configured in `config/stack_config.h`:

| Mode | Behavior |
|------|----------|
| Multi-threaded (default) | Accept thread + per-connection threads + event worker (~1 ms) |
| Single-threaded | Combined server thread |
| Threadless | Application calls process-incoming and periodic-task functions |

Control objects use their own select/operate state machine (unselected → ready → wait for select → test → operate, including time-activated operate).

## How this differs from the Rust stacks

| Topic | rodbus / dnp3 | libIEC61850 |
|-------|---------------|-------------|
| Language / memory | Safe Rust, ownership | Manual C, HAL allocators |
| Domain richness | Points / registers | Hierarchical semantic model |
| Hot path messaging | Mostly polled request/reply (+ dnp3 unsolicited) | Dual plane including multicast |
| Schema strategy | Hand + codegen variations | asn1c + hand Basic Encoding Rules |
| Portability knob | Cargo features | `stack_config.h` + HAL backends |
| Actor style | Tokio task + mailbox | Threads or poll ticks |

## Pros

- Matches how utilities engineer substations
- Portable C with threadless mode for embedded
- Compile-time footprint control
- Mature examples for client, server, goose, sampled values

## Cons / trade-offs

- Steep conceptual load (model + two planes + ISO stack)
- Dual BER implementations increase audit surface
- Multi-thread defaults demand disciplined data-model locking
- Static models need rebuilds when configuration changes
- Licensing (GPLv3 versus commercial) affects product packaging
- Windows goose depends on raw Ethernet capture stacks (historically WinPcap)

## Lessons to steal for translators

1. **Canonical model should be richer than registers** if either side is IEC 61850 — preserve quality, timestamps, and semantic paths when possible.
2. Treat goose/sampled values as **event streams**, not as “another poll.”
3. Keep **engineering-time configuration** (mapping files) separate from **runtime codecs**.
4. Offer a **poll/tick mode** if your translator already has a scheduler.
5. Security (Transport Layer Security, routable goose cryptography) wraps transports; do not invent a parallel abstract service layer for it.

## About the two trees in your folder

They are the **same project lineage**. Use **1.6.2 develop** for current architecture and fixes. Treat **1.6.0** as historical unless you specifically need the bundled Portuguese reference documents.

## Self-check

1. What lives in the publisher/subscriber plane?
2. Why is Substation Configuration Language usually compiled offline into C structs?
3. When would you enable threadless mode?



---


# Chapter 9 — Compare and Contrast

This chapter is the “cheat sheet” you can review before designing anything new.

## One-page comparison

| Dimension | rodbus (Modbus) | dnp3 (Distributed Network Protocol 3) | libIEC61850 (IEC 61850) |
|-----------|-----------------|----------------------------------------|-------------------------|
| Primary abstraction | Coils and registers | Typed points + event buffers | Hierarchical logical device tree |
| Framing | Length header or cyclic redundancy check | Sync + cyclic redundancy check + transport segments | Transport Packet / Connection-Oriented Transport Protocol; Ethernet for goose/sampled values |
| Application encoding | Compact function bodies | Object headers (group/variation) | Basic Encoding Rules (generated + hand) |
| Session style | Tokio actor, single in-flight | Tokio actor, single in-flight + unsolicited | Thread or tick per connection + event worker |
| Spontaneous data | No native | Unsolicited responses | Reports + goose + sampled values |
| Config surface | Small | Medium | Large (Substation Configuration Language / static model) |
| Best teacher for… | Layering & framing | Multi-layer stacks & sessions | Semantic models & dual planes |
| Language culture | Safe Rust | Safe Rust | Portable C |

## Shared patterns (steal these every time)

1. **Physical adapter interface** with a mock
2. **Incremental frame state machine** with hard maximum sizes
3. **Session owns the socket**; handles send messages
4. **Layered decode logging**
5. **Reconnect policy outside parsers**
6. **Extension via traits / callbacks**, not by editing core parsers
7. **Fail closed on stream desync; fail soft on noisy serial** (when applicable)

## Divergent patterns (choose deliberately)

| Pattern | Prefer when |
|---------|-------------|
| Single Application Data Unit + dual coats (**rodbus**) | Same application message rides on Transmission Control Protocol and serial |
| Dedicated transport assembly (**dnp3**) | Application messages exceed link maximum payload |
| Model-as-database + mapping layer (**libIEC61850**) | Peers share a rich semantic tree, not a flat address space |
| asn1c / schema codegen | Message catalog is huge and standards-driven |
| Hand Basic Encoding Rules / cursors | Latency, footprint, or auditability dominate |
| Multicast side plane | Millisecond-class events must not wait on poll cycles |

## Complexity versus capability

```
Capability
    ▲
    │                         ● libIEC61850
    │
    │              ● dnp3
    │
    │     ● rodbus
    │
    └──────────────────────────────────► Implementation complexity
```

For a **translation service**, you often implement **two points on this chart** plus a canonical core. Budget complexity for the harder peer; keep the core boring.

## Error model comparison

| Event | rodbus | dnp3 | libIEC61850 |
|-------|--------|------|-------------|
| Bad cyclic redundancy check / length | Session error → reconnect | Link error (close or discard) | Connection teardown / indication |
| Illegal function / object | Exception / internal indications | Application response with indications | Service errors / last application error |
| Timeout | Request fail; maybe session death | Task fail; association logic continues | Client request timeout / state error |
| Admin disable | Supported | Supported (enable/disable communications) | Stop listening / close |

Map all of these into **your** translator’s error taxonomy: `TransportFault`, `CodecFault`, `ApplicationNack`, `Timeout`, `ConfigError`.

## Performance postures

| Goal | Technique seen in these stacks |
|------|--------------------------------|
| Low allocation | Fixed buffers; zero-copy iterators; streaming writers |
| Low latency | Transmission Control Protocol no-delay; short event worker sleeps; goose retransmit tuning |
| Many peers | Multi-association channels; multi unit-identifier maps; max session caps with eviction |
| Embedded | Feature gates; `stack_config.h`; threadless poll |

## What each stack teaches a translator author

- **From rodbus:** keep coats swappable; serialize master transactions; treat exceptions as data.
- **From dnp3:** isolate transport reassembly; design for unsolicited; duplicate cache on servers.
- **From libIEC61850:** invest in the canonical semantic model; separate engineering-time mapping from runtime; do not forget the multicast plane.

## Self-check

1. Which stack is the best template for dual Transmission Control Protocol/serial framing?
2. Which problem forces a transport layer between link and application?
3. Why is IEC 61850 “higher” on the capability chart?



---


# Chapter 10 — Blueprint for a Protocol Translation Service

This is the architecture you can take to a design review.

## Purpose statement

> Accept data and commands from protocol A, normalize them into a canonical process model, apply policy, and emit protocol B — with clear ownership of framing, sessions, time, and quality.

## Reference architecture

```
                 ┌─────────────────────────────────────────────┐
                 │                 Operations                   │
                 │  metrics · logs · health · config reload     │
                 └─────────────────────────────────────────────┘
                 ┌──────────────┐     ┌──────────────┐
                 │ Southbound   │     │ Northbound   │
                 │ stack A      │     │ stack B      │
                 │ phys/frame/  │     │ phys/frame/  │
                 │ app/session  │     │ app/session  │
                 └──────┬───────┘     └───────┬──────┘
                        │ ingress             │ egress
                        ▼                     ▲
                 ┌─────────────────────────────────────────────┐
                 │              Canonical core                  │
                 │  point store · event queue · command bus     │
                 │  mapping table · policy · clock              │
                 └─────────────────────────────────────────────┘
```

**Southbound** often faces field devices. **Northbound** often faces a control center or another bus. Either direction can originate commands; draw arrows for *your* product.

## Canonical model (minimum viable)

Each point record should carry:

| Field | Why |
|-------|-----|
| Stable identifier | Survives protocol renumbering |
| Value + type | Boolean, integer, float, double, bitstring, … |
| Quality | Good / invalid / overflow / restart / … |
| Timestamp | Device time versus translator receive time — label which |
| Change counter or event id | Deduplicate |
| Origin | Which southbound session produced it |

Commands need:

| Field | Why |
|-------|-----|
| Target identifier | Mapping lookup |
| Command type | Select, operate, direct operate, write register, … |
| Value / trip-close | |
| Timeout / interlock policy | |
| Correlation token | Reply to northbound |

## Mapping configuration

Keep mapping **data-driven** (files or database), not hard-coded:

```text
canonical: breaker_1.position
  from_modbus: unit=3; reg=10001; type=coil; invert=false
  to_dnp3: index=12; class=1; static_group=1; variation=2
  policy: write_auth=operators; deadband=n/a
```

Reload mapping without restarting framers when possible; version the mapping schema.

## Data flow — measurement ingress

```
frame ok → app decode → map to canonical id → policy (scale/clamp)
  → update point store → enqueue event → northbound encoder → send
```

Rules:

- Never block the southbound session actor on northbound Transmission Control Protocol slowdowns — use a bounded queue and drop/shed with metrics if full (choose policy explicitly).
- Preserve quality; do not invent “good” when the source said “invalid.”

## Data flow — command egress

```
northbound command → authorize → map to southbound address
  → southbound select/operate or write → wait result → northbound ack/nak
```

For Distributed Network Protocol 3 / IEC 61850 controls, honor **select-before-operate** state machines. Do not collapse them into a single write unless the product requirements say direct-operate only.

## Process and threading

Recommended production shape (inspired by the Rust stacks):

1. One session actor per southbound channel
2. One session actor per northbound channel
3. One core worker (or lock-free queues into a core) for mapping/policy
4. Supervisors for reconnect

Alternatively, a single-threaded event loop is fine at modest rates if every codec is non-blocking.

## Bounded resources checklist

| Resource | Bound |
|----------|-------|
| Frame size | Protocol maximum |
| Event queue | Fixed capacity |
| Sessions | Max connections |
| Outstanding commands | Per-direction limit |
| Log rate | Sample under storms |

## Observability

Copy the three libraries’ idea: **decode levels per layer**. Add:

- counters: frames ok/bad, timeouts, queue depth, mapping misses
- traces: correlation token across the hop
- a “last value” debug view of the canonical store

## Security

- Terminate Transport Layer Security at the physical adapter
- Authorize **after** decode, **before** side effects (as rodbus role checks do)
- Treat mapping edits as privileged configuration
- Do not log secret material from secure sessions

## Incremental delivery plan

1. Canonical store + fake ingress/egress adapters (no real protocols)
2. Southbound Modbus only → store
3. Northbound Distributed Network Protocol 3 only ← store
4. Commands both ways
5. Quality/time hardening
6. Second southbound protocol
7. Chaos tests (partial frames, reconnect storms, queue fill)

## Anti-patterns specific to translators

| Anti-pattern | Result |
|--------------|--------|
| Point-to-point byte bridging | Unmaintainable special cases |
| Blocking southbound on northbound | Field timeouts cascade |
| Silent mapping misses | “It works in the lab” |
| One shared mutable socket across protocols | Corruption |
| Collapsing select-before-operate | Unsafe controls |

## Self-check

1. What four fields belong on every canonical point?
2. Where do you authorize writes?
3. What happens when the northbound queue is full? (You must have an answer.)



---


# Chapter 11 — Trade-offs and Best Practices

## Parsing trade-offs

| Approach | Prefer when | Avoid when |
|----------|-------------|------------|
| Incremental state machine | Streams, partial reads | Trivial fixed datagrams (still fine, just heavier) |
| Length prefix | Trusted streams with length fields | Noisy serial without sync |
| Sync + checksum | Serial, mixed reliability | You forgot fail-soft versus fail-closed policy |
| Function length tables | Known fixed layouts (Modbus Remote Terminal Unit) | Open-ended vendor function codes |
| Zero-copy cursors | High rate, same-language handlers | Need to store decoded data long-term without copying |
| Schema-generated codecs | Huge standards | Tiny embedded flash budgets without trimming |
| Parser combinators | Prototypes | Safety-audited hot paths (unless team is expert) |

## Concurrency trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| One actor per channel (Tokio) | Clear ownership, great for Rust stacks | Requires async literacy |
| One thread per connection (C) | Simple mental model | Stack/memory cost; locking discipline |
| Threadless poll | Fits existing real-time operating system | Easy to starve if tick is slow |
| Shared multi-threaded parser | Throughput temptation | Almost always not worth the races |

## Correlation trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| Single in-flight | Correctness on serial; simple | Latency × depth hurts throughput |
| Transaction identifiers with pipelining | Throughput | Complex stale-reply handling; rare in these stacks |
| Hash + sequence duplicate cache | Survives retries | Memory and hash cost; must bound cache |

## Model richness trade-offs

| Model | Pros | Cons |
|-------|------|------|
| Flat registers | Easy mapping | Loses semantics |
| Typed points + quality + time | Good translator core | More code |
| Full IEC logical node tree | Faithful to utility engineering | Heavy; overkill if both peers are Modbus |

**Guideline:** make the canonical model **as rich as your richest peer**, then map poorer peers upward (synthesize quality/time carefully and document defaults).

## Best practices checklist (print this)

### Framing

- [ ] Hard maximum frame size enforced before copy
- [ ] Parser has an explicit `reset()`
- [ ] Unit tests feed byte-at-a-time and max-size frames
- [ ] Cyclic redundancy check / length failures counted

### Sessions

- [ ] Socket ownership is unique
- [ ] Request timeout separate from reconnect backoff
- [ ] Unsolicited path cannot complete the wrong promise
- [ ] Administrative enable/disable exists

### Application codecs

- [ ] Ranges validated early
- [ ] Application negative responses ≠ transport faults
- [ ] Logging can show headers without dumping every payload in production

### Translator core

- [ ] Mapping is data-driven and versioned
- [ ] Bounded queues with explicit shed policy
- [ ] Quality preserved end-to-end
- [ ] Controls respect select-before-operate when required
- [ ] Clock source labeled on timestamps

### Operations

- [ ] Health endpoint shows session states
- [ ] Chaos test: kill sockets under load
- [ ] Config reload does not wedge actors

## “Good taste” decisions observed in the studied code

1. **Start disabled** until configured (**rodbus**).
2. **Maybe-async callbacks** to keep foreign-function interfaces honest (**rodbus**, **dnp3**).
3. **Decode levels** instead of unstructured hex dumps.
4. **Codegen catalogs**, hand-write sessions (**dnp3**, Manufacturing Message Specification).
5. **Compile-time feature switches** for footprint (**libIEC61850** `stack_config.h`, Rust crate features).
6. **Mock physical layers** for deterministic tests.

## When to break the rules

- Ultra-high-rate sampled values may need kernel bypass or specialized NIC paths — still keep a logical layer boundary even if folders fuse for performance.
- A throwaway lab shim may byte-bridge temporarily — do not ship it.
- If both ends are identical protocols, you may proxy at session level without a rich model — still keep framing isolation for security filtering.

## Self-check

1. Pick a parsing approach for noisy serial with sync bytes — justify fail-soft or fail-closed.
2. Name one reason to reject pipelining on a Modbus client.
3. What should happen to quality bits across a translation?



---


# Chapter 12 — Capstone Exercises (Offline)

No network required. Use paper, a whiteboard, or a local editor.

## Exercise 1 — Draw the sandwich

Pick **one** protocol you know (even Hypertext Transfer Protocol). Draw:

1. Physical adapter
2. Framer (state names included)
3. Application codec
4. Session actor
5. Domain model

Write one sentence each on what that layer **must not** know.

## Exercise 2 — Frame state machine

Design a framer for a fictional protocol:

- Sync bytes `0xA5 0x5A`
- 1-byte length `N` (payload size), `N` ≤ 128
- Payload of `N` bytes
- 1-byte checksum = sum of payload modulo 256

Write states, transitions, and what happens on checksum failure for (a) serial fail-soft and (b) Transmission Control Protocol fail-closed.

## Exercise 3 — Compare coats

Explain how **rodbus** keeps one protocol data unit while switching between Modbus Application Protocol and Remote Terminal Unit. List which modules would change if you added a third coat (for example, User Datagram Protocol with an explicit length).

## Exercise 4 — Unsolicited safety

A master is waiting for a solicited response. An unsolicited message arrives first. Write pseudocode for the session loop that:

- Dispatches unsolicited to a handler
- Does not complete the solicited promise
- Still respects the solicited timeout

## Exercise 5 — Translator sketch

You must translate Modbus coils → Distributed Network Protocol 3 binary inputs, and Distributed Network Protocol 3 controls → Modbus coil writes.

Deliverables:

1. Canonical point record definition
2. Mapping file sample (3 points)
3. Sequence diagram for a control with select-before-operate on the Distributed Network Protocol 3 northbound and a single coil write southbound (document the policy choice!)
4. Queue-full policy

## Exercise 6 — IEC two-plane awareness

A breaker position changes. List what might be emitted on:

1. A buffered report over Manufacturing Message Specification
2. A Generic Object Oriented Substation Event publication

What would your translator lose if it only subscribed to reports?

## Exercise 7 — Audit a bug class

A device sends a Transmission Control Protocol Modbus length field of `0xFFFF`. Walk through how a correct stack rejects this. Then describe a buggy stack that allocates `length` blindly — what happens under attack?

## Exercise 8 — Architecture review script

Using chapter 11’s checklist, review one of the libraries in the parent folder (read-only). Score 10 checklist items as pass/fail with file references. This is excellent airplane work if you downloaded the sources.

## Suggested answers direction (brief)

Do not peek until you try.

<details>
<summary>Exercise 2 hints</summary>

States might be: `FindSync1`, `FindSync2`, `ReadLength`, `ReadPayload`, `ReadChecksum`. On failure (a) reset to `FindSync1` and discard one byte or restart hunt; (b) return error and close.

</details>

<details>
<summary>Exercise 4 hints</summary>

`select` on read and timer. On frame: if unsolicited → handler; if solicited match → complete promise; else ignore. On timer → fail promise.

</details>

<details>
<summary>Exercise 7 hints</summary>

Clamp length to maximum Application Data Unit; never allocate unchecked. The buggy stack allows memory exhaustion or wraparound.

</details>

## Glossary (course-wide)

| Term | Definition |
|------|------------|
| Application Data Unit | Framed packet including addressing/transaction fields around a protocol data unit |
| Protocol Data Unit | Function code and data without the outer network header |
| Canonical model | Translator’s internal process representation |
| Cyclic redundancy check | Checksum used to detect corrupted frames |
| Fail closed | Abort the session on framing errors |
| Fail soft | Resynchronize and continue after framing errors |
| First / final flags | Transport markers for multi-segment Distributed Network Protocol 3 application messages |
| Hardware Abstraction Layer | Portable OS/platform interface |
| Select before operate | Two-step control arming pattern |
| Session actor | Task/thread that owns protocol state and input/output |
| Sync hunt | Searching a byte stream for start-of-frame markers |
| Transaction identifier | Modbus Application Protocol field correlating requests and replies |
| Unit identifier | Modbus address of a logical device on a segment |
| Zero-copy | Parsing by borrowing buffer slices instead of allocating new storage |

## Course closing

You now have the same mental toolkit used in **rodbus**, **dnp3**, and **libIEC61850**:

1. Layer the sandwich
2. Parse with bounded state machines
3. Own sessions like actors
4. Put meaning in a domain model
5. Translate through a canonical core — never through raw byte tunnels

When you land, open the HTML version’s animated diagrams and narrate them aloud from memory. Teaching the picture is the fastest way to keep it.



---


