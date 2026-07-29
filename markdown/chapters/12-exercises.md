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
