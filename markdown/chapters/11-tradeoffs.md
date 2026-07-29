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
