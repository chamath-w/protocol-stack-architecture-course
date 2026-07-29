# -*- coding: utf-8 -*-
"""Generate self-contained protocol-stack course HTML with inline SVG animations."""
from pathlib import Path
import walkthroughs

OUT = Path(__file__).resolve().parent / "html" / "index.html"
OUT.parent.mkdir(parents=True, exist_ok=True)

CSS = r"""
:root {
  --bg: #0f1419;
  --bg2: #1a2332;
  --bg3: #243044;
  --text: #e8eef6;
  --muted: #9aadc4;
  --accent: #3d9cf0;
  --accent2: #2ec4a8;
  --warn: #f0a030;
  --danger: #e85d5d;
  --card: #162032;
  --line: #2a3a52;
  --serif: "Palatino Linotype", Palatino, "Book Antiqua", Georgia, serif;
  --sans: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  --mono: Consolas, "Courier New", monospace;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: var(--sans);
  background: radial-gradient(1200px 600px at 10% -10%, #1c3a5c 0%, transparent 50%),
              radial-gradient(900px 500px at 100% 0%, #14352f 0%, transparent 45%),
              var(--bg);
  color: var(--text);
  line-height: 1.55;
}
a { color: var(--accent); }
.layout { display: grid; grid-template-columns: 280px 1fr; min-height: 100vh; }
nav {
  position: sticky; top: 0; height: 100vh; overflow: auto;
  background: rgba(15,20,25,0.92); border-right: 1px solid var(--line);
  padding: 1.25rem 1rem 2rem; backdrop-filter: blur(8px);
}
nav h1 { font-size: 1.05rem; margin: 0 0 0.25rem; font-family: var(--serif); color: #fff; }
nav .tag { font-size: 0.75rem; color: var(--muted); margin-bottom: 1rem; }
nav a {
  display: block; text-decoration: none; color: var(--muted);
  padding: 0.35rem 0.55rem; border-radius: 6px; font-size: 0.88rem; margin: 0.1rem 0;
}
nav a:hover, nav a.active { background: var(--bg3); color: #fff; }
nav .group { margin-top: 0.9rem; font-size: 0.7rem; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--accent2); padding-left: 0.55rem; }
main { padding: 2rem 2.5rem 4rem; max-width: 920px; }
.hero {
  padding: 1.5rem 0 1rem; border-bottom: 1px solid var(--line); margin-bottom: 2rem;
}
.hero h1 { font-family: var(--serif); font-size: 2.2rem; margin: 0 0 0.5rem; line-height: 1.2; }
.hero p { color: var(--muted); margin: 0; max-width: 62ch; }
section.chapter {
  margin: 0 0 3.5rem; padding-top: 0.5rem;
  border-top: 1px solid transparent;
}
section.chapter > h2 {
  font-family: var(--serif); font-size: 1.75rem; margin: 0 0 0.75rem;
  color: #fff;
}
section.chapter > h3 { margin-top: 1.75rem; color: #d7e6f7; font-size: 1.15rem; }
.lead { font-size: 1.05rem; color: #c5d4e6; }
.card {
  background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  padding: 1rem 1.1rem; margin: 1rem 0;
}
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 960px) {
  .layout { grid-template-columns: 1fr; }
  nav { position: relative; height: auto; }
  .grid2 { grid-template-columns: 1fr; }
  main { padding: 1.25rem; }
}
table {
  width: 100%; border-collapse: collapse; font-size: 0.9rem; margin: 1rem 0;
}
th, td { border: 1px solid var(--line); padding: 0.5rem 0.6rem; vertical-align: top; }
th { background: var(--bg3); text-align: left; }
td { background: rgba(22,32,50,0.6); }
pre, code { font-family: var(--mono); }
pre {
  background: #0b1018; border: 1px solid var(--line); border-radius: 10px;
  padding: 0.9rem 1rem; overflow: auto; font-size: 0.82rem; color: #cde3ff;
}
.diagram {
  background: linear-gradient(180deg, #121a26, #0e1520);
  border: 1px solid var(--line); border-radius: 14px;
  padding: 1rem; margin: 1.25rem 0 0.5rem; overflow: hidden;
}
.diagram svg { width: 100%; height: auto; display: block; }
.caption { font-size: 0.85rem; color: var(--muted); margin: 0 0 1.25rem; }
.pill {
  display: inline-block; font-size: 0.72rem; padding: 0.15rem 0.5rem;
  border-radius: 999px; background: var(--bg3); color: var(--accent2);
  margin-right: 0.35rem;
}
.callout {
  border-left: 3px solid var(--accent2); padding: 0.6rem 0.9rem;
  background: rgba(46,196,168,0.08); margin: 1rem 0; border-radius: 0 8px 8px 0;
}
.warnbox {
  border-left: 3px solid var(--warn); padding: 0.6rem 0.9rem;
  background: rgba(240,160,48,0.08); margin: 1rem 0; border-radius: 0 8px 8px 0;
}
.controls { display: flex; gap: 0.5rem; flex-wrap: wrap; margin: 0.5rem 0 0; }
.controls button {
  background: var(--bg3); color: var(--text); border: 1px solid var(--line);
  border-radius: 8px; padding: 0.4rem 0.75rem; cursor: pointer; font: inherit;
}
.controls button:hover { border-color: var(--accent); }
.paused .anim { animation-play-state: paused !important; }
ul.tight li { margin: 0.25rem 0; }
""" + walkthroughs.EXTRA_CSS + r"""
ul.tight li { margin: 0.25rem 0; }
.footer {
  margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--line);
  color: var(--muted); font-size: 0.85rem;
}
/* Animations shared */
@keyframes flowRight {
  0% { offset-distance: 0%; opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { offset-distance: 100%; opacity: 0; }
}
@keyframes pulse {
  0%, 100% { opacity: 0.35; }
  50% { opacity: 1; }
}
@keyframes climb {
  0% { transform: translateY(18px); opacity: 0; }
  20% { opacity: 1; }
  80% { opacity: 1; }
  100% { transform: translateY(-70px); opacity: 0; }
}
@keyframes dash {
  to { stroke-dashoffset: -40; }
}
@keyframes blinkState {
  0%, 100% { fill-opacity: 0.15; }
  50% { fill-opacity: 0.55; }
}
@keyframes mailbox {
  0% { transform: translateX(-30px); opacity: 0; }
  20% { opacity: 1; }
  70% { opacity: 1; }
  100% { transform: translateX(110px); opacity: 0; }
}
.anim-flow { animation: flowRight 3.2s linear infinite; }
.anim-pulse { animation: pulse 2s ease-in-out infinite; }
.anim-climb { animation: climb 2.8s ease-in-out infinite; }
.anim-dash { stroke-dasharray: 6 6; animation: dash 1s linear infinite; }
.anim-state { animation: blinkState 1.6s ease-in-out infinite; }
.anim-mail { animation: mailbox 2.4s ease-in-out infinite; }
"""

