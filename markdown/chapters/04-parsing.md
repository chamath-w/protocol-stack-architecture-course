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
