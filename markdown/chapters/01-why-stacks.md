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
