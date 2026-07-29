# Chapter 10 — Blueprint for a Protocol Translation Service

This is the architecture you can take to a design review.

## Purpose statement

> Accept data and commands from protocol A, normalize them into a canonical process model, apply policy, and emit protocol B — with clear ownership of framing, sessions, time, and quality.

## Reference architecture

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

**Southbound** often faces field devices. **Northbound** often faces a control center or another bus. Either direction can originate commands; draw arrows for *your* product.

## Canonical model (minimum viable)

Each point record should carry:

| Field | Why |
|-------|-----|
| Stable identifier | Survives protocol renumbering |
| Value + type | Boolean, integer, float, double, bitstring, … |
| Quality | Good / invalid / overflow / restart / … |
| Timestamp | Device time versus translator receive time — label which |
| Change counter or event id | Deduplicate |
| Origin | Which southbound session produced it |

Commands need:

| Field | Why |
|-------|-----|
| Target identifier | Mapping lookup |
| Command type | Select, operate, direct operate, write register, … |
| Value / trip-close | |
| Timeout / interlock policy | |
| Correlation token | Reply to northbound |

## Mapping configuration

Keep mapping **data-driven** (files or database), not hard-coded:

```text
canonical: breaker_1.position
  from_modbus: unit=3; reg=10001; type=coil; invert=false
  to_dnp3: index=12; class=1; static_group=1; variation=2
  policy: write_auth=operators; deadband=n/a
```

Reload mapping without restarting framers when possible; version the mapping schema.

## Data flow — measurement ingress

```
frame ok → app decode → map to canonical id → policy (scale/clamp)
  → update point store → enqueue event → northbound encoder → send
```

Rules:

- Never block the southbound session actor on northbound Transmission Control Protocol slowdowns — use a bounded queue and drop/shed with metrics if full (choose policy explicitly).
- Preserve quality; do not invent “good” when the source said “invalid.”

## Data flow — command egress

```
northbound command → authorize → map to southbound address
  → southbound select/operate or write → wait result → northbound ack/nak
```

For Distributed Network Protocol 3 / IEC 61850 controls, honor **select-before-operate** state machines. Do not collapse them into a single write unless the product requirements say direct-operate only.

## Process and threading

Recommended production shape (inspired by the Rust stacks):

1. One session actor per southbound channel
2. One session actor per northbound channel
3. One core worker (or lock-free queues into a core) for mapping/policy
4. Supervisors for reconnect

Alternatively, a single-threaded event loop is fine at modest rates if every codec is non-blocking.

## Bounded resources checklist

| Resource | Bound |
|----------|-------|
| Frame size | Protocol maximum |
| Event queue | Fixed capacity |
| Sessions | Max connections |
| Outstanding commands | Per-direction limit |
| Log rate | Sample under storms |

## Observability

Copy the three libraries’ idea: **decode levels per layer**. Add:

- counters: frames ok/bad, timeouts, queue depth, mapping misses
- traces: correlation token across the hop
- a “last value” debug view of the canonical store

## Security

- Terminate Transport Layer Security at the physical adapter
- Authorize **after** decode, **before** side effects (as rodbus role checks do)
- Treat mapping edits as privileged configuration
- Do not log secret material from secure sessions

## Incremental delivery plan

1. Canonical store + fake ingress/egress adapters (no real protocols)
2. Southbound Modbus only → store
3. Northbound Distributed Network Protocol 3 only ← store
4. Commands both ways
5. Quality/time hardening
6. Second southbound protocol
7. Chaos tests (partial frames, reconnect storms, queue fill)

## Anti-patterns specific to translators

| Anti-pattern | Result |
|--------------|--------|
| Point-to-point byte bridging | Unmaintainable special cases |
| Blocking southbound on northbound | Field timeouts cascade |
| Silent mapping misses | “It works in the lab” |
| One shared mutable socket across protocols | Corruption |
| Collapsing select-before-operate | Unsafe controls |

## Self-check

1. What four fields belong on every canonical point?
2. Where do you authorize writes?
3. What happens when the northbound queue is full? (You must have an answer.)