def svg_layers():
    return r'''
<div class="diagram" id="diag-layers">
<svg viewBox="0 0 760 340" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Layered protocol sandwich with upward byte flow">
  <defs>
    <linearGradient id="g1" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#2a6f97"/><stop offset="100%" stop-color="#1b4332"/>
    </linearGradient>
    <filter id="soft"><feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  </defs>
  <rect x="40" y="30" width="420" height="70" rx="12" fill="#1e3a5f" stroke="#3d9cf0" stroke-width="1.5"/>
  <text x="250" y="58" text-anchor="middle" fill="#e8eef6" font-size="16" font-family="Segoe UI,sans-serif">Application / Session / Handlers</text>
  <text x="250" y="80" text-anchor="middle" fill="#9aadc4" font-size="12" font-family="Segoe UI,sans-serif">meaning · timers · user callbacks</text>

  <rect x="40" y="120" width="420" height="70" rx="12" fill="#1a3d3a" stroke="#2ec4a8" stroke-width="1.5"/>
  <text x="250" y="148" text-anchor="middle" fill="#e8eef6" font-size="16" font-family="Segoe UI,sans-serif">Framing / Transport assembly</text>
  <text x="250" y="170" text-anchor="middle" fill="#9aadc4" font-size="12" font-family="Segoe UI,sans-serif">length · sequence · checksum · sync hunt</text>

  <rect x="40" y="210" width="420" height="70" rx="12" fill="#3a2a1e" stroke="#f0a030" stroke-width="1.5"/>
  <text x="250" y="238" text-anchor="middle" fill="#e8eef6" font-size="16" font-family="Segoe UI,sans-serif">Physical adapter</text>
  <text x="250" y="260" text-anchor="middle" fill="#9aadc4" font-size="12" font-family="Segoe UI,sans-serif">sockets · serial · Ethernet · Transport Layer Security</text>

  <!-- animated packet climbing -->
  <g class="anim anim-climb">
    <rect x="200" y="250" width="100" height="26" rx="6" fill="#3d9cf0" opacity="0.9"/>
    <text x="250" y="267" text-anchor="middle" fill="#0f1419" font-size="12" font-weight="700" font-family="Consolas,monospace">BYTES</text>
  </g>

  <path d="M500 245 C560 245, 560 65, 620 65" fill="none" stroke="#3d9cf0" stroke-width="2" class="anim anim-dash"/>
  <circle cx="500" cy="245" r="5" fill="#f0a030"/><circle cx="620" cy="65" r="5" fill="#3d9cf0"/>
  <text x="640" y="50" fill="#e8eef6" font-size="13" font-family="Segoe UI,sans-serif">Decode upward</text>
  <text x="640" y="70" fill="#9aadc4" font-size="12" font-family="Segoe UI,sans-serif">Encode downward</text>

  <text x="40" y="315" fill="#9aadc4" font-size="12" font-family="Segoe UI,sans-serif">Rule: a layer talks only to its neighbors. Lower layers never know about coils or logical nodes.</text>
</svg>
</div>
<p class="caption">Figure 1 — The layered sandwich. Animated packet shows the decode direction (physical → application).</p>
'''

def svg_pipeline():
    return r'''
<div class="diagram" id="diag-pipeline">
<svg viewBox="0 0 760 220" xmlns="http://www.w3.org/2000/svg" aria-label="Byte pipeline stages">
  <defs>
    <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#3d9cf0"/>
    </marker>
  </defs>
  <rect x="20" y="70" width="110" height="60" rx="10" fill="#243044" stroke="#3d9cf0"/>
  <text x="75" y="105" text-anchor="middle" fill="#fff" font-size="13" font-family="Segoe UI,sans-serif">Socket</text>
  <rect x="160" y="70" width="110" height="60" rx="10" fill="#243044" stroke="#2ec4a8"/>
  <text x="215" y="98" text-anchor="middle" fill="#fff" font-size="13" font-family="Segoe UI,sans-serif">Buffer</text>
  <text x="215" y="116" text-anchor="middle" fill="#9aadc4" font-size="11" font-family="Segoe UI,sans-serif">NeedMore?</text>
  <rect x="300" y="70" width="120" height="60" rx="10" fill="#243044" stroke="#f0a030"/>
  <text x="360" y="98" text-anchor="middle" fill="#fff" font-size="13" font-family="Segoe UI,sans-serif">Frame FSM</text>
  <text x="360" y="116" text-anchor="middle" fill="#9aadc4" font-size="11" font-family="Segoe UI,sans-serif">sync·len·CRC</text>
  <rect x="450" y="70" width="120" height="60" rx="10" fill="#243044" stroke="#3d9cf0"/>
  <text x="510" y="105" text-anchor="middle" fill="#fff" font-size="13" font-family="Segoe UI,sans-serif">App parse</text>
  <rect x="600" y="70" width="120" height="60" rx="10" fill="#1a3d3a" stroke="#2ec4a8"/>
  <text x="660" y="105" text-anchor="middle" fill="#fff" font-size="13" font-family="Segoe UI,sans-serif">Handler</text>

  <line x1="130" y1="100" x2="155" y2="100" stroke="#3d9cf0" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="270" y1="100" x2="295" y2="100" stroke="#3d9cf0" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="420" y1="100" x2="445" y2="100" stroke="#3d9cf0" stroke-width="2" marker-end="url(#arrow)"/>
  <line x1="570" y1="100" x2="595" y2="100" stroke="#3d9cf0" stroke-width="2" marker-end="url(#arrow)"/>

  <!-- moving dots along path -->
  <circle r="6" fill="#2ec4a8" class="anim">
    <animateMotion dur="3s" repeatCount="indefinite" path="M75,100 L215,100 L360,100 L510,100 L660,100"/>
  </circle>
  <circle r="6" fill="#3d9cf0" class="anim">
    <animateMotion dur="3s" begin="1s" repeatCount="indefinite" path="M75,100 L215,100 L360,100 L510,100 L660,100"/>
  </circle>
  <circle r="6" fill="#f0a030" class="anim">
    <animateMotion dur="3s" begin="2s" repeatCount="indefinite" path="M75,100 L215,100 L360,100 L510,100 L660,100"/>
  </circle>

  <text x="20" y="40" fill="#e8eef6" font-size="15" font-family="Segoe UI,sans-serif">Inbound pipeline (rodbus / dnp3 shaped)</text>
  <text x="20" y="190" fill="#9aadc4" font-size="12" font-family="Segoe UI,sans-serif">Each stage returns NeedMore, a complete unit, or an error that resets/closes.</text>
</svg>
</div>
<p class="caption">Figure 2 — Bytes move stage by stage. Partial reads stop at the buffer until the frame state machine can finish.</p>
'''

