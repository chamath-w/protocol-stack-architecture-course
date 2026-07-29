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
