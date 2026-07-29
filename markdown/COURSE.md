# Protocol Stack Architecture Course

**Self-contained study guide for airplane use.** Open the companion HTML at `html/index.html` for animated diagrams and the interactive parse lab.

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

The **canonical core** is your product’s protocol-independent process image (values, quality, time, mapping, policy). Prefer it over pairwise byte bridges so you do not grow N² converters as protocols are added. Deep dive: [Chapter 10](10-translation-service.md).

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


# Chapter 4 — Parsing Payloads: Strategies in Depth

Parsing industrial protocols is mostly about **turning a stream of bytes into structured messages without allocating blindly or trusting the peer**. This chapter catalogs the options, when each wins or loses, and how the stacks in this folder chose.

## The four jobs of a parser

Every framer and codec is doing some mix of:

1. **Synchronize** — find where a message starts
2. **Delimit** — know where it ends
3. **Validate** — checksums, lengths, protocol identifiers, version fields
4. **Interpret** — map bytes to typed fields (function codes, registers, object headers, …)

| Job | Typical owner |
|-----|----------------|
| Synchronize / delimit / validate framing | Link or frame layer |
| Interpret meaning | Application codec |
| Reassemble multi-frame application messages | Transport layer (Distributed Network Protocol 3) |

Do not merge all four into one function. Framing bugs and semantic bugs need different tests.

---

## Strategy catalog (what exists)

### 1. Incremental state machine (streaming finite-state machine)

**Idea:** Keep an explicit `state` enum. On each call, either consume bytes and advance, return “need more,” emit a frame, or error/reset.

**Where you see it:** **dnp3** link (`FindSync1` → `FindSync2` → `ReadHeader` → `ReadBody`); **rodbus** Modbus Application Protocol and Remote Terminal Unit parsers; **libIEC61850** Transport Packet waiting states.

**Best for:** Transmission Control Protocol streams, serial byte streams, any medium that delivers arbitrary chunks.

**Worse for:** Already-delimited datagrams where you always get one whole message per read (still usable, just heavier than necessary).

**Pros:** Natural partial reads; bounded memory; easy `reset()`; unit-testable with sliced input.  
**Cons:** Many states; easy to miss an error path; off-by-one bugs in hand machines.

**Hard rules:** Cap lengths before copying. Store only what the next state needs (parsed header + expected remaining count).

---

### 2. Length-prefixed framing

**Idea:** A header field says how many bytes follow. Read header → clamp length → read body.

**Example:** Modbus Application Protocol on Transmission Control Protocol — 16-bit length (includes unit identifier).

**Best for:** Reliable bidirectional streams with an explicit length field in the standard.

**Worse for:** Noisy serial where you might join mid-frame (no sync to recover); untrusted peers without a hard maximum.

**Pros:** Fast; no sync hunt; simple state machine (`Begin` → `Header`).  
**Cons:** Corrupted length can request gigabytes — **must clamp**; alone cannot resync on serial.

**Verdict:** Default choice for modern Transmission Control Protocol industrial coats. Pair with fail-closed on bad lengths.

---

### 3. Sync-byte hunt + integrity check

**Idea:** Search for magic start bytes, parse a header, verify cyclic redundancy check (or similar) over header and/or body. On failure, discard and hunt again (fail soft) or close (fail closed).

**Examples:** Distributed Network Protocol 3 link (`0x05 0x64` + cyclic redundancy check blocks); many serial protocols.

**Best for:** Serial lines, radio, anything with noise or mid-stream attach.

**Worse for:** Pure Transmission Control Protocol where length-prefix already delimits — unless the standard mandates sync for compatibility (Distributed Network Protocol 3 still uses it over Transmission Control Protocol).

**Pros:** Recovers from garbage; detects corruption.  
**Cons:** Sync pattern can appear inside payloads (false starts — checksum rejects); more central processing unit cost; policy choice (soft vs closed) must be explicit.

**Verdict:** Prefer for serial. On Transmission Control Protocol, use it when the standard requires it; otherwise length-prefix is cleaner.

