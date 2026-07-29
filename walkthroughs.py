# -*- coding: utf-8 -*-
"""Interactive step-by-step parsing walkthroughs for the HTML course."""

EXTRA_CSS = r"""
.walk {
  background: linear-gradient(180deg, #121a26, #0e1520);
  border: 1px solid var(--line); border-radius: 14px;
  padding: 1rem 1.1rem 1.1rem; margin: 1.25rem 0 0.75rem;
}
.walk h4 { margin: 0 0 0.35rem; color: #fff; font-size: 1.05rem; }
.walk .wsub { color: var(--muted); font-size: 0.85rem; margin: 0 0 0.75rem; }
.walk-toolbar {
  display: flex; flex-wrap: wrap; gap: 0.45rem; align-items: center;
  margin: 0 0 0.75rem;
}
.walk-toolbar button {
  background: var(--bg3); color: var(--text); border: 1px solid var(--line);
  border-radius: 8px; padding: 0.4rem 0.75rem; cursor: pointer; font: inherit;
}
.walk-toolbar button:hover { border-color: var(--accent); }
.walk-toolbar button:disabled { opacity: 0.4; cursor: default; }
.walk-toolbar .step-label {
  margin-left: auto; font-size: 0.85rem; color: var(--accent2);
  font-variant-numeric: tabular-nums;
}
.byte-row {
  display: flex; flex-wrap: wrap; gap: 0.35rem; margin: 0.5rem 0 0.75rem;
  font-family: var(--mono); font-size: 0.78rem;
}
.byte {
  min-width: 2.4rem; text-align: center; padding: 0.35rem 0.25rem;
  border-radius: 6px; background: #0b1018; border: 1px solid #2a3a52;
  color: #9aadc4; transition: background .2s, border-color .2s, color .2s, transform .2s;
}
.byte .bl { display: block; font-size: 0.65rem; color: #6a7d94; margin-top: 0.15rem; }
.byte.on {
  background: rgba(61,156,240,0.25); border-color: var(--accent); color: #fff;
  transform: translateY(-2px);
}
.byte.ok {
  background: rgba(46,196,168,0.22); border-color: var(--accent2); color: #fff;
}
.byte.bad {
  background: rgba(232,93,93,0.25); border-color: var(--danger); color: #fff;
}
.byte.dim { opacity: 0.35; }
.state-row {
  display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.5rem 0 0.75rem;
}
.state-pill {
  padding: 0.35rem 0.65rem; border-radius: 999px; border: 1px solid var(--line);
  background: #0b1018; color: var(--muted); font-size: 0.8rem;
  transition: all .2s;
}
.state-pill.on {
  background: rgba(46,196,168,0.2); border-color: var(--accent2); color: #fff;
}
.narrate {
  min-height: 3.2rem; padding: 0.75rem 0.9rem; border-radius: 10px;
  background: rgba(61,156,240,0.08); border-left: 3px solid var(--accent);
  color: #c5d4e6; font-size: 0.92rem;
}
.walk svg { width: 100%; height: auto; display: block; margin: 0.5rem 0; }
.tabbar { display: flex; flex-wrap: wrap; gap: 0.35rem; margin: 0.75rem 0; }
.tabbar button {
  background: transparent; color: var(--muted); border: 1px solid var(--line);
  border-radius: 999px; padding: 0.35rem 0.7rem; cursor: pointer; font: inherit; font-size: 0.82rem;
}
.tabbar button.on {
  background: var(--bg3); color: #fff; border-color: var(--accent);
}
.walk-panel { display: none; }
.walk-panel.on { display: block; }
"""