def svg_fsm():
    return r'''
<div class="diagram" id="diag-fsm">
<svg viewBox="0 0 760 300" xmlns="http://www.w3.org/2000/svg" aria-label="Link layer sync hunt state machine">
  <text x="20" y="28" fill="#e8eef6" font-size="15" font-family="Segoe UI,sans-serif">Incremental frame state machine (Distributed Network Protocol 3 link style)</text>

  <g id="s1">
    <rect x="30" y="70" width="130" height="50" rx="10" fill="#1e3a5f" stroke="#3d9cf0" class="anim anim-state"/>
    <text x="95" y="100" text-anchor="middle" fill="#fff" font-size="13" font-family="Segoe UI,sans-serif">FindSync1</text>
  </g>
  <g>
    <rect x="200" y="70" width="130" height="50" rx="10" fill="#1e3a5f" stroke="#3d9cf0"/>
    <text x="265" y="100" text-anchor="middle" fill="#fff" font-size="13" font-family="Segoe UI,sans-serif">FindSync2</text>
  </g>
  <g>
    <rect x="370" y="70" width="130" height="50" rx="10" fill="#1a3d3a" stroke="#2ec4a8"/>
    <text x="435" y="100" text-anchor="middle" fill="#fff" font-size="13" font-family="Segoe UI,sans-serif">ReadHeader</text>
  </g>
  <g>
    <rect x="540" y="70" width="160" height="50" rx="10" fill="#3a2a1e" stroke="#f0a030"/>
    <text x="620" y="100" text-anchor="middle" fill="#fff" font-size="13" font-family="Segoe UI,sans-serif">ReadBody</text>
  </g>

  <defs>
    <marker id="a2" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#9aadc4"/></marker>
  </defs>
  <line x1="160" y1="95" x2="195" y2="95" stroke="#9aadc4" marker-end="url(#a2)"/>
  <line x1="330" y1="95" x2="365" y2="95" stroke="#9aadc4" marker-end="url(#a2)"/>
  <line x1="500" y1="95" x2="535" y2="95" stroke="#9aadc4" marker-end="url(#a2)"/>

  <path d="M620 120 C620 180, 95 180, 95 125" fill="none" stroke="#e85d5d" stroke-width="1.5" marker-end="url(#a2)" class="anim anim-dash"/>
  <text x="300" y="200" fill="#e85d5d" font-size="12" font-family="Segoe UI,sans-serif">checksum / length error → reset (fail soft) or close (fail closed)</text>

  <rect x="30" y="230" width="700" height="50" rx="8" fill="#0b1018" stroke="#2a3a52"/>
  <text x="50" y="260" fill="#9aadc4" font-size="13" font-family="Consolas,monospace">stream: ... 12 05 64 [header+CRC] [body blocks+CRC] ...</text>
  <rect x="118" y="242" width="28" height="26" rx="4" fill="#3d9cf0" opacity="0.85" class="anim anim-pulse"/>
</svg>
</div>
<p class="caption">Figure 3 — Sync hunt then header then body. Same shape appears in Modbus Transmission Control Protocol (Begin→Header) and Transport Packet waiting states.</p>
'''

def svg_actor():
    return r'''
<div class="diagram" id="diag-actor">
<svg viewBox="0 0 760 280" xmlns="http://www.w3.org/2000/svg" aria-label="Session actor and mailbox">
  <text x="20" y="28" fill="#e8eef6" font-size="15" font-family="Segoe UI,sans-serif">Session actor (rodbus Channel / dnp3 MasterTask)</text>

  <rect x="40" y="70" width="180" height="150" rx="12" fill="#243044" stroke="#3d9cf0"/>
  <text x="130" y="100" text-anchor="middle" fill="#fff" font-size="14" font-family="Segoe UI,sans-serif">User / API</text>
  <text x="130" y="125" text-anchor="middle" fill="#9aadc4" font-size="12" font-family="Segoe UI,sans-serif">cloneable handle</text>
  <text x="130" y="150" text-anchor="middle" fill="#9aadc4" font-size="12" font-family="Segoe UI,sans-serif">read / write / enable</text>
  <text x="130" y="185" text-anchor="middle" fill="#2ec4a8" font-size="12" font-family="Segoe UI,sans-serif">Promise / oneshot</text>

  <rect x="280" y="115" width="120" height="60" rx="10" fill="#1a3d3a" stroke="#2ec4a8"/>
  <text x="340" y="140" text-anchor="middle" fill="#fff" font-size="13" font-family="Segoe UI,sans-serif">Mailbox</text>
  <text x="340" y="158" text-anchor="middle" fill="#9aadc4" font-size="11" font-family="Segoe UI,sans-serif">mpsc queue</text>
  <rect x="300" y="130" width="18" height="14" rx="3" fill="#f0a030" class="anim anim-mail"/>

  <rect x="460" y="55" width="260" height="180" rx="12" fill="#1e3a5f" stroke="#f0a030"/>
  <text x="590" y="85" text-anchor="middle" fill="#fff" font-size="14" font-family="Segoe UI,sans-serif">Session task owns</text>
  <text x="590" y="115" text-anchor="middle" fill="#c5d4e6" font-size="12" font-family="Segoe UI,sans-serif">• socket / serial port</text>
  <text x="590" y="138" text-anchor="middle" fill="#c5d4e6" font-size="12" font-family="Segoe UI,sans-serif">• parser state</text>
  <text x="590" y="161" text-anchor="middle" fill="#c5d4e6" font-size="12" font-family="Segoe UI,sans-serif">• sequence / timers</text>
  <text x="590" y="184" text-anchor="middle" fill="#c5d4e6" font-size="12" font-family="Segoe UI,sans-serif">• one in-flight request</text>
  <text x="590" y="210" text-anchor="middle" fill="#9aadc4" font-size="11" font-family="Segoe UI,sans-serif">select!: I/O · mail · timeout</text>

  <line x1="220" y1="145" x2="275" y2="145" stroke="#3d9cf0" stroke-width="2"/>
  <line x1="400" y1="145" x2="455" y2="145" stroke="#3d9cf0" stroke-width="2"/>
</svg>
</div>
<p class="caption">Figure 4 — Outside code never touches the socket. The actor serializes work and correlates replies.</p>
'''