---

### 4. Function-code (or type-code) length tables

**Idea:** After reading a small fixed prefix (address + function code), look up how long the rest of the frame must be. Different tables for requests vs responses.

**Example:** **rodbus** Remote Terminal Unit receive path.

**Best for:** Protocols with a closed set of fixed layouts (classic Modbus coils/registers).

**Worse for:** Open-ended vendor function codes; variable-length fields that are not discoverable from the first bytes; standards that expect silence-based framing only.

**Pros:** Deterministic without timing; works with asynchronous runtimes; no need to wait for 3.5 character silence on receive.  
**Cons:** Unknown function code → cannot delimit → hard error; tables must stay complete.

**Note:** **rodbus** still applies inter-frame delay on **transmit** for bus turnaround; receive delimiting is table-driven.

**Verdict:** Excellent for Modbus-like serial when you control the function set. Poor as a general strategy for extensible protocols.

---

### 5. Inter-frame silence / idle-line detection

**Idea:** A gap of N character times means “frame ended” (classic Modbus Remote Terminal Unit physical guidance).

**Best for:** Hardware universal asynchronous receiver-transmitters with idle detection; very low-level drivers.

**Worse for:** Software asynchronous runtimes with jittery scheduling; virtual serial ports; high baud where gaps are tiny; mixed traffic with irregular spacing.

**Pros:** Can delimit unknown layouts without a length table.  
**Cons:** Fragile in software; false frame splits under load; hard to unit-test.

**Verdict:** Prefer hardware support or use as a backup. For portable stacks, length tables or sync+length beat pure silence detection — which is why **rodbus** chose tables for receive.

---

### 6. Transport / segmentation assembly (first–final flags)

**Idea:** Link frames are small; application messages are large. A transport header carries first flag, final flag, and sequence. Assembler states: empty → running → complete.

**Example:** **dnp3** transport layer (about 249 application bytes per link frame).

**Best for:** Standards that segment application fragments across multiple link frames.

**Worse for:** Protocols whose application message always fits in one frame (Modbus). Adding this layer “just in case” adds bugs without benefit.

**Pros:** Clear module boundary; sequence checking catches loss/reorder.  
**Cons:** Another state machine; must handle peer change and overflow; duplicates/retries need session policy too.

**Verdict:** Mandatory when the standard segments. Keep it **out of** the link parser and **out of** the application object decoder.

---

### 7. Zero-copy cursor interpretation

**Idea:** Once a complete application buffer exists, walk it with a cursor: read integers, borrow slices, yield iterators — avoid allocating a vector per point.

**Examples:** **rodbus** and **dnp3** application parse via `scursor`.

**Best for:** High-rate polling, large measurement lists, same-language handlers that finish before the buffer is reused.

**Worse for:** Storing decoded values past the handler call without copying; garbage-collected language bindings (often copy at the boundary anyway).

**Pros:** Fast; low allocation; cache-friendly.  
**Cons:** Lifetime discipline; harder debugging if you accidentally keep a dangling borrow (Rust prevents this; C does not).

**Verdict:** Prefer for hot application decode in Rust/C++. Always copy when crossing into long-lived stores or foreign-function interfaces.

---

### 8. Schema-generated codecs (Abstract Syntax Notation One / similar)

**Idea:** Compile a formal schema into encode/decode functions (often Basic Encoding Rules: tag, length, value).

**Example:** **libIEC61850** Manufacturing Message Specification via asn1c; goose/sampled-value paths often hand-rolled for control.

**Best for:** Huge message catalogs defined by standards bodies.

**Worse for:** Tiny embedded footprints without trimming; teams that cannot review generated code; ultra-hot paths where allocation-heavy decode trees hurt.

**Pros:** Faithfulness to the standard; less hand-written catalog bugs.  
**Cons:** Bulk; opacity; security fixes in generator *and* hand helpers; possible heap churn.

