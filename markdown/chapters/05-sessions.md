# Chapter 5 — Sessions, Actors, and Correlation

Framing gives you messages. **Sessions** give you conversations that survive time.

## What session state includes

| Concern | Examples |
|---------|----------|
| Sequence / transaction identifiers | Modbus transaction identifier; Distributed Network Protocol 3 application sequence (4 bits); unsolicited sequence |
| Outstanding work | Current request; select-before-operate stage; file transfer offset |
| Timers | Response timeout; reconnect backoff; integrity poll period; Generic Object Oriented Substation Event retransmission |
| Peer identity | Link addresses; unit identifiers; association parameters |
| Caches | Last response for duplicate detection; selected control |
| Enabled flag | Communications administratively down while configured |

## The actor pattern (Rust stacks)

```
User code                      Session task
────────                       ────────────
Channel.handle ──mailbox──►   read physical layer
   enable/disable              parse frames
   read/write requests         run state machines
   settings                    write replies
                               complete promises
```

Properties:

- **Single owner** of protocol mutable state → fewer races
- **Serialized requests** on one channel → simple correlation
- **Handles are cloneable**; the task is not

**libIEC61850** often mirrors this with **one thread per connection** and a server accept loop, plus an event worker for periodic reporting and goose timing.

## Correlation strategies

### Strategy 1 — Single in-flight request

**rodbus** client and **dnp3** master (per channel) wait for the matching reply before starting the next user request.

Correlation keys:

- **Modbus Transmission Control Protocol:** transaction identifier (+ ignore mismatched identifiers as stale)
- **Modbus Remote Terminal Unit:** “the next valid frame” (half-duplex assumption)
- **Distributed Network Protocol 3:** application sequence number + link address match

**Pros:** Simple, correct for serial, easy timeouts.  
**Cons:** Lower throughput on high-latency links unless you open multiple channels.

### Strategy 2 — Echo identifiers

Servers copy the request’s transaction identifier / sequence into the response. The client checks equality.

### Strategy 3 — Duplicate detection by hash

**dnp3** outstations may hash the raw fragment and compare with the last valid request sequence. Retransmissions can reuse the cached response — important on unreliable networks.

### Strategy 4 — Multi-step procedure state machines

Controls often need nested states:

```
Idle → Select → Operate → Done
```

File transfers, time sync, and integrity-then-unsolicited enable sequences are the same idea. Keep them as explicit enums inside the session, not as scattered booleans.

## Timeouts and backoff

Distinguish:

| Timer | Meaning |
|-------|---------|
| Request timeout | Peer did not answer this transaction |
| Session death | Too many timeouts / bad frames → tear down connection |
| Reconnect delay | Wait before dialing again (often exponential after failures, shorter after clean disconnects) |
| Application schedules | Poll periods, unsolicited retry, goose retransmit |

**rodbus** can kill a Transmission Control Protocol session after consecutive response timeouts, then reconnect. Queued user requests fail with “no connection” while offline rather than hanging forever.

## Unsolicited / spontaneous messages

Distributed Network Protocol 3 and IEC 61850 reporting break the pure ask-answer model. Design rules:

1. While waiting for a solicited reply, **still read the socket**.
2. Route unsolicited messages to handlers **without** completing the pending solicited promise.
3. Confirmations (if required) are separate short transactions with their own sequence rules.

If your session loop only reads after writing a request, you will deadlock when the peer speaks first.

## Connectivity versus protocol

Both Step Function stacks separate:

```
Client connectivity state machine          Protocol session
Disabled → Connecting → Connected    →     Master/Outstation/ClientLoop runs
         ↘ WaitAfterFail ↗                 (only while Connected)
```

Benefits:

- Protocol code assumes a live byte pipe
- Reconnect policy can change without touching parsers
- Administrative disable stops traffic without destroying configuration

## Threadless and embedded modes

**libIEC61850** can compile as:

- Multi-threaded (default)
- Single-threaded
- Threadless (application polls incoming data and periodic tasks)

Mental model: the **same state machines**, driven either by threads or by your scheduler’s `tick()`. When integrating with a real-time operating system, prefer an explicit tick over hidden threads.

## Promises and foreign-function interfaces

Rust stacks complete user operations with oneshot channels or callbacks (`Promise`). If the task dies, dropping the promise fails the caller. That pattern is essential when generating C / C# / Java bindings: the binding layer must not assume the native task lives forever.

## Anti-patterns

| Anti-pattern | Failure mode |
|--------------|--------------|
| Shared parser + socket across threads without a lock hierarchy | Heisenbugs, double sends |
| Blocking inside a handler that the session calls | Stall entire channel |
| Correlating only by “last function code” | Mis-associate replies under delay |
| Infinite buffering of inbound data | Memory exhaustion from slow handlers |
| Treating application exceptions as session fatals | Flapping reconnects |

## Self-check

1. What does a Modbus Remote Terminal Unit client use as a correlation key?
2. Why must a master still read while waiting for a solicited response?
3. What belongs in connectivity state versus session state?