def svg_three_stacks():
    return r'''
<div class="diagram" id="diag-three">
<svg viewBox="0 0 760 360" xmlns="http://www.w3.org/2000/svg" aria-label="Three stacks compared">
  <text x="20" y="28" fill="#e8eef6" font-size="15" font-family="Segoe UI,sans-serif">Three stacks — height of the sandwich</text>

  <!-- rodbus -->
  <text x="120" y="55" text-anchor="middle" fill="#2ec4a8" font-size="14" font-family="Segoe UI,sans-serif">rodbus</text>
  <rect x="50" y="70" width="140" height="40" rx="8" fill="#1e3a5f" stroke="#3d9cf0"/>
  <text x="120" y="95" text-anchor="middle" fill="#fff" font-size="12">App PDU</text>
  <rect x="50" y="120" width="140" height="40" rx="8" fill="#1a3d3a" stroke="#2ec4a8"/>
  <text x="120" y="145" text-anchor="middle" fill="#fff" font-size="12">MBAP / RTU coat</text>
  <rect x="50" y="170" width="140" height="40" rx="8" fill="#3a2a1e" stroke="#f0a030"/>
  <text x="120" y="195" text-anchor="middle" fill="#fff" font-size="12">Physical</text>
  <text x="120" y="235" text-anchor="middle" fill="#9aadc4" font-size="11">coils / registers</text>

  <!-- dnp3 -->
  <text x="380" y="55" text-anchor="middle" fill="#3d9cf0" font-size="14" font-family="Segoe UI,sans-serif">dnp3</text>
  <rect x="310" y="70" width="140" height="36" rx="8" fill="#1e3a5f" stroke="#3d9cf0"/>
  <text x="380" y="93" text-anchor="middle" fill="#fff" font-size="12">Application</text>
  <rect x="310" y="112" width="140" height="36" rx="8" fill="#243044" stroke="#9aadc4"/>
  <text x="380" y="135" text-anchor="middle" fill="#fff" font-size="12">Transport FIR/FIN</text>
  <rect x="310" y="154" width="140" height="36" rx="8" fill="#1a3d3a" stroke="#2ec4a8"/>
  <text x="380" y="177" text-anchor="middle" fill="#fff" font-size="12">Link 0x0564+CRC</text>
  <rect x="310" y="196" width="140" height="36" rx="8" fill="#3a2a1e" stroke="#f0a030"/>
  <text x="380" y="219" text-anchor="middle" fill="#fff" font-size="12">Physical</text>
  <text x="380" y="255" text-anchor="middle" fill="#9aadc4" font-size="11">points + events</text>

  <!-- iec -->
  <text x="640" y="55" text-anchor="middle" fill="#f0a030" font-size="14" font-family="Segoe UI,sans-serif">libIEC61850</text>
  <rect x="570" y="70" width="150" height="28" rx="6" fill="#1e3a5f" stroke="#3d9cf0"/>
  <text x="645" y="88" text-anchor="middle" fill="#fff" font-size="11">Abstract services</text>
  <rect x="570" y="102" width="150" height="28" rx="6" fill="#243044" stroke="#9aadc4"/>
  <text x="645" y="120" text-anchor="middle" fill="#fff" font-size="11">MMS mapping</text>
  <rect x="570" y="134" width="150" height="28" rx="6" fill="#1a3d3a" stroke="#2ec4a8"/>
  <text x="645" y="152" text-anchor="middle" fill="#fff" font-size="11">MMS / ACSE / ISO</text>
  <rect x="570" y="166" width="150" height="28" rx="6" fill="#2a3044" stroke="#9aadc4"/>
  <text x="645" y="184" text-anchor="middle" fill="#fff" font-size="11">COTP + TPKT</text>
  <rect x="570" y="198" width="150" height="28" rx="6" fill="#3a2a1e" stroke="#f0a030"/>
  <text x="645" y="216" text-anchor="middle" fill="#fff" font-size="11">HAL sockets</text>
  <text x="645" y="255" text-anchor="middle" fill="#9aadc4" font-size="11">+ GOOSE/SV plane</text>

  <rect x="50" y="280" width="670" height="55" rx="10" fill="#0b1018" stroke="#2a3a52"/>
  <text x="70" y="305" fill="#c5d4e6" font-size="13" font-family="Segoe UI,sans-serif">Same ideas at every height: physical → frame → meaning → session actor / thread.</text>
  <text x="70" y="325" fill="#9aadc4" font-size="12" font-family="Segoe UI,sans-serif">IEC 61850 adds a second plane (Ethernet multicast) beside the tall client/server stack.</text>

  <circle cx="120" cy="50" r="4" fill="#2ec4a8" class="anim anim-pulse"/>
  <circle cx="380" cy="50" r="4" fill="#3d9cf0" class="anim anim-pulse"/>
  <circle cx="640" cy="50" r="4" fill="#f0a030" class="anim anim-pulse"/>
</svg>
</div>
<p class="caption">Figure 5 — Complexity grows with semantic richness and number of layers — not with “using Rust versus C.”</p>
'''