def walkthroughs_html():
    return r'''
<div class="card">
  <strong>Interactive parse lab</strong> — use <em>Next</em> / <em>Back</em> (or Auto-play) to walk each strategy one step at a time. Bytes highlight as the parser consumes them. Works fully offline.
</div>

<div class="tabbar" id="parse-tabs" role="tablist">
  <button type="button" class="on" data-tab="len">1. Length-prefixed</button>
  <button type="button" data-tab="sync">2. Sync hunt + check</button>
  <button type="button" data-tab="fc">3. Function-code table</button>
  <button type="button" data-tab="tr">4. Transport assemble</button>
  <button type="button" data-tab="ber">5. Tag-length-value</button>
</div>

<!-- LENGTH PREFIX -->
<div class="walk-panel on" id="panel-len">
<div class="walk" data-walk="len">
  <h4>Length-prefixed framing (Modbus Application Protocol style)</h4>
  <p class="wsub">Best on Transmission Control Protocol. Header tells you the body size. Clamp the length or an attacker allocates forever.</p>
  <div class="walk-toolbar">
    <button type="button" data-act="back">Back</button>
    <button type="button" data-act="next">Next</button>
    <button type="button" data-act="reset">Reset</button>
    <button type="button" data-act="auto">Auto-play</button>
    <span class="step-label" data-step-label>Step 0</span>
  </div>
  <div class="state-row">
    <span class="state-pill" data-state="Begin">Begin</span>
    <span class="state-pill" data-state="Header">Header</span>
    <span class="state-pill" data-state="Body">Read body</span>
    <span class="state-pill" data-state="Done">Frame ready</span>
    <span class="state-pill" data-state="Error">Error / close</span>
  </div>
  <svg viewBox="0 0 720 110" aria-hidden="true">
    <rect x="20" y="30" width="680" height="50" rx="8" fill="#0b1018" stroke="#2a3a52"/>
    <text x="40" y="20" fill="#9aadc4" font-size="12" font-family="Segoe UI,sans-serif">Stream buffer (partial reads arrive over time)</text>
    <rect data-viz="cursor" x="36" y="36" width="8" height="38" fill="#3d9cf0" opacity="0.9"/>
  </svg>
  <div class="byte-row" data-bytes></div>
  <div class="narrate" data-narrate></div>
</div>
</div>

<!-- SYNC HUNT -->
<div class="walk-panel" id="panel-sync">
<div class="walk" data-walk="sync">
  <h4>Sync hunt + integrity check (Distributed Network Protocol 3 link style)</h4>
  <p class="wsub">Best on noisy serial. Hunt magic bytes, read header, verify check. Fail soft = resync; fail closed = tear down.</p>
  <div class="walk-toolbar">
    <button type="button" data-act="back">Back</button>
    <button type="button" data-act="next">Next</button>
    <button type="button" data-act="reset">Reset</button>
    <button type="button" data-act="auto">Auto-play</button>
    <span class="step-label" data-step-label>Step 0</span>
  </div>
  <div class="state-row">
    <span class="state-pill" data-state="FindSync1">FindSync1</span>
    <span class="state-pill" data-state="FindSync2">FindSync2</span>
    <span class="state-pill" data-state="ReadHeader">ReadHeader</span>
    <span class="state-pill" data-state="ReadBody">ReadBody</span>
    <span class="state-pill" data-state="Done">Accept</span>
    <span class="state-pill" data-state="Resync">Fail soft resync</span>
  </div>
  <div class="byte-row" data-bytes></div>
  <div class="narrate" data-narrate></div>
</div>
</div>

<!-- FUNCTION CODE TABLE -->
<div class="walk-panel" id="panel-fc">
<div class="walk" data-walk="fc">
  <h4>Function-code length table (Modbus Remote Terminal Unit style)</h4>
  <p class="wsub">Best when layouts are a closed set. Read unit id + function code, look up exact remaining length, then check cyclic redundancy check. Unknown function codes cannot be delimited.</p>
  <div class="walk-toolbar">
    <button type="button" data-act="back">Back</button>
    <button type="button" data-act="next">Next</button>
    <button type="button" data-act="reset">Reset</button>
    <button type="button" data-act="auto">Auto-play</button>
    <span class="step-label" data-step-label>Step 0</span>
  </div>
  <div class="state-row">
    <span class="state-pill" data-state="Start">Start</span>
    <span class="state-pill" data-state="Lookup">Lookup length</span>
    <span class="state-pill" data-state="ReadFull">Read full body</span>
    <span class="state-pill" data-state="Crc">Check CRC</span>
    <span class="state-pill" data-state="Done">Frame ready</span>
  </div>
  <div class="byte-row" data-bytes></div>
  <div class="narrate" data-narrate></div>
</div>
</div>

<!-- TRANSPORT -->
<div class="walk-panel" id="panel-tr">
<div class="walk" data-walk="tr">
  <h4>Transport first/final assembly (Distributed Network Protocol 3)</h4>
  <p class="wsub">Use when application messages span multiple link frames. Keep this module separate from sync hunt and from object decoding.</p>
  <div class="walk-toolbar">
    <button type="button" data-act="back">Back</button>
    <button type="button" data-act="next">Next</button>
    <button type="button" data-act="reset">Reset</button>
    <button type="button" data-act="auto">Auto-play</button>
    <span class="step-label" data-step-label>Step 0</span>
  </div>
  <div class="state-row">
    <span class="state-pill" data-state="Empty">Empty</span>
    <span class="state-pill" data-state="Running">Running</span>
    <span class="state-pill" data-state="Complete">Complete</span>
    <span class="state-pill" data-state="Drop">Drop / reset</span>
  </div>
  <svg viewBox="0 0 720 150" aria-hidden="true">
    <rect id="tr-f1" x="40" y="30" width="160" height="50" rx="8" fill="#0b1018" stroke="#2a3a52"/>
    <text x="120" y="60" text-anchor="middle" fill="#9aadc4" font-size="12" font-family="Segoe UI,sans-serif">Frame FIR=1</text>
    <rect id="tr-f2" x="280" y="30" width="160" height="50" rx="8" fill="#0b1018" stroke="#2a3a52"/>
    <text x="360" y="60" text-anchor="middle" fill="#9aadc4" font-size="12" font-family="Segoe UI,sans-serif">Frame mid</text>
    <rect id="tr-f3" x="520" y="30" width="160" height="50" rx="8" fill="#0b1018" stroke="#2a3a52"/>
    <text x="600" y="60" text-anchor="middle" fill="#9aadc4" font-size="12" font-family="Segoe UI,sans-serif">Frame FIN=1</text>
    <rect id="tr-out" x="160" y="100" width="400" height="36" rx="8" fill="#0b1018" stroke="#2a3a52"/>
    <text x="360" y="123" text-anchor="middle" fill="#9aadc4" font-size="12" font-family="Segoe UI,sans-serif">Assembled application fragment</text>
  </svg>
  <div class="byte-row" data-bytes></div>
  <div class="narrate" data-narrate></div>
</div>
</div>

<!-- BER TLV -->
<div class="walk-panel" id="panel-ber">
<div class="walk" data-walk="ber">
  <h4>Tag–length–value walk (Basic Encoding Rules style)</h4>
  <p class="wsub">Used heavily in International Electrotechnical Commission 61850 Manufacturing Message Specification and goose headers. Read tag, read length (clamp!), then value — recurse for constructed types.</p>
  <div class="walk-toolbar">
    <button type="button" data-act="back">Back</button>
    <button type="button" data-act="next">Next</button>
    <button type="button" data-act="reset">Reset</button>
    <button type="button" data-act="auto">Auto-play</button>
    <span class="step-label" data-step-label>Step 0</span>
  </div>
  <div class="state-row">
    <span class="state-pill" data-state="Tag">Read tag</span>
    <span class="state-pill" data-state="Len">Read length</span>
    <span class="state-pill" data-state="Val">Read value</span>
    <span class="state-pill" data-state="Nest">Nested field</span>
    <span class="state-pill" data-state="Done">Message complete</span>
  </div>
  <div class="byte-row" data-bytes></div>
  <div class="narrate" data-narrate></div>
</div>
</div>
'''