**Verdict:** Use for large ISO-style stacks. For latency-critical Ethernet snapshots, hand parsers with hard limits (as libIEC61850 does for goose) are often better.

---

### 9. Parser combinators / declarative grammars

**Idea:** Compose small parsers (`nom`, `combine`, …) into a grammar.

**Best for:** Prototypes, file formats, recursive structures with clear text/binary grammars.

**Worse for:** Streaming partial input unless carefully designed; safety-certified hot paths where every transition must be auditable; no-alloc embedded.

**Verdict:** None of the three production stacks studied here use combinators on the hot path. Prefer explicit state machines for industrial wire framing.

---

### 10. Datagram = one message (User Datagram Protocol / multicast)

**Idea:** Each socket read is already one protocol data unit (or one link frame). Still validate length and checksum inside the datagram; do not span messages across datagrams unless the standard says so.

**Example:** **dnp3** User Datagram Protocol mode (`LinkReadMode::Datagram`); IEC 61850 goose/sampled values on Ethernet.

**Best for:** Multicast and datagram transports.

**Worse for:** Assuming the same code path as Transmission Control Protocol streams without disabling multi-frame spanning.

---

## Decision matrix — pick by application

| Application context | Prefer | Avoid / demote |
|---------------------|--------|----------------|
| Modbus over Transmission Control Protocol | Length-prefixed state machine + clamp | Sync hunt alone; silence detection |
| Modbus over serial (known function set) | Function-code length table + cyclic redundancy check; fail soft on bad check | Pure silence delimiting in user-space async; unknown-FC open world |
| Distributed Network Protocol 3 serial | Sync hunt + cyclic redundancy check, fail soft; then transport assembly; then cursor app parse | Collapsing all layers into one buffer scrape |
| Distributed Network Protocol 3 Transmission Control Protocol | Same framing as standard; fail closed on link errors | Ignoring transport first/final flags |
| IEC 61850 Manufacturing Message Specification | Schema Basic Encoding Rules for protocol data units; hand helpers for association pieces | Ad-hoc string splitting |
| IEC 61850 goose / sampled values | Hand Basic Encoding Rules / fixed layouts with hard caps; datagram mindset | Full asn1c trees on every multicast packet if latency matters |
| Protocol translator hot path | Zero-copy into canonical **copy** at the core boundary | Storing borrowed wire slices in the point store |
| Safety / certification narrative | Explicit enums + tables you can review | Opaque combinator soup |
| Hostile network (internet-facing gateway) | Fail closed, clamp all lengths, fuzz framers | Fail soft forever (hides attacks as “noise”) |
| Lab bench / forgiving serial | Fail soft resync | Closing the port on every glitch |

---

## Layered parsing in practice (happy path)

```text
read() → append buffer
framer.parse():
  NeedMore → read again
  Frame → transport.assemble(frame)   # if layer exists
       → if complete fragment: app.decode(fragment)
       → session.handle(message)
  Error → reset and/or close
```

**Application decode** should assume the fragment is already whole. Do not sync-hunt inside object headers.

---

## Fail soft versus fail closed (framing errors)

| Policy | Behavior | Good for | Bad for |
|--------|----------|----------|---------|
| Fail soft | Discard byte(s), return to sync hunt | Noisy serial | Masking malicious length games on Transmission Control Protocol |
| Fail closed | Abort session, reconnect | Stream protocols; gateways | Flapping on a single serial glitch |

**dnp3** exposes this as link error mode (`Discard` vs `Close`). Choose per medium, not globally.

---

## Worked micro-examples

### Length-prefixed (Modbus Application Protocol)

```text
Bytes:  [00 01] [00 00] [00 06] [01] [03 00 00 00 0A]
         tx id   proto   length  uid  function + data
State:  Begin → need 7 header bytes → Header(len=6) → read 6 → Frame
Check:  proto==0; length in (0,254]; body length = length-1 after uid accounting per stack rules
```

### Sync hunt (Distributed Network Protocol 3 link start)