def svg_translator():
    return r'''
<div class="diagram" id="diag-xlate">
<svg viewBox="0 0 760 320" xmlns="http://www.w3.org/2000/svg" aria-label="Protocol translation service">
  <text x="20" y="28" fill="#e8eef6" font-size="15" font-family="Segoe UI,sans-serif">Protocol translation service — canonical core</text>

  <rect x="30" y="60" width="190" height="200" rx="12" fill="#1a3d3a" stroke="#2ec4a8"/>
  <text x="125" y="90" text-anchor="middle" fill="#fff" font-size="14">Southbound</text>
  <text x="125" y="115" text-anchor="middle" fill="#9aadc4" font-size="12">Stack A</text>
  <text x="125" y="150" text-anchor="middle" fill="#c5d4e6" font-size="12">phys → frame</text>
  <text x="125" y="170" text-anchor="middle" fill="#c5d4e6" font-size="12">→ app → session</text>
  <text x="125" y="210" text-anchor="middle" fill="#2ec4a8" font-size="12">Modbus example</text>

  <rect x="285" y="50" width="190" height="220" rx="12" fill="#1e3a5f" stroke="#3d9cf0"/>
  <text x="380" y="80" text-anchor="middle" fill="#fff" font-size="14">Canonical core</text>
  <text x="380" y="110" text-anchor="middle" fill="#c5d4e6" font-size="12">point store</text>
  <text x="380" y="132" text-anchor="middle" fill="#c5d4e6" font-size="12">quality · time</text>
  <text x="380" y="154" text-anchor="middle" fill="#c5d4e6" font-size="12">mapping table</text>
  <text x="380" y="176" text-anchor="middle" fill="#c5d4e6" font-size="12">policy / auth</text>
  <text x="380" y="198" text-anchor="middle" fill="#c5d4e6" font-size="12">event queue</text>
  <text x="380" y="230" text-anchor="middle" fill="#f0a030" font-size="12">never raw bytes</text>

  <rect x="540" y="60" width="190" height="200" rx="12" fill="#3a2a1e" stroke="#f0a030"/>
  <text x="635" y="90" text-anchor="middle" fill="#fff" font-size="14">Northbound</text>
  <text x="635" y="115" text-anchor="middle" fill="#9aadc4" font-size="12">Stack B</text>
  <text x="635" y="150" text-anchor="middle" fill="#c5d4e6" font-size="12">session → app</text>
  <text x="635" y="170" text-anchor="middle" fill="#c5d4e6" font-size="12">→ frame → phys</text>
  <text x="635" y="210" text-anchor="middle" fill="#f0a030" font-size="12">DNP3 example</text>

  <path d="M220 140 L280 140" stroke="#2ec4a8" stroke-width="3" class="anim anim-dash"/>
  <path d="M475 140 L535 140" stroke="#f0a030" stroke-width="3" class="anim anim-dash"/>

  <circle r="7" fill="#2ec4a8" class="anim">
    <animateMotion dur="2.5s" repeatCount="indefinite" path="M125,160 L380,160 L635,160"/>
  </circle>
  <circle r="7" fill="#f0a030" class="anim">
    <animateMotion dur="2.5s" begin="1.2s" repeatCount="indefinite" path="M635,180 L380,180 L125,180"/>
  </circle>

  <text x="30" y="290" fill="#9aadc4" font-size="12" font-family="Segoe UI,sans-serif">Measurements flow A→core→B. Commands flow B→core→A. Bound the queues.</text>
</svg>
</div>
<p class="caption">Figure 6 — Translation through meaning, not through byte tunnels. Green = measurements, amber = commands.</p>
'''

def svg_iec_planes():
    return r'''
<div class="diagram" id="diag-planes">
<svg viewBox="0 0 760 300" xmlns="http://www.w3.org/2000/svg" aria-label="IEC 61850 two planes">
  <text x="20" y="28" fill="#e8eef6" font-size="15" font-family="Segoe UI,sans-serif">IEC 61850 — two communication planes</text>

  <rect x="220" y="50" width="320" height="60" rx="12" fill="#243044" stroke="#9aadc4"/>
  <text x="380" y="75" text-anchor="middle" fill="#fff" font-size="14">Live data model (logical devices / nodes)</text>
  <text x="380" y="95" text-anchor="middle" fill="#9aadc4" font-size="12">engineering-time Substation Configuration Language → C structs</text>

  <rect x="40" y="140" width="300" height="120" rx="12" fill="#1e3a5f" stroke="#3d9cf0"/>
  <text x="190" y="175" text-anchor="middle" fill="#fff" font-size="14">Client / server plane</text>
  <text x="190" y="200" text-anchor="middle" fill="#c5d4e6" font-size="12">Transmission Control Protocol</text>
  <text x="190" y="220" text-anchor="middle" fill="#c5d4e6" font-size="12">Manufacturing Message Specification</text>
  <text x="190" y="240" text-anchor="middle" fill="#9aadc4" font-size="12">reports · control · directory</text>

  <rect x="420" y="140" width="300" height="120" rx="12" fill="#1a3d3a" stroke="#2ec4a8"/>
  <text x="570" y="175" text-anchor="middle" fill="#fff" font-size="14">Publisher / subscriber plane</text>
  <text x="570" y="200" text-anchor="middle" fill="#c5d4e6" font-size="12">Ethernet multicast</text>
  <text x="570" y="220" text-anchor="middle" fill="#c5d4e6" font-size="12">GOOSE · Sampled Values</text>
  <text x="570" y="240" text-anchor="middle" fill="#9aadc4" font-size="12">millisecond-class events</text>

  <line x1="300" y1="110" x2="190" y2="140" stroke="#3d9cf0" stroke-width="2" class="anim anim-dash"/>
  <line x1="460" y1="110" x2="570" y2="140" stroke="#2ec4a8" stroke-width="2" class="anim anim-dash"/>
</svg>
</div>
<p class="caption">Figure 7 — Missing the publisher/subscriber plane means missing protection-speed events.</p>
'''