EXTRA_JS = r"""
(function(){
  const walks = {
    len: {
      bytes: [
        {h:'00', l:'tx'}, {h:'01', l:'tx'},
        {h:'00', l:'proto'}, {h:'00', l:'proto'},
        {h:'00', l:'len'}, {h:'06', l:'len'},
        {h:'01', l:'uid'},
        {h:'03', l:'fc'}, {h:'00', l:'hi'}, {h:'00', l:'lo'}, {h:'00', l:'qty'}, {h:'0A', l:'qty'}
      ],
      steps: [
        {state:'Begin', on:[], narrate:'Stream may deliver any number of bytes per read. State = Begin. We need 7 header bytes before we know the body length.', cursor:0},
        {state:'Begin', on:[0,1], narrate:'Arrived: transaction identifier 0x0001. Still need more header bytes (NeedMore).', cursor:2},
        {state:'Begin', on:[0,1,2,3], narrate:'Protocol identifier 0x0000 — must be zero for Modbus Application Protocol. Still NeedMore.', cursor:4},
        {state:'Header', on:[0,1,2,3,4,5], narrate:'Length field = 6. Clamp check: 0 < 6 ≤ 254 ✓. Transition to Header/body collection. Expect 6 bytes after the length field (unit id + protocol data unit).', cursor:6},
        {state:'Body', on:[0,1,2,3,4,5,6,7,8,9,10,11], cls:'ok', narrate:'Body complete: unit 1, function 3, read 10 registers starting at 0. Emit Frame. Application codec interprets the protocol data unit next.', cursor:12},
        {state:'Done', on:[0,1,2,3,4,5,6,7,8,9,10,11], cls:'ok', narrate:'Frame ready. Session correlates using the transaction identifier on Transmission Control Protocol. Prefer fail-closed if length were illegal.', cursor:12},
        {state:'Error', on:[4,5], cls:'bad', narrate:'Counter-example: if length were 0xFFFF, a correct stack rejects before allocate/copy and closes the session. Never trust the peer’s length blindly.', cursor:6}
      ]
    },
    sync: {
      bytes: [
        {h:'AA', l:'noise'}, {h:'05', l:'sync1'}, {h:'64', l:'sync2'},
        {h:'05', l:'len'}, {h:'C4', l:'ctrl'}, {h:'01', l:'dest'}, {h:'00', l:'dest'},
        {h:'02', l:'src'}, {h:'00', l:'src'}, {h:'AB', l:'hcrc'}, {h:'CD', l:'hcrc'},
        {h:'C0', l:'th'}, {h:'DE', l:'data'}, {h:'AD', l:'data'}, {h:'12', l:'bcrc'}, {h:'34', l:'bcrc'},
        {h:'05', l:'fake'}
      ],
      steps: [
        {state:'FindSync1', on:[0], narrate:'Noise byte 0xAA is not 0x05. Stay in FindSync1 and advance one byte (fail-soft mindset).', cursor:1},
        {state:'FindSync2', on:[1], narrate:'Saw 0x05 → FindSync2. Next byte must be 0x64 or we return to FindSync1.', cursor:2},
        {state:'ReadHeader', on:[1,2], narrate:'Saw 0x64. Sync locked. Read fixed link header fields and header cyclic redundancy check.', cursor:3},
        {state:'ReadHeader', on:[1,2,3,4,5,6,7,8,9,10], cls:'ok', narrate:'Header cyclic redundancy check passes. Compute body byte count from length field. Enter ReadBody; data also comes in checked blocks.', cursor:11},
        {state:'ReadBody', on:[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15], cls:'ok', narrate:'Body blocks + trailing check OK. Emit link frame payload upward to transport. False sync bytes inside payload would fail checks and resync.', cursor:16},
        {state:'Done', on:[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15], cls:'ok', narrate:'Accept frame. On Transmission Control Protocol, many stacks still use this framing because the standard requires it — but error policy is often fail-closed.', cursor:16},
        {state:'Resync', on:[16], cls:'bad', narrate:'If a check fails mid-body: fail soft returns to FindSync1 (serial), fail closed tears down (typical Transmission Control Protocol). Choose per medium.', cursor:16}
      ]
    },
    fc: {
      bytes: [
        {h:'01', l:'uid'}, {h:'03', l:'fc'},
        {h:'00', l:'addr'}, {h:'00', l:'addr'}, {h:'00', l:'qty'}, {h:'0A', l:'qty'},
        {h:'C5', l:'crc'}, {h:'CD', l:'crc'}
      ],
      steps: [
        {state:'Start', on:[], narrate:'Remote Terminal Unit request parser starts empty. Unlike silence detection, we will discover length from the function code.', cursor:0},
        {state:'Start', on:[0,1], narrate:'Read unit identifier 1 and function code 3 (read holding registers).', cursor:2},
        {state:'Lookup', on:[0,1], narrate:'Lookup request table: function 3 request body is exactly 4 bytes (start address + quantity). Remaining = 4 + 2 CRC.', cursor:2},
        {state:'ReadFull', on:[0,1,2,3,4,5], narrate:'Read the 4 body bytes. Still need cyclic redundancy check (NeedMore if truncated).', cursor:6},
        {state:'Crc', on:[0,1,2,3,4,5,6,7], narrate:'Read CRC. Compute CRC-16/Modbus over address+PDU and compare.', cursor:8},
        {state:'Done', on:[0,1,2,3,4,5,6,7], cls:'ok', narrate:'CRC OK → Frame. Application decode follows. Transmit path still inserts ~3.5 character idle for bus turnaround — separate concern from receive delimiting.', cursor:8},
        {state:'Lookup', on:[0], cls:'bad', narrate:'If function code were unknown, length cannot be known → hard frame error (cannot safely delimit). That is the main weakness of this strategy.', cursor:1}
      ]
    },
    tr: {
      bytes: [
        {h:'F1', l:'FIR'}, {h:'..', l:'pay'}, {h:'..', l:'pay'},
        {h:'M2', l:'mid'}, {h:'..', l:'pay'},
        {h:'L3', l:'FIN'}, {h:'..', l:'pay'}
      ],
      steps: [
        {state:'Empty', on:[], narrate:'Assembler Empty. Waiting for a transport segment with First flag set.', cursor:0},
        {state:'Running', on:[0,1,2], narrate:'Frame 1: First=1 Final=0 sequence=N. Clear any stale partial, copy payload, state=Running. (Highlight frame 1.)', cursor:3, tr:1},
        {state:'Running', on:[0,1,2,3,4], narrate:'Frame 2: First=0 Final=0 sequence=N+1. Append. Sequence mismatch would Drop.', cursor:5, tr:2},
        {state:'Complete', on:[0,1,2,3,4,5,6], cls:'ok', narrate:'Frame 3: First=0 Final=1. Append → Complete. Hand the full application fragment to zero-copy object parsing.', cursor:7, tr:3},
        {state:'Drop', on:[3], cls:'bad', narrate:'If a mid frame arrives with First=1 unexpectedly, or sequence skips, drop partial and restart. Never feed a torn fragment to the application codec.', cursor:4, tr:0}
      ]
    },
    ber: {
      bytes: [
        {h:'A1', l:'tag'}, {h:'08', l:'len'},
        {h:'02', l:'tag'}, {h:'01', l:'len'}, {h:'05', l:'int'},
        {h:'04', l:'tag'}, {h:'03', l:'len'}, {h:'41', l:'oct'}, {h:'42', l:'oct'}, {h:'43', l:'oct'}
      ],
      steps: [
        {state:'Tag', on:[0], narrate:'Read tag 0xA1 (context-specific, constructed). This value will contain nested fields.', cursor:1},
        {state:'Len', on:[0,1], narrate:'Length = 8. Clamp against remaining buffer and max depth/size policy before continuing.', cursor:2},
        {state:'Nest', on:[0,1,2,3,4], narrate:'Nested: tag 0x02 (integer), length 1, value 5. Hand parsers and asn1c both walk tag–length–value; hot paths often hand-roll this.', cursor:5},
        {state:'Val', on:[0,1,2,3,4,5,6,7,8,9], narrate:'Nested: tag 0x04 (octet string), length 3, bytes 41 42 43. Constructed parent length must account for all children.', cursor:10},
        {state:'Done', on:[0,1,2,3,4,5,6,7,8,9], cls:'ok', narrate:'Parent length satisfied → message/field complete. Reject indefinite lengths or deep nesting on untrusted links (hardening seen in libIEC61850 fixes).', cursor:10}
      ]
    }
  };

  function renderBytes(el, bytes) {
    el.innerHTML = bytes.map((b,i) =>
      `<div class="byte" data-i="${i}">${b.h}<span class="bl">${b.l}</span></div>`
    ).join('');
  }

  function applyStep(root, model, idx) {
    const step = model.steps[idx];
    const label = root.querySelector('[data-step-label]');
    const narr = root.querySelector('[data-narrate]');
    const byteEls = [...root.querySelectorAll('.byte')];
    const pills = [...root.querySelectorAll('.state-pill')];
    label.textContent = `Step ${idx + 1} / ${model.steps.length}`;
    narr.textContent = step.narrate;
    pills.forEach(p => p.classList.toggle('on', p.getAttribute('data-state') === step.state));
    byteEls.forEach((el, i) => {
      el.classList.remove('on','ok','bad','dim');
      if (step.on.includes(i)) el.classList.add(step.cls || 'on');
      else if (step.on.length) el.classList.add('dim');
    });
    const cursor = root.querySelector('[data-viz="cursor"]');
    if (cursor && typeof step.cursor === 'number') {
      cursor.setAttribute('x', String(36 + Math.min(step.cursor, 12) * 52));
    }
    if (root.getAttribute('data-walk') === 'tr') {
      const map = {0:'#2a3a52', 1:'#3d9cf0', 2:'#3d9cf0', 3:'#2ec4a8'};
      const n = step.tr || 0;
      ['tr-f1','tr-f2','tr-f3','tr-out'].forEach((id, i) => {
        const node = document.getElementById(id);
        if (!node) return;
        let stroke = '#2a3a52';
        if (n === 1 && i === 0) stroke = '#3d9cf0';
        if (n === 2 && i <= 1) stroke = '#3d9cf0';
        if (n === 3 && i <= 2) stroke = '#3d9cf0';
        if (n === 3 && i === 3) stroke = '#2ec4a8';
        if (n === 0 && step.state === 'Drop') stroke = (i===1 ? '#e85d5d' : '#2a3a52');
        node.setAttribute('stroke', stroke);
      });
    }
  }

  function mountWalk(root) {
    const key = root.getAttribute('data-walk');
    const model = walks[key];
    if (!model) return;
    const bytesEl = root.querySelector('[data-bytes]');
    renderBytes(bytesEl, model.bytes);
    let idx = 0;
    let timer = null;
    const stopAuto = () => { if (timer) { clearInterval(timer); timer = null; } };
    const show = () => applyStep(root, model, idx);
    root.querySelector('[data-act="next"]').addEventListener('click', () => {
      stopAuto();
      idx = Math.min(idx + 1, model.steps.length - 1);
      show();
    });
    root.querySelector('[data-act="back"]').addEventListener('click', () => {
      stopAuto();
      idx = Math.max(idx - 1, 0);
      show();
    });
    root.querySelector('[data-act="reset"]').addEventListener('click', () => {
      stopAuto();
      idx = 0;
      show();
    });
    root.querySelector('[data-act="auto"]').addEventListener('click', (ev) => {
      if (timer) { stopAuto(); ev.target.textContent = 'Auto-play'; return; }
      ev.target.textContent = 'Stop';
      timer = setInterval(() => {
        if (idx >= model.steps.length - 1) { stopAuto(); ev.target.textContent = 'Auto-play'; return; }
        idx += 1;
        show();
      }, 1600);
    });
    show();
  }

  document.querySelectorAll('[data-walk]').forEach(mountWalk);

  const tabs = document.getElementById('parse-tabs');
  if (tabs) {
    tabs.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-tab]');
      if (!btn) return;
      tabs.querySelectorAll('button').forEach(b => b.classList.toggle('on', b === btn));
      const id = btn.getAttribute('data-tab');
      document.querySelectorAll('.walk-panel').forEach(p => p.classList.toggle('on', p.id === 'panel-' + id));
    });
  }
})();
"""
