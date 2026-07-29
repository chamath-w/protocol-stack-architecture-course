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