def svg_dnp_flow():
    return r'''
<div class="diagram" id="diag-dnp">
<svg viewBox="0 0 760 260" xmlns="http://www.w3.org/2000/svg" aria-label="DNP3 segment assembly">
  <text x="20" y="28" fill="#e8eef6" font-size="15" font-family="Segoe UI,sans-serif">Distributed Network Protocol 3 — transport assembly</text>

  <rect x="40" y="60" width="150" height="70" rx="10" fill="#3a2a1e" stroke="#f0a030"/>
  <text x="115" y="90" text-anchor="middle" fill="#fff" font-size="12">Link frame 1</text>
  <text x="115" y="110" text-anchor="middle" fill="#f0a030" font-size="11">FIR=1 FIN=0</text>

  <rect x="220" y="60" width="150" height="70" rx="10" fill="#3a2a1e" stroke="#f0a030"/>
  <text x="295" y="90" text-anchor="middle" fill="#fff" font-size="12">Link frame 2</text>
  <text x="295" y="110" text-anchor="middle" fill="#f0a030" font-size="11">FIR=0 FIN=0</text>

  <rect x="400" y="60" width="150" height="70" rx="10" fill="#3a2a1e" stroke="#f0a030"/>
  <text x="475" y="90" text-anchor="middle" fill="#fff" font-size="12">Link frame 3</text>
  <text x="475" y="110" text-anchor="middle" fill="#2ec4a8" font-size="11">FIR=0 FIN=1</text>

  <path d="M115 130 L115 160 L475 160 L475 130" fill="none" stroke="#3d9cf0" stroke-width="2" class="anim anim-dash"/>

  <rect x="200" y="175" width="360" height="55" rx="10" fill="#1e3a5f" stroke="#3d9cf0" class="anim anim-pulse"/>
  <text x="380" y="207" text-anchor="middle" fill="#fff" font-size="14">Complete application fragment → zero-copy parse</text>

  <text x="580" y="100" fill="#9aadc4" font-size="12" font-family="Segoe UI,sans-serif">Empty→Running→Complete</text>
</svg>
</div>
<p class="caption">Figure 8 — First/Final flags reassemble multi-frame application messages before object parsing.</p>
'''

JS = r"""
(function(){
  const links = [...document.querySelectorAll('nav a[href^="#"]')];
  const sections = links.map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  const io = new IntersectionObserver((entries) => {
    entries.forEach(en => {
      if (!en.isIntersecting) return;
      links.forEach(l => l.classList.toggle('active', l.getAttribute('href') === '#' + en.target.id));
    });
  }, { rootMargin: '-40% 0px -50% 0px', threshold: 0.01 });
  sections.forEach(s => io.observe(s));

  document.querySelectorAll('[data-toggle-anim]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.body.classList.toggle('paused');
      const paused = document.body.classList.contains('paused');
      btn.textContent = paused ? 'Resume animations' : 'Pause animations';
    });
  });
})();
""" + "\n" + walkthroughs.EXTRA_JS + "\n"

def chapter(cid, title, body):
    return f'<section class="chapter" id="{cid}">\n<h2>{title}</h2>\n{body}\n</section>\n'

chapters_html = []

chapters_html.append(chapter("intro", "Course introduction", f'''
<p class="lead">A self-contained course on structuring industrial protocol stacks and protocol translation services, distilled from <strong>rodbus</strong> (Modbus), <strong>dnp3</strong> (Distributed Network Protocol 3), and <strong>libIEC61850</strong> (International Electrotechnical Commission 61850).</p>
<p><span class="pill">Offline</span><span class="pill">Airplane ready</span><span class="pill">Acronyms expanded</span></p>
<div class="controls"><button type="button" data-toggle-anim>Pause animations</button></div>
{svg_layers()}
<div class="callout"><strong>How to study:</strong> skim animated figures first, then read the matching Markdown chapters in <code>markdown/chapters/</code> for depth. The full text is also in <code>markdown/COURSE.md</code>.</div>
'''))

chapters_html.append(chapter("ch1", "1 — Why protocol stacks exist", f'''
<p>Industrial devices speak different wire languages. A <strong>protocol translation service</strong> sits between them and moves <em>meaning</em> — not raw bytes — from one format to another.</p>
<div class="grid2">
  <div class="card"><h3>Without layers</h3><ul class="tight"><li>Partial Transmission Control Protocol reads break parsers</li><li>Serial noise desynchronizes streams</li><li>Reconnects tangle with application logic</li><li>You cannot tell which layer failed</li></ul></div>
  <div class="card"><h3>With layers</h3><ul class="tight"><li>Physical adapter owns sockets</li><li>Framer owns delimiters and checksums</li><li>Session owns timers and correlation</li><li>Domain model owns process meaning</li></ul></div>
</div>
{svg_pipeline()}
'''))

chapters_html.append(chapter("ch2", "2 — Mental models", f'''
<table>
<tr><th>Model</th><th>Picture</th><th>Seen in</th></tr>
<tr><td>Layered sandwich</td><td>Vertical folders by layer</td><td>All three</td></tr>
<tr><td>Byte pipeline</td><td>NeedMore / Frame / Error</td><td>rodbus, dnp3</td></tr>
<tr><td>Session actor</td><td>One task owns the socket</td><td>rodbus, dnp3 (Tokio); libIEC61850 threads/ticks</td></tr>
<tr><td>Half-duplex conversation</td><td>One outstanding request</td><td>Modbus &amp; DNP3 masters</td></tr>
<tr><td>Two planes</td><td>Client/server + pub/sub</td><td>libIEC61850</td></tr>
<tr><td>Model as database</td><td>Tree or point store is truth</td><td>libIEC61850, dnp3 outstation</td></tr>
</table>
{svg_actor()}
<div class="warnbox">Fail soft (discard and resync) suits noisy serial. Fail closed (tear down) suits Transmission Control Protocol streams where desynchronization is fatal. <strong>dnp3</strong> exposes both as link error modes.</div>
'''))

chapters_html.append(chapter("ch3", "3 — Splitting into layers", f'''
<pre>Physical adapter
Framing / checksum / sync
Transport segmentation   ← needed by Distributed Network Protocol 3
Application codec
Session / association
Domain model
Product application programming interface</pre>
<p>For a <strong>translator</strong>, build <em>two stacks plus a boring canonical core</em>. Never let Stack A frame types appear in Stack B modules.</p>
{svg_translator()}
'''))

