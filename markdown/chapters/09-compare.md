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
