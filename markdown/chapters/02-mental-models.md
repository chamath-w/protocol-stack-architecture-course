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