chapters_html.append(chapter("ch4", "4 — Parsing strategies", f'''
<p class="lead">Framing turns a byte stream into messages. Below: which strategy to pick, then an interactive step-by-step lab you can click through offline.</p>

<table>
<tr><th>Strategy</th><th>Best for</th><th>Worse for</th></tr>
<tr><td>Length-prefixed finite-state machine</td><td>Modbus Application Protocol on Transmission Control Protocol</td><td>Noisy serial alone; unclamped lengths</td></tr>
<tr><td>Sync hunt + cyclic redundancy check</td><td>Serial / Distributed Network Protocol 3 link</td><td>When a pure length header already delimits (unless standard requires sync)</td></tr>
<tr><td>Function-code length tables</td><td>Closed Modbus Remote Terminal Unit layouts</td><td>Unknown / vendor function codes</td></tr>
<tr><td>Idle-line silence</td><td>Hardware idle detect</td><td>Jittery software async runtimes</td></tr>
<tr><td>Transport first/final assembly</td><td>Segmented application messages (DNP3)</td><td>Protocols that never segment</td></tr>
<tr><td>Zero-copy cursors</td><td>High-rate same-language handlers</td><td>Long-lived stores / language bindings (copy instead)</td></tr>
<tr><td>Schema Basic Encoding Rules</td><td>Huge Manufacturing Message Specification catalogs</td><td>Tiny flash + ultra-hot multicast without trimming</td></tr>
<tr><td>Parser combinators</td><td>Prototypes</td><td>Certified industrial hot paths (these stacks avoid them)</td></tr>
</table>

{svg_fsm()}

<h3>Interactive parse lab</h3>
{walkthroughs.walkthroughs_html()}

<div class="callout">Full narrative, decision matrix, and worked micro-examples: Markdown <code>chapters/04-parsing.md</code>.</div>
'''))

chapters_html.append(chapter("ch5", "5 — Sessions and correlation", f'''
<ul>
<li><strong>Single in-flight request</strong> per channel keeps correlation simple (transaction identifier on Modbus Transmission Control Protocol; sequence on Distributed Network Protocol 3; “next frame” on Remote Terminal Unit).</li>
<li><strong>Still read while waiting</strong> so unsolicited messages cannot deadlock the session.</li>
<li><strong>Separate connectivity</strong> (connect / backoff) from protocol session (only runs while connected).</li>
<li><strong>Nested enums</strong> for select-before-operate, file transfer, and startup integrity sequences.</li>
</ul>
{svg_actor()}
'''))

chapters_html.append(chapter("ch6", "6 — Case study: Modbus (rodbus)", f'''
<p><span class="pill">Rust</span><span class="pill">Tokio actor</span><span class="pill">One Application Data Unit, two coats</span></p>
<ul>
<li>Shared protocol data unit; Transmission Control Protocol uses Modbus Application Protocol headers; serial uses unit identifier + cyclic redundancy check.</li>
<li>Remote Terminal Unit receive framing uses function-code length tables (not silence detection); transmit still applies 3.5 character-time gaps.</li>
<li>Channels start disabled; bad framing fails the session; Modbus exceptions do not.</li>
<li>Server maps many unit identifiers to handlers — gateway friendly.</li>
</ul>
<pre>PhysLayer → FrameWriter/FramedReader → ClientLoop/SessionTask → Channel/RequestHandler</pre>
'''))

chapters_html.append(chapter("ch7", "7 — Case study: Distributed Network Protocol 3 (dnp3)", f'''
<p><span class="pill">Rust</span><span class="pill">Link + Transport + Application</span><span class="pill">Unsolicited</span></p>
{svg_dnp_flow()}
<ul>
<li>Link: sync <code>0x05 0x64</code>, cyclic redundancy check blocks, frame count bit.</li>
<li>Transport: first/final/sequence assembler (<code>Empty → Running → Complete</code>).</li>
<li>Application: zero-copy object header parse; codegen for variations.</li>
<li>Master prioritizes automatic tasks (restart, integrity, unsolicited enable) with one transaction at a time.</li>
<li>Outstation: event database, duplicate hash detection, select-before-operate.</li>
</ul>
'''))

chapters_html.append(chapter("ch8", "8 — Case study: IEC 61850 (libIEC61850)", f'''
<p><span class="pill">C99</span><span class="pill">Dual plane</span><span class="pill">Model as database</span></p>
{svg_iec_planes()}
<ul>
<li>Client/server: Hardware Abstraction Layer → Transport Packet / Connection-Oriented Transport Protocol → ISO session/presentation → Association Control → Manufacturing Message Specification → Abstract Communication Service Interface.</li>
<li>Publisher/subscriber: Generic Object Oriented Substation Event and Sampled Values on Ethernet (hand Basic Encoding Rules).</li>
<li>Substation Configuration Language compiled offline to static C models (or dynamic APIs / text config).</li>
<li>Threading: multi, single, or threadless poll via <code>stack_config.h</code>.</li>
<li>Your folder’s <code>Library_IEC61850-1.6</code> is the same lineage at 1.6.0; prefer <code>libiec61850-1.6_develop</code> (1.6.2) for study.</li>
</ul>
'''))

chapters_html.append(chapter("ch9", "9 — Compare and contrast", f'''
{svg_three_stacks()}
<table>
<tr><th>Steal from…</th><th>Pattern</th></tr>
<tr><td>rodbus</td><td>Swappable coats; serialize masters; exceptions ≠ transport faults</td></tr>
<tr><td>dnp3</td><td>Transport module; unsolicited-first-class; duplicate cache</td></tr>
<tr><td>libIEC61850</td><td>Rich canonical semantics; engineering-time mapping; second plane</td></tr>
</table>
'''))