```text
Bytes:  ... aa 05 64 [header][crc] [body blocks][crc] ...
State:  FindSync1 (wait 05) → FindSync2 (wait 64) → ReadHeader → ReadBody
On bad crc: fail soft → FindSync1; or fail closed → tear down
```

### Function-code table (Remote Terminal Unit request)

```text
Bytes:  [01] [03] [00 00 00 0A] [crc lo] [crc hi]
         uid  FC   fixed-size body for FC 03 request
State:  Start → read uid+FC → lookup request length → ReadFullBody → crc ok → Frame
```

### Transport assembly

```text
Frame1: FIR=1 FIN=0 seq=5  payload...
Frame2: FIR=0 FIN=0 seq=6  payload...
Frame3: FIR=0 FIN=1 seq=7  payload...
Assembler: Empty → Running → Running → Complete → app.parse
```

---

## Comparison to the three libraries

| Strategy | rodbus | dnp3 | libIEC61850 |
|----------|--------|------|-------------|
| Incremental frame finite-state machine | Yes | Yes | Yes (Transport Packet, etc.) |
| Length prefix | Modbus Application Protocol | Header length fields inside link | Transport Packet length |
| Sync + cyclic redundancy check | Remote Terminal Unit crc; no DNP sync | Core link design | Not the MMS path |
| Function length tables | Remote Terminal Unit | No (object headers instead) | No |
| Transport first/final | No | Yes | Segmentation differs (Connection-Oriented Transport Protocol) |
| Zero-copy cursors | Yes | Yes | Manual buffer walks; MMS often tree-allocates |
| Schema Basic Encoding Rules | No | No | Yes (MMS) + hand BER (goose/…) |

---

## Choosing for *your* next stack (checklist)

1. What medium? (serial / Transmission Control Protocol / User Datagram Protocol / Ethernet multicast)
2. Does the standard define sync, length, both, or silence?
3. Can application messages span frames?
4. Is the function/object catalog closed or huge?
5. Hostile or friendly network?
6. Do handlers need zero-copy or long-lived owned data?

Write the answers down, then pick from the catalog above. If you pick two strategies for two media (as **rodbus** does), share the application codec and isolate the coat.

## Self-check

1. Why is length-prefix alone a poor fit for noisy serial?
2. When are function-code length tables better than silence detection?
3. Why keep transport assembly out of the application object decoder?
4. When should a translator **copy** instead of zero-copy?



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


# Chapter 10 — Canonical Core and the Translation Service Blueprint

This chapter explains **what a canonical core is**, **why serious translators prefer one**, and then gives the architecture you can take to a design review.

## What “canonical core” means

**Canonical** here means: *one agreed internal representation of process truth*, independent of any single wire protocol.

The **canonical core** is the middle of a protocol translation service:

```
Protocol A stack  →  Canonical core  →  Protocol B stack
   (bytes in)         (meaning)           (bytes out)
```

It is **not**:

- a shared socket buffer
- a pile of `if protocol == Modbus` switches inside a Distributed Network Protocol 3 encoder
- a raw byte forwarder (“whatever came in goes out”)

It **is**:

- a **point / tag store** (current values)
- an optional **event / change queue**
- a **command bus** (writes, selects, operates)
- a **mapping table** (wire address ↔ stable identifier ↔ other wire address)
- **policy** (scale, clamp, deadband, authorize, rate limit)
- a **clock / time policy** (whose timestamp is on this value?)

Think of it as the product’s **process image** plus the **rules for changing it**. Protocol stacks are adapters that speak foreign languages into that image.

---

## Why a canonical core is preferred (and often required)

### 1. Combinatorial explosion without one

With **N** protocols and no core, people build pairwise bridges:

```
bridges needed ≈ N × (N − 1)   # directed A→B and B→A each count
```

| Protocols | Pairwise directed bridges | With canonical core (adapters) |
|-----------|---------------------------|--------------------------------|
| 2 | 2 | 2 |
| 3 | 6 | 3 |
| 4 | 12 | 4 |
| 6 | 30 | 6 |

