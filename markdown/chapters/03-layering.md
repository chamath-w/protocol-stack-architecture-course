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