chapters_html.append(chapter("ch10", "10 — Canonical core & translation blueprint", f'''
<p class="lead">A <strong>canonical core</strong> is one agreed internal representation of process truth — independent of any single wire protocol. Protocol stacks are adapters; the core is the product’s process image plus the rules for changing it.</p>

{svg_translator()}

<div class="grid2">
  <div class="card">
    <h3>Why prefer a core</h3>
    <ul class="tight">
      <li><strong>Avoid N² bridges</strong> — 6 protocols need 6 adapters with a core, but 30 pairwise directed bridges without one</li>
      <li><strong>Meaning survives quirks</strong> — quality, time, scaling live once</li>
      <li><strong>Test without sockets</strong> — fake adapters against the store</li>
      <li><strong>Authorize once</strong> — after decode, before side effects</li>
      <li><strong>Evolve</strong> — add protocol C without rewriting A↔B</li>
    </ul>
  </div>
  <div class="card">
    <h3>What the core holds</h3>
    <ul class="tight">
      <li>Point store (value, quality, time, origin)</li>
      <li>Event / change queue (bounded)</li>
      <li>Command bus + correlation tokens</li>
      <li>Mapping table (data-driven)</li>
      <li>Policy (scale, deadband, auth)</li>
      <li>Clock / time-source labels</li>
    </ul>
  </div>
</div>

<div class="warnbox"><strong>Not a core:</strong> shared socket buffers, pairwise byte tunnels, or <code>if protocol==Modbus</code> switches inside another protocol’s encoder. <strong>Thin bridges</strong> are only for disposable lab shims or same-protocol proxies — still isolate framing.</div>

<table>
<tr><th>In adapters (stacks)</th><th>In canonical core</th></tr>
<tr><td>Sync, checksums, session actors, transaction ids</td><td>Stable identifiers, quality, mapping, product interlocks</td></tr>
<tr><td>Wire select-before-operate state</td><td>Policy: how northbound arming maps to southbound writes</td></tr>
<tr><td>Per-protocol decode logs</td><td>Cross-hop metrics and “last value” views</td></tr>
</table>

<pre>southbound decode → map → policy → point store → event queue → northbound encode
northbound command → authorize → map → southbound write/select-operate → ack</pre>

<div class="callout">Never block southbound on northbound back-pressure — bounded queues with an explicit shed policy. Never upgrade invalid quality to good. Full deep-dive: Markdown <code>chapters/10-translation-service.md</code>.</div>
'''))

chapters_html.append(chapter("ch11", "11 — Trade-offs and checklist", f'''
<div class="card">
<strong>Printable checklist highlights</strong>
<ul class="tight">
<li>Hard maximum frame size before copy</li>
<li>Parser <code>reset()</code> on errors</li>
<li>Unique socket ownership</li>
<li>Unsolicited cannot complete the wrong promise</li>
<li>Mapping data-driven; quality preserved</li>
<li>Health shows session states; chaos-test reconnects</li>
</ul>
</div>
<p>Full checklist and trade-off tables live in Markdown chapter 11.</p>
'''))

chapters_html.append(chapter("ch12", "12 — Capstone exercises", f'''
<ol>
<li>Draw a sandwich for a protocol you know — what each layer must <em>not</em> know.</li>
<li>Design a sync/length/checksum frame state machine with fail-soft and fail-closed policies.</li>
<li>Explain how rodbus keeps one protocol data unit behind two coats.</li>
<li>Write pseudocode that handles unsolicited while a solicited request is pending.</li>
<li>Sketch Modbus ↔ Distributed Network Protocol 3 translation with mapping and queue-full policy.</li>
<li>List what you lose if you ignore the Generic Object Oriented Substation Event plane.</li>
<li>Audit a length-field allocation bug class.</li>
<li>Score one library against the chapter 11 checklist using file references (great airplane work).</li>
</ol>
<div class="callout">Detailed prompts and a glossary are in <code>markdown/chapters/12-exercises.md</code>.</div>
'''))

chapters_html.append(chapter("glossary", "Glossary", '''
<table>
<tr><th>Term</th><th>Definition</th></tr>
<tr><td>Application Data Unit</td><td>Framed packet including addressing fields around a protocol data unit</td></tr>
<tr><td>Canonical model / core</td><td>Translator’s internal process representation (point store, mapping, policy) independent of any single wire protocol</td></tr>
<tr><td>Cyclic redundancy check</td><td>Checksum detecting corruption</td></tr>
<tr><td>Fail closed / fail soft</td><td>Abort session versus resynchronize after bad frames</td></tr>
<tr><td>Session actor</td><td>Task or thread that owns protocol state and input/output</td></tr>
<tr><td>Sync hunt</td><td>Searching a stream for start-of-frame markers</td></tr>
<tr><td>Zero-copy</td><td>Borrow buffer slices instead of allocating new storage</td></tr>
<tr><td>Select before operate</td><td>Two-step control arming pattern</td></tr>
</table>
'''))

nav = '''
<nav>
  <h1>Protocol Stack Course</h1>
  <div class="tag">Self-contained · offline HTML</div>
  <div class="group">Start</div>
  <a href="#intro">Introduction &amp; figure 1</a>
  <div class="group">Foundations</div>
  <a href="#ch1">1. Why stacks exist</a>
  <a href="#ch2">2. Mental models</a>
  <a href="#ch3">3. Layering</a>
  <a href="#ch4">4. Parsing + lab</a>
  <a href="#ch5">5. Sessions</a>
  <div class="group">Case studies</div>
  <a href="#ch6">6. Modbus / rodbus</a>
  <a href="#ch7">7. DNP3</a>
  <a href="#ch8">8. IEC 61850</a>
  <div class="group">Design</div>
  <a href="#ch9">9. Compare</a>
  <a href="#ch10">10. Canonical core</a>
  <a href="#ch11">11. Trade-offs</a>
  <a href="#ch12">12. Exercises</a>
  <a href="#glossary">Glossary</a>
</nav>
'''

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta name="description" content="Self-contained course on industrial protocol stack architecture and translation services"/>
<title>Protocol Stack Architecture Course</title>
<style>
{CSS}
</style>
</head>
<body>
<div class="layout">
{nav}
<main>
<header class="hero">
  <h1>Protocol Stack Architecture</h1>
  <p>How production Modbus, Distributed Network Protocol 3, and International Electrotechnical Commission 61850 stacks are layered, parsed, and session-managed — and how to design a protocol translation service from those patterns.</p>
</header>
{''.join(chapters_html)}
<footer class="footer">
  <p>Companion Markdown: <code>../markdown/COURSE.md</code>. Analyzed trees are not redistributed here (respect upstream licenses). Animations use only inline Scalable Vector Graphics and Cascading Style Sheets.</p>
</footer>
</main>
</div>
<script>
{JS}
</script>
</body>
</html>
'''

OUT.write_text(html, encoding="utf-8")
print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")
