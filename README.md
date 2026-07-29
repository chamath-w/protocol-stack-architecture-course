# Protocol Stack Architecture Course

A self-contained course on how industrial protocol stacks are structured, how to parse wire payloads, and how to design a **protocol translation service**. The material is drawn from a close reading of three production-grade implementations:

| Library | Protocol | Language | Role in this course |
|---------|----------|----------|---------------------|
| **rodbus** (Step Function I/O) | Modbus Transmission Control Protocol and Remote Terminal Unit | Rust | Simplest layered stack — best starting point |
| **dnp3** (Step Function I/O) | Distributed Network Protocol version 3 (Institute of Electrical and Electronics Engineers 1815) | Rust | Multi-layer framing with link, transport, and application |
| **libIEC61850** (MZ Automation) | International Electrotechnical Commission 61850 | C | Rich data model plus dual communication planes |

## Study formats (airplane-ready)

Everything in this repository is **offline**. No network is required after you download it.

| Format | Path | Best for |
|--------|------|----------|
| **Interactive HTML** | [`html/index.html`](html/index.html) | Visual learning — animated diagrams, chapter navigation |
| **Full Markdown course** | [`markdown/COURSE.md`](markdown/COURSE.md) | Reading / annotating / printing |
| **Chapter files** | [`markdown/chapters/`](markdown/chapters/) | Studying one topic at a time |

Open `html/index.html` in any browser (Chrome, Firefox, Edge, Safari). Animations use inline Scalable Vector Graphics and Cascading Style Sheets only — no external scripts or fonts from the internet.

## Course map

1. Why protocol stacks exist, and what a translation service does
2. Mental models that keep designs coherent
3. How to split the problem into layers
4. Parsing strategies (state machines, cursors, length tables, Abstract Syntax Notation)
5. Session actors, correlation, and reconnect loops
6. Case study: Modbus with **rodbus**
7. Case study: Distributed Network Protocol 3 with **dnp3**
8. Case study: International Electrotechnical Commission 61850 with **libIEC61850**
9. Compare and contrast the three stacks
10. Blueprint for a protocol translation service
11. Trade-offs and best practices checklist
12. Capstone exercises (no network required)

## Acronym policy

This course **minimizes acronyms**. When a short form is unavoidable, it is expanded on first use in each chapter. A glossary lives at the end of the full Markdown course and in the HTML sidebar.

## Source trees analyzed

These implementations live alongside this course in the parent folder (not re-uploaded here, to respect licenses):

- `rodbus-main/rodbus-main`
- `dnp3-main/dnp3-main`
- `libiec61850-1.6_develop/libiec61850-1.6_develop` (prefer this over the older 1.6.0 tree)
- `Library_IEC61850-1.6/Library_IEC61850-1.6` (same lineage at version 1.6.0 — treated as historical)

**License note:** **rodbus** and **dnp3** from Step Function I/O are commercial products with non-commercial evaluation terms. **libIEC61850** is GPLv3 with commercial options. This course discusses *architecture patterns* observed in those codebases; it does not redistribute their source.

## How to use this on a flight

1. Clone or download the repository before boarding.
2. Open `html/index.html` offline, or open `markdown/COURSE.md` in any Markdown viewer.
3. Work through chapters 1–5 for foundations, then 6–8 for concrete stacks, then 9–11 for design decisions.
4. Attempt the capstone sketches in chapter 12 with paper or a local editor.

## Repository contents

```
protocol-stack-course/
├── README.md
├── markdown/
│   ├── COURSE.md
│   └── chapters/
│       ├── 01-why-stacks.md
│       ├── 02-mental-models.md
│       ├── 03-layering.md
│       ├── 04-parsing.md
│       ├── 05-sessions.md
│       ├── 06-modbus-rodbus.md
│       ├── 07-dnp3.md
│       ├── 08-iec61850.md
│       ├── 09-compare.md
│       ├── 10-translation-service.md
│       ├── 11-tradeoffs.md
│       └── 12-exercises.md
└── html/
    └── index.html
```
