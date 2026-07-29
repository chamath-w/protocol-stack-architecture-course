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