Each pairwise bridge re-implements scaling, quality handling, and control semantics. A core turns the problem into **N adapters + one model**.

### 2. Meaning survives protocol quirks

| Concern | Without core (byte/path bridging) | With canonical core |
|---------|-----------------------------------|---------------------|
| Modbus has no quality bits | You invent nothing or invent silently | Explicit default quality + documentation |
| Distributed Network Protocol 3 event classes | Hard-coded into Modbus poll logic | Mapped to event priority in the core |
| IEC 61850 semantic paths | Flattened to register numbers too early | Stable identifiers retain path metadata |
| Endianness / scaling | Duplicated in every bridge | One policy module |

The core is where you decide **product behavior**. Stacks only encode/decode.

### 3. Testability

You can unit-test:

- mapping lookups
- deadbands
- select-before-operate policy
- queue shed behavior

…with **fake ingress/egress adapters** and no sockets. Pairwise bridges usually need two live stacks to test anything.

### 4. Operational clarity

On-call questions become answerable:

- “What is the canonical value of `breaker_1.position` right now?”
- “Which southbound session last updated it?”
- “Did northbound fail to send, or did southbound never update?”

Without a core, truth is smeared across wire captures.

### 5. Evolution

Adding protocol C means writing **one** new adapter against the existing model — not rewriting A↔B. Replacing a Modbus library should not require rewriting your Distributed Network Protocol 3 encoder.

### 6. Safety and authorization

Authorize **once** against canonical identifiers and roles, after decode and before side effects. Doing auth inside each stack duplicates policy and drifts.

---

## When a thin bridge might be acceptable

A full core is **preferred** for products. A thin bridge can be acceptable when:

| Situation | Why a thin bridge might pass |
|-----------|------------------------------|
| Temporary lab shim | Disposable; not shipped |
| Identical protocol both sides (proxy/filter) | Same semantics; still isolate framing for security |
| One-off vendor tool with two fixed endpoints | Cost of a model exceeds lifetime of the tool |

Even then, keep **framing isolated**. Never share mutable frame buffers across “sides.”

If the tool might grow a third protocol, build the core on day one — retrofits are expensive.

---

## What belongs in the core versus the stacks

| Belongs in stack adapters | Belongs in canonical core |
|---------------------------|---------------------------|
| Sync hunt, cyclic redundancy check, length clamp | Stable point identifiers |
| Session actors, reconnect, transaction identifiers | Current value, quality, time |
| Function-code / object encode-decode | Mapping configuration |
| Protocol-specific control state machines (arming on the wire) | Product-level interlocks and who may write |
| Per-layer decode logs for that protocol | Cross-hop correlation tokens and metrics |

**Gray area:** select-before-operate. The **wire** state machine lives in the Distributed Network Protocol 3 / IEC adapter; the **product policy** (“northbound select maps to southbound direct write”) lives in the core and must be documented.

---

## Canonical model (minimum viable)

### Point / measurement record

| Field | Why it exists |
|-------|----------------|
| Stable identifier | Survives register renumbering and site rewiring |
| Value + type | Boolean, integer, float, double, bitstring, … |
| Quality | Good / invalid / overflow / restart / operator-blocked / … |
| Timestamp + time quality | Device time vs translator receive time — **label which** |
| Change counter or event id | Deduplicate; detect missed events |
| Origin | Which session/adapter produced the update |
| Optional semantic metadata | IEC path, engineering units, description |

### Command record

| Field | Why |
|-------|-----|
| Target identifier | Mapping lookup |
| Command type | Select, operate, cancel, direct operate, write register, … |
| Value / trip-close / setpoint | |
| Timeout / policy flags | |
| Correlation token | Reply to the northbound caller |
| Requester identity | Authorization and audit |

### Mapping entry (configuration, not code)

```text
canonical: breaker_1.position
  from_modbus: unit=3; address=10001; type=coil; invert=false
  to_dnp3: index=12; class=1; static_group=1; variation=2
  policy: write_auth=operators; deadband=n/a; scale=1; offset=0
```

Version the mapping schema. Prefer reload without restarting framers.

---

## How data moves through the core

### Measurement ingress (field → center)

```
southbound frame ok
  → application decode (protocol types)
  → map to canonical id
  → policy (scale / clamp / deadband)
  → update point store
  → enqueue event (if changed / if class warrants)
  → northbound encoder
  → send
```

**Critical rule:** do not block the southbound session actor on a slow northbound socket. Use a **bounded queue**. When full, choose explicitly: drop oldest, drop newest, or shed by priority — and **count it**.

**Quality rule:** never upgrade “invalid” to “good.” If Modbus has no quality, set an explicit `Quality::AssumedGood` (or similar) so operators know it was synthesized.

### Command egress (center → field)

```
northbound command
  → authorize against canonical id + role
  → map to southbound address + command shape
  → southbound select/operate or write
  → wait result / timeout
  → northbound acknowledge or negative acknowledge
```

Document whether a Distributed Network Protocol 3 select-before-operate collapses to a single Modbus write (common, but a **policy choice**, not an accident).

---

## Mental model: adapters around a database

```
┌─────────────┐   ┌──────────────────────┐   ┌─────────────┐
│ Adapter A   │   │ Canonical core       │   │ Adapter B   │
│ (rodbus-    │◄─►│  store · map · policy│◄─►│ (dnp3-like) │
│  shaped)    │   │  queues · clock      │   │             │
└─────────────┘   └──────────────────────┘   └─────────────┘
```

This matches how **libIEC61850** treats the live model tree as the database, and how **dnp3** outstations treat the point database as truth. Your translator’s core is the same idea elevated to **multi-protocol** scope.

---

## Anti-patterns (canonical core edition)

| Anti-pattern | What goes wrong |
|--------------|-----------------|
| Pairwise byte bridge | Unmaintainable special cases; N² growth |
| Storing wire borrows in the point store | Use-after-free / torn reads when buffers reuse |
| Blocking southbound on northbound | Field timeouts cascade; reconnect storms |
| Silent mapping misses | “Works in lab,” empty in production |
| Auth only on one adapter | Bypass via the other protocol |
| Inventing Good quality | Misleading operators and automation |

---

## Reference architecture (full service)

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

**Southbound** often faces field devices. **Northbound** often faces a control center. Either direction can originate commands.

## Process and threading

Recommended production shape (inspired by the Rust stacks):

1. One session actor per southbound channel  
2. One session actor per northbound channel  
3. Core updated via channels/queues (or a single-threaded loop at modest rates)  
4. Supervisors for reconnect  

## Bounded resources checklist

| Resource | Bound |
|----------|-------|
| Frame size | Protocol maximum |
| Event queue | Fixed capacity |
| Sessions | Max connections |
| Outstanding commands | Per-direction limit |
| Log rate | Sample under storms |

## Observability

- Per-protocol decode levels (as in **rodbus** / **dnp3**)
- Canonical “last value” debug view
- Counters: mapping misses, queue depth, shed events, timeouts
- Traces keyed by correlation token across the hop

## Security

- Terminate Transport Layer Security at the physical adapter  
- Authorize after decode, before side effects  
- Treat mapping edits as privileged configuration  

## Incremental delivery plan

1. Canonical store + fake adapters (no real protocols)  
2. Southbound Modbus → store  
3. Northbound Distributed Network Protocol 3 ← store  
4. Commands both ways + documented control policy  
5. Quality/time hardening  
6. Second southbound protocol  
7. Chaos tests (partial frames, reconnect storms, queue fill)  

## Self-check

1. How many adapters do you need for 5 protocols with a canonical core versus pairwise bridges?  
2. Name three fields every canonical point should carry besides the raw value.  
3. Why is blocking southbound on northbound Transmission Control Protocol back-pressure dangerous?  
4. When is a thin bridge acceptable, and what must you still isolate?



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


