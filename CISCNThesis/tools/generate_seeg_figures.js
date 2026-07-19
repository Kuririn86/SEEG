const fs = require('fs');
const path = require('path');

const outDir = path.resolve('/Users/claude_file/Desktop/Program/1.morphcast_test/SEEG/0719/CISCNThesis/figures');
fs.mkdirSync(outDir, { recursive: true });

const C = {
  navy: '#29445f',
  teal: '#167b82',
  coral: '#c4665a',
  ochre: '#bf954e',
  slate: '#6d7d8c',
  ink: '#1d2d3f',
  muted: '#5f7182',
  line: '#aab6c1',
  guide: '#d7dee5',
  bg: '#ffffff',
  panel: '#fbfcfd',
  paleNavy: '#f8fafc',
  paleTeal: '#f4fafa',
  paleCoral: '#fff8f6',
  paleOchre: '#fffaf1'
};

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function T(x, y, s, cls = 'body', anchor = 'start', fill = '') {
  const extra = fill ? ` fill="${fill}"` : '';
  return `<text x="${x}" y="${y}" class="${cls}" text-anchor="${anchor}"${extra}>${esc(s)}</text>`;
}
function R(x, y, w, h, cls = 'panel', r = 9, extra = '') {
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${r}" class="${cls}" ${extra}/>`;
}
function L(x1, y1, x2, y2, stroke = C.line, width = 2, dash = '') {
  return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${width}" ${dash ? `stroke-dasharray="${dash}"` : ''}/>`;
}
function P(d, stroke = C.navy, width = 2.5, dash = '', marker = '') {
  return `<path d="${d}" fill="none" stroke="${stroke}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round" ${dash ? `stroke-dasharray="${dash}"` : ''} ${marker ? `marker-end="url(#${marker})"` : ''}/>`;
}
function Dot(x, y, r, fill, stroke = '#ffffff', sw = 2) {
  return `<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`;
}
function markerDefs() {
  return `<defs>
    <marker id="arrow-navy" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,5 L0,10 z" fill="${C.navy}"/></marker>
    <marker id="arrow-teal" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,5 L0,10 z" fill="${C.teal}"/></marker>
    <marker id="arrow-coral" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,5 L0,10 z" fill="${C.coral}"/></marker>
    <marker id="arrow-ochre" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L10,5 L0,10 z" fill="${C.ochre}"/></marker>
  </defs>`;
}
function styles() {
  return `<style>
    .ink{fill:${C.ink};font-family:Arial,Helvetica,sans-serif}
    .muted{fill:${C.muted};font-family:Arial,Helvetica,sans-serif}
    .title{font-size:27px;font-weight:700;letter-spacing:.1px}
    .subtitle{font-size:16px;letter-spacing:.2px}
    .section{font-size:18px;font-weight:700;letter-spacing:1.2px}
    .head{font-size:21px;font-weight:700;letter-spacing:.1px}
    .body{font-size:18px;letter-spacing:.1px}
    .small{font-size:15px;letter-spacing:.1px}
    .micro{font-size:13px;letter-spacing:.1px}
    .formula{font-size:17px;font-family:Arial,Helvetica,sans-serif;fill:${C.ink}
    }
    .panel{fill:${C.bg};stroke:${C.line};stroke-width:2}
    .panel-navy{fill:${C.paleNavy};stroke:${C.navy};stroke-width:2.2}
    .panel-teal{fill:${C.paleTeal};stroke:${C.teal};stroke-width:2.2}
    .panel-coral{fill:${C.paleCoral};stroke:${C.coral};stroke-width:2.2}
    .panel-ochre{fill:${C.paleOchre};stroke:${C.ochre};stroke-width:2.2}
    .dashbox{fill:#fbfcfd;stroke:#97a7b5;stroke-width:2;stroke-dasharray:7 7}
    .guide{fill:none;stroke:${C.guide};stroke-width:1.5;stroke-dasharray:5 8}
  </style>`;
}
function frame(title, subtitle, body, width = 2000, height = 1000) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-labelledby="title desc">
    <title id="title">${esc(title)}</title><desc id="desc">${esc(subtitle)}</desc>
    ${markerDefs()}${styles()}
    <rect width="${width}" height="${height}" fill="${C.bg}"/>
    ${T(54, 52, title, 'title', 'start', C.ink)}
    ${T(width - 54, 52, subtitle, 'subtitle', 'end', C.muted)}
    ${L(54, 78, width - 54, 78, C.guide, 1.5)}
    ${body}
  </svg>`;
}
function card(x, y, w, h, cls, title, lines, accent = C.navy) {
  let out = R(x, y, w, h, cls);
  out += Dot(x + 24, y + 29, 7, accent);
  out += T(x + 43, y + 35, title, 'head');
  lines.forEach((line, i) => { out += T(x + 20, y + 72 + i * 27, line, i === lines.length - 1 && line.length < 50 ? 'small muted' : 'body muted'); });
  return out;
}
function wave(x, y, w, color = C.navy, amp = 12, cycles = 5) {
  const step = w / (cycles * 2);
  let d = `M ${x} ${y}`;
  for (let i = 0; i < cycles * 2; i++) {
    const x0 = x + i * step;
    const x1 = x0 + step;
    d += ` C ${x0 + step * .25} ${y - amp}, ${x0 + step * .75} ${y + amp}, ${x1} ${y}`;
  }
  return P(d, color, 2.2);
}
function heatmap(x, y, cols, rows, cw, ch, colors) {
  let out = '';
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
    const idx = Math.min(colors.length - 1, Math.floor((c + r * .8) / Math.max(1, cols / colors.length)));
    out += `<rect x="${x + c * cw}" y="${y + r * ch}" width="${cw - 2}" height="${ch - 2}" fill="${colors[idx]}"/>`;
  }
  return out;
}
function save(name, content) {
  fs.writeFileSync(path.join(outDir, `${name}.svg`), content, 'utf8');
}

// Figure 1: data audit and sample construction.
function figData() {
  let b = '';
  b += R(54, 108, 592, 790, 'panel');
  b += R(678, 108, 620, 790, 'panel');
  b += R(1330, 108, 616, 790, 'panel');
  b += T(82, 148, 'A  SIGNAL AUDIT', 'section', 'start', C.navy);
  b += T(706, 148, 'B  QUALITY-AWARE PREPROCESSING', 'section', 'start', C.teal);
  b += T(1358, 148, 'C  PATIENT-LEVEL SAMPLE CONSTRUCTION', 'section', 'start', C.coral);

  b += T(90, 206, 'Raw SEEG record', 'head');
  b += T(90, 232, 'channel ID · sampling rate · C x T waveform', 'small muted');
  b += R(90, 260, 230, 430, 'panel-navy');
  for (let i = 0; i < 9; i++) {
    const yy = 300 + i * 42;
    b += Dot(116, yy, 6, [C.navy, C.navy, C.teal, C.teal, C.coral, C.coral, C.ochre, C.slate, C.navy][i]);
    b += wave(138, yy, 145, [C.navy, C.slate, C.teal, C.teal, C.coral, C.coral, C.ochre, C.slate, C.navy][i], 7, 4);
  }
  b += T(205, 724, 'valid channels', 'small muted', 'middle');
  b += card(366, 266, 238, 140, 'panel-navy', 'Audit fields', ['shape and dtype', 'sampling rate and units', 'missing values'], C.navy);
  b += card(366, 456, 238, 140, 'panel-coral', 'Leakage checks', ['file and waveform hashes', 'near-duplicate clusters', 'metadata probe'], C.coral);
  b += P('M320 475 H350 V336 H356', C.navy, 3, '', 'arrow-navy');
  b += P('M320 475 H350 V526 H356', C.coral, 3, '', 'arrow-coral');
  b += T(90, 806, 'freeze audit protocol before training', 'small muted');

  b += card(720, 222, 252, 146, 'panel-teal', 'Resampling and filters', ['anti-aliasing', 'band-pass + notch', 'causal delay calibration'], C.teal);
  b += card(1006, 222, 252, 146, 'panel-teal', 'Bad-channel QC', ['flatline and saturation', 'line-noise ratio', 'artifact risk score'], C.teal);
  b += R(720, 450, 538, 188, 'panel-navy');
  b += T(748, 488, 'Reference and robust scaling', 'head');
  b += T(748, 526, 'common-average / bipolar reference', 'body muted');
  b += T(748, 557, 'median-MAD normalization with clipping', 'body muted');
  b += T(748, 590, 'bad channels kept as an explicit mask', 'small muted');
  b += P('M846 368 V430', C.teal, 3, '', 'arrow-teal');
  b += P('M1132 368 V430', C.teal, 3, '', 'arrow-teal');
  b += R(720, 704, 538, 124, 'panel-ochre');
  b += T(748, 742, 'Output tensors', 'head');
  b += T(748, 778, 'X: B x C x T    |    channel mask M    |    frame mask', 'body muted');
  b += P('M989 638 V684', C.navy, 3, '', 'arrow-navy');

  b += R(1370, 222, 536, 170, 'panel-coral');
  b += T(1398, 260, 'Patient-level split', 'head');
  b += T(1398, 294, 'patient identity is isolated across train / validation / test', 'small muted');
  const splitY = 330;
  b += R(1398, splitY, 122, 36, 'panel-navy', 5); b += T(1459, splitY + 24, 'train', 'small', 'middle', C.navy);
  b += R(1534, splitY, 122, 36, 'panel-teal', 5); b += T(1595, splitY + 24, 'validation', 'small', 'middle', C.teal);
  b += R(1670, splitY, 122, 36, 'panel-coral', 5); b += T(1731, splitY + 24, 'test', 'small', 'middle', C.coral);
  b += T(1398, 382, 'no random windows across the same continuous record', 'micro muted');
  b += R(1370, 438, 536, 218, 'panel');
  b += T(1398, 476, 'Overlapping windows and labels', 'head');
  b += T(1398, 510, '4 s window · 0.5 s step · 0.125 s frame output', 'small muted');
  b += L(1400, 574, 1858, 574, C.navy, 2);
  for (let i = 0; i < 7; i++) {
    b += R(1400 + i * 58, 546, 150, 54, i === 3 ? 'panel-coral' : 'panel-navy', 4);
    b += T(1408 + i * 58, 578, i === 3 ? 'onset' : `w${i + 1}`, 'micro muted');
  }
  b += T(1398, 622, 'frame labels remain available around state transitions', 'small muted');
  b += R(1370, 704, 536, 124, 'dashbox');
  b += T(1398, 742, 'Cross-subject augmentation', 'head');
  b += T(1398, 776, 'channel dropout · time / frequency masking · baseline drift', 'small muted');
  b += T(1398, 804, 'onset labels are transformed synchronously', 'micro muted');
  b += T(1000, 866, 'The audit report fixes preprocessing, windowing and split rules before model selection.', 'small muted', 'middle');
  return frame('SEEG data audit and patient-level sample construction', 'quality control · leakage prevention · label alignment', b);
}

// Figure 2: QST-DPGNet architecture.
function figModel() {
  let b = '';
  b += R(54, 108, 250, 760, 'panel-navy');
  b += R(340, 108, 492, 760, 'panel');
  b += R(868, 108, 392, 760, 'panel-teal');
  b += R(1298, 108, 648, 760, 'panel');
  b += T(82, 148, 'A  INPUT AND MASKS', 'section', 'start', C.navy);
  b += T(368, 148, 'B  MULTI-SCALE REPRESENTATION', 'section', 'start', C.teal);
  b += T(896, 148, 'C  DYNAMIC PROPAGATION', 'section', 'start', C.teal);
  b += T(1326, 148, 'D  JOINT OUTPUT HEADS', 'section', 'start', C.coral);

  b += T(82, 214, 'Window X', 'head');
  b += T(82, 244, 'B x C x T', 'body muted');
  b += R(82, 276, 184, 182, 'panel-navy');
  for (let i = 0; i < 6; i++) b += wave(100, 304 + i * 25, 145, [C.navy, C.navy, C.teal, C.coral, C.ochre, C.slate][i], 7, 5);
  b += T(174, 492, 'multichannel time series', 'small muted', 'middle');
  b += R(82, 554, 184, 100, 'panel');
  b += T(174, 588, 'channel mask M', 'body muted', 'middle');
  b += T(174, 620, 'frame mask', 'body muted', 'middle');
  b += T(174, 742, 'optional: coordinates +', 'small muted', 'middle');
  b += T(174, 768, 'brain-region soft map', 'small muted', 'middle');
  b += P('M266 365 H326', C.navy, 3, '', 'arrow-navy');

  b += card(374, 206, 424, 178, 'panel-navy', 'Shared temporal encoder', ['depthwise 1D convolutions', 'short / mid / long receptive fields', 'shared weights across channel IDs'], C.navy);
  b += wave(400, 340, 350, C.navy, 10, 8);
  b += wave(400, 360, 350, C.teal, 7, 12);
  b += R(374, 456, 424, 178, 'panel-teal');
  b += T(398, 494, 'Time-frequency branch', 'head');
  b += T(398, 528, 'STFT or differentiable filter bank', 'body muted');
  b += heatmap(400, 548, 8, 3, 42, 18, ['#274d73', '#397b87', '#68a3a0', '#b8c98e', '#bf954e', '#c4665a']);
  b += T(398, 624, 'log-power bands aligned to frame rate', 'small muted');
  b += P('M832 292 H854 V370 H860', C.navy, 3, '', 'arrow-navy');
  b += P('M832 545 H854 V450 H860', C.teal, 3, '', 'arrow-teal');
  b += R(886, 320, 356, 126, 'panel-ochre');
  b += T(914, 357, 'Gated fusion', 'head');
  b += T(914, 390, 'H = G x Htime + (1 - G) x Htf', 'formula');
  b += T(914, 418, 'retains waveform and rhythm evidence', 'small muted');
  b += P('M1064 446 V485', C.ochre, 3, '', 'arrow-ochre');
  b += R(886, 508, 356, 256, 'panel-navy');
  b += T(914, 545, 'Dynamic dual graph', 'head');
  b += T(914, 575, 'A_t = anatomy prior + functional dynamics', 'formula');
  b += T(914, 610, 'baseline change: Delta A_t = A_t - A_baseline', 'small muted');
  b += P('M940 650 L1008 620 L1068 675 L1135 625 L1194 689', C.navy, 2.5);
  b += P('M940 650 L1135 625 M1008 620 L1135 625 M1068 675 L1194 689', C.slate, 2, '6 5');
  b += Dot(940, 650, 8, C.navy); b += Dot(1008, 620, 8, C.teal); b += Dot(1068, 675, 8, C.coral); b += Dot(1135, 625, 8, C.ochre); b += Dot(1194, 689, 8, C.slate);
  b += T(914, 728, 'top-k valid neighbours + node residual', 'small muted');
  b += P('M1242 640 H1280', C.navy, 3, '', 'arrow-navy');

  b += R(1326, 206, 254, 156, 'panel-navy');
  b += T(1350, 244, 'Long-range model', 'head');
  b += T(1350, 276, 'dilated depthwise TCN', 'body muted');
  b += T(1350, 307, 'light gated attention', 'body muted');
  b += wave(1352, 341, 185, C.navy, 9, 5);
  b += P('M1242 702 H1280 V284 H1316', C.navy, 3, '', 'arrow-navy');
  b += R(1326, 408, 254, 142, 'panel-coral');
  b += T(1350, 446, 'Fragment state head', 'head');
  b += T(1350, 478, 'p_clip + calibrated probability', 'body muted');
  b += T(1350, 510, 'quality-weighted pooling', 'small muted');
  b += R(1326, 594, 254, 142, 'panel-navy');
  b += T(1350, 632, 'Frame state + onset', 'head');
  b += T(1350, 664, 'p_state,t and p_onset,t', 'body muted');
  b += T(1350, 696, 'transition consistency', 'small muted');
  b += R(1616, 206, 294, 156, 'panel-teal');
  b += T(1640, 244, 'Channel recruitment head', 'head');
  b += T(1640, 276, 'r_c,t retains channel x time', 'body muted');
  b += T(1640, 307, 'early recruitment + propagation', 'small muted');
  b += heatmap(1640, 326, 8, 2, 28, 16, ['#274d73', '#397b87', '#68a3a0', '#b8c98e', '#bf954e', '#c4665a']);
  b += P('M1448 362 V394', C.navy, 3, '', 'arrow-navy');
  b += P('M1450 362 V576', C.navy, 3, '', 'arrow-navy');
  b += P('M1580 284 H1606', C.teal, 3, '', 'arrow-teal');
  b += R(1616, 408, 294, 142, 'panel-ochre');
  b += T(1640, 446, 'State-transition constraint', 'head');
  b += T(1640, 478, 'p_onset rise -> persistent p_state', 'body muted');
  b += T(1640, 510, 'suppresses isolated spikes', 'small muted');
  b += P('M1580 665 H1606 V480 H1608', C.ochre, 3, '', 'arrow-ochre');
  b += R(1616, 594, 294, 142, 'panel-navy');
  b += T(1640, 632, 'Submission outputs', 'head');
  b += T(1640, 664, 'label + p + onset time', 'body muted');
  b += T(1640, 696, 'Top-10 official channel IDs', 'small muted');
  b += P('M1450 550 V574 H1606 V664', C.navy, 3, '', 'arrow-navy');
  b += T(1000, 840, 'One shared representation jointly answers when the state changes, which channels are recruited first and how activity propagates.', 'small muted', 'middle');
  return frame('QST-DPGNet: state transition and dynamic propagation network', 'shared representation · multi-task heads · interpretable outputs', b);
}

// Figure 3: onset localization.
function figOnset() {
  let b = '';
  b += R(54, 108, 470, 790, 'panel');
  b += R(554, 108, 700, 790, 'panel-navy');
  b += R(1284, 108, 662, 790, 'panel');
  b += T(82, 148, 'A  WINDOW FUSION', 'section', 'start', C.navy);
  b += T(582, 148, 'B  JOINT STATE MACHINE', 'section', 'start', C.navy);
  b += T(1312, 148, 'C  ROBUST ONSET DECISION', 'section', 'start', C.ochre);

  b += T(88, 208, 'Overlapping windows', 'head');
  b += T(88, 238, 'Hann-weighted frame fusion', 'small muted');
  b += L(96, 318, 468, 318, C.guide, 1.5);
  for (let i = 0; i < 5; i++) {
    b += R(96 + i * 42, 274, 182, 70, i === 2 ? 'panel-coral' : 'panel-navy', 6);
    b += wave(110 + i * 42, 317, 142, i === 2 ? C.coral : C.navy, 7, 5);
    b += T(108 + i * 42, 296, `w${i + 1}`, 'micro muted');
  }
  b += P('M278 390 H466', C.navy, 3, '', 'arrow-navy');
  b += R(92, 438, 376, 330, 'panel-teal');
  b += T(118, 477, 'Fused sequences', 'head');
  b += T(118, 508, 'state p_t', 'body muted');
  b += P('M118 548 C166 550 178 548 212 548 S260 540 286 505 S330 470 364 472 S406 474 438 470', C.coral, 3);
  b += L(118, 548, 438, 548, C.line, 1.2);
  b += T(118, 596, 'boundary b_t', 'body muted');
  b += P('M118 632 C190 632 228 630 250 628 S270 586 294 580 S322 634 438 632', C.ochre, 3);
  b += T(118, 680, 'recruitment max_c r_c,t', 'body muted');
  b += P('M118 710 C190 710 234 708 262 700 S290 662 320 668 S350 706 438 704', C.teal, 3);
  b += T(88, 782, 'filter delay and frame-center offsets are calibrated before search', 'small muted');

  b += T(588, 208, 'State probabilities', 'head');
  b += T(588, 236, 'same time axis, different evidence roles', 'small muted');
  b += L(620, 638, 1204, 638, C.navy, 2);
  for (let i = 0; i < 7; i++) b += L(620 + i * 97, 630, 620 + i * 97, 646, C.line, 1.5);
  b += T(620, 672, '0 s', 'micro muted'); b += T(1204, 672, 'window end', 'micro muted', 'end');
  b += T(620, 290, 'state p_t', 'body ink');
  b += P('M620 332 C730 332 760 330 824 324 S884 274 928 248 S988 230 1040 226 S1120 228 1204 216', C.coral, 4);
  b += T(620, 408, 'boundary b_t', 'body ink');
  b += P('M620 450 C820 450 872 448 918 444 S930 388 948 380 S966 448 1204 448', C.ochre, 3);
  b += T(620, 526, 'recruitment max_c r_c,t', 'body ink');
  b += P('M620 566 C820 566 860 564 904 558 S924 518 946 520 S984 554 1048 554 S1120 552 1204 552', C.teal, 3);
  b += L(946, 236, 946, 638, C.ochre, 2, '7 7');
  b += T(946, 214, 'candidate', 'micro muted', 'middle');
  b += R(704, 706, 460, 116, 'panel-ochre');
  b += T(728, 744, 'Hysteresis', 'head');
  b += T(728, 778, 'trigger at tau_h  |  maintain at tau_l  |  tau_h > tau_l', 'body muted');
  b += T(728, 806, 'continuous positive duration D_min suppresses isolated spikes', 'small muted');

  b += T(1318, 208, 'Joint boundary score', 'head');
  b += T(1318, 242, 'earliest candidate satisfying future persistence', 'small muted');
  b += R(1318, 282, 586, 150, 'panel-ochre');
  b += T(1346, 324, 'B_k = rho1 b_k + rho2 Delta logit(p_k) + rho3 max_c r_c,k - rho4 Q_artifact', 'formula');
  b += T(1346, 364, 'state rise + boundary peak + early recruitment - artifact risk', 'body muted');
  b += T(1346, 396, 'the first valid peak is selected, not the first p_t > 0.5', 'small muted');
  b += R(1318, 474, 280, 198, 'panel-navy');
  b += T(1346, 512, 'Left-censored', 'head');
  b += T(1346, 546, 'high probability at first frame', 'body muted');
  b += T(1346, 578, 'onset = 0; internal flag retained', 'small muted');
  b += P('M1350 624 H1550', C.navy, 2); b += L(1350, 612, 1350, 636, C.navy, 2); b += T(1350, 654, '0', 'micro muted');
  b += R(1626, 474, 278, 198, 'panel-coral');
  b += T(1654, 512, 'Artifact rejection', 'head');
  b += T(1654, 546, 'isolated burst or flatline', 'body muted');
  b += T(1654, 578, 'cannot trigger without persistence', 'small muted');
  b += P('M1652 624 C1690 600 1710 645 1748 620 S1812 606 1878 624', C.coral, 2.5);
  b += T(1318, 738, 'Calibrated onset time', 'head');
  b += T(1318, 776, 't_onset = max(0, k* / f_frame - d_system)', 'formula');
  b += T(1318, 808, 'report precision separately from actual temporal resolution', 'small muted');
  b += T(1000, 868, 'State persistence, boundary evidence and change-point support are combined; no single threshold defines onset.', 'small muted', 'middle');
  return frame('Onset localization from state persistence and boundary evidence', 'window fusion · hysteresis · change-point correction', b, 2000, 1000);
}

// Figure 4: channel ranking and optional spatial mapping.
function figChannels() {
  let b = '';
  b += R(54, 108, 552, 790, 'panel');
  b += R(636, 108, 658, 790, 'panel-teal');
  b += R(1324, 108, 622, 790, 'panel');
  b += T(82, 148, 'A  ONSET-AWARE EVIDENCE WINDOW', 'section', 'start', C.teal);
  b += T(664, 148, 'B  FUSED CHANNEL SCORE', 'section', 'start', C.teal);
  b += T(1352, 148, 'C  RANKING AND SPATIAL CONDITION', 'section', 'start', C.coral);

  b += T(88, 210, 'Channel x time recruitment', 'head');
  b += T(88, 240, 'early window limits late propagation bias', 'small muted');
  b += R(88, 278, 470, 304, 'panel-navy');
  b += L(140, 306, 140, 548, C.line, 1.5);
  for (let i = 0; i < 8; i++) {
    const yy = 320 + i * 29;
    b += T(102, yy + 5, `ch${i + 1}`, 'micro muted');
    b += wave(154, yy, 328, [C.navy, C.teal, C.coral, C.ochre, C.slate, C.navy, C.teal, C.slate][i], i < 3 ? 5 + i * 2 : 3, 6);
    if (i < 5) b += R(228 + i * 14, yy - 9, 32 + i * 7, 18, 'panel-coral', 3);
  }
  b += L(156, 562, 514, 562, C.navy, 2);
  b += T(156, 588, 'onset', 'micro muted'); b += T(514, 588, 'late propagation', 'micro muted', 'end');
  b += T(88, 650, 'internal layers', 'head');
  b += T(88, 684, 'onset candidate  |  early propagation  |  late propagation', 'body muted');
  b += Dot(105, 730, 7, C.coral); b += T(122, 735, 'first sustained recruitment', 'small muted');
  b += Dot(105, 762, 7, C.teal); b += T(122, 767, 'early network propagation', 'small muted');
  b += Dot(105, 794, 7, C.slate); b += T(122, 799, 'late broad synchronization', 'small muted');

  b += T(670, 210, 'S_c = weighted evidence - artifact risk', 'head');
  const comps = [
    ['E_early', 'early recruitment and baseline deviation', C.coral, 0.92],
    ['L_latency', 'shorter recruitment latency', C.ochre, 0.78],
    ['D_evolution', 'persistent rhythm and frequency migration', C.teal, 0.70],
    ['P_outflow', 'directed graph outflow above baseline', C.navy, 0.58],
    ['R_repeat', 'cross-seizure ranking consistency', C.slate, 0.45],
    ['M_model', 'recruitment head confidence', '#8aa8b0', 0.36],
    ['Q_artifact', 'bad-channel and artifact penalty', C.coral, 0.24]
  ];
  comps.forEach((row, i) => {
    const yy = 266 + i * 62;
    b += T(672, yy + 7, row[0], 'body ink');
    b += T(672, yy + 31, row[1], 'small muted');
    b += R(1004, yy - 7, 228, 18, 'panel', 5);
    b += R(1004, yy - 7, 228 * row[3], 18, 'panel-teal', 5, `fill="${row[2]}" stroke="none"`);
  });
  b += R(670, 722, 560, 112, 'panel-ochre');
  b += T(696, 760, 'Non-negative weights sum to 1', 'head');
  b += T(696, 792, 'sample-wise percentile ranks prevent energy alone from dominating', 'small muted');
  b += T(992, 816, 'k = min(10, C_valid)', 'formula', 'middle');

  b += T(1360, 210, 'Top-10 output', 'head');
  b += T(1360, 240, 'official channel IDs, ordered by S_c', 'small muted');
  const rankColors = [C.coral, C.coral, C.ochre, C.teal, C.teal, C.navy, C.navy, C.slate, C.slate, C.slate];
  for (let i = 0; i < 10; i++) {
    const yy = 282 + i * 30;
    b += T(1360, yy + 5, `${i + 1}`, 'small muted');
    b += T(1402, yy + 5, ['A3-A4', 'B2-B3', 'A2-A3', 'C5-C6', 'D1-D2', 'B4-B5', 'C2-C3', 'D4-D5', 'A5-A6', 'C7-C8'][i], 'body ink');
    b += R(1502, yy - 9, 284 - i * 13, 16, i < 2 ? 'panel-coral' : i < 5 ? 'panel-teal' : 'panel-navy', 4);
    b += Dot(1810, yy - 1, 5, rankColors[i]);
  }
  b += R(1360, 604, 530, 132, 'dashbox');
  b += T(1388, 642, 'Conditional spatial mapping', 'head');
  b += T(1388, 674, 'coordinates + MRI/CT + quality control', 'body muted');
  b += T(1388, 706, 'contact -> region aggregation and 3D path', 'small muted');
  b += P('M1610 570 V590', C.navy, 2.5, '7 7', 'arrow-navy');
  b += R(1698, 774, 190, 88, 'panel-navy');
  b += T(1793, 806, 'contact / ROI', 'small muted', 'middle');
  b += P('M1740 832 L1780 810 L1830 836 L1790 850 Z', C.navy, 1.8);
  b += Dot(1740, 832, 6, C.coral); b += Dot(1780, 810, 6, C.teal); b += Dot(1830, 836, 6, C.ochre);
  b += T(1360, 822, 'Not SOZ / EZ / surgical boundary', 'head', 'start', C.coral);
  b += T(1360, 852, 'only important channels within current implant coverage', 'small muted');
  b += T(966, 868, 'Fast ranking uses one forward pass; attribution validates necessity and sufficiency offline.', 'small muted', 'middle');
  return frame('Onset-aware Top-10 channel ranking and conditional spatial mapping', 'early recruitment · propagation order · coordinate-aware reporting', b);
}

// Figure 5: inference and deployment.
function figDeployment() {
  let b = '';
  b += R(54, 108, 1892, 310, 'panel');
  b += R(54, 456, 912, 442, 'panel-navy');
  b += R(1000, 456, 946, 442, 'panel-teal');
  b += T(82, 148, 'A  FORMAL FAST INFERENCE PIPELINE', 'section', 'start', C.navy);
  b += T(82, 496, 'B  STREAMING CACHE AND HARDWARE LANES', 'section', 'start', C.navy);
  b += T(1028, 496, 'C  OFFLINE EXPLANATION AND QA', 'section', 'start', C.teal);

  const steps = [
    ['1', 'Read + audit', 'shape · IDs · fs'],
    ['2', 'Preprocess', 'filter · mask · scale'],
    ['3', 'Window + cache', 'overlap reuse'],
    ['4', 'One forward', 'state · onset · r_c,t'],
    ['5', 'Post-process', 'calibration · hysteresis'],
    ['6', 'Format', 'JSON / official fields']
  ];
  steps.forEach((s, i) => {
    const x = 88 + i * 300;
    const cls = i === 3 ? 'panel-coral' : i === 4 ? 'panel-ochre' : 'panel-navy';
    b += R(x, 208, 232, 136, cls);
    b += Dot(x + 26, 238, 12, i === 3 ? C.coral : i === 4 ? C.ochre : C.navy);
    b += T(x + 26, 244, s[0], 'small', 'middle', '#ffffff');
    b += T(x + 52, 244, s[1], 'head');
    b += T(x + 20, 284, s[2], 'body muted');
    b += T(x + 20, 316, i === 3 ? 'single forward pass' : i === 4 ? 'P50 / P95 tracked' : 'deterministic stage', 'small muted');
    if (i < steps.length - 1) b += P(`M${x + 232} 276 H${x + 286}`, i === 3 ? C.coral : C.navy, 3, '', i === 3 ? 'arrow-coral' : 'arrow-navy');
  });
  b += T(1000, 382, 'Only positive samples emit onset; all fields are checked by the submission validator.', 'small muted', 'middle');

  b += T(84, 560, 'Sliding-window ring buffer', 'head');
  b += T(84, 590, '4 s context, 0.5 s step', 'small muted');
  b += R(84, 624, 386, 132, 'panel');
  for (let i = 0; i < 5; i++) b += R(108 + i * 58, 674, 120, 32, i === 4 ? 'panel-teal' : 'panel-navy', 4);
  b += T(108, 698, 'cached', 'micro muted'); b += T(340, 698, 'new 0.5 s', 'micro muted');
  b += P('M472 690 H520', C.teal, 3, '', 'arrow-teal');
  b += R(532, 624, 370, 132, 'panel-teal');
  b += T(560, 660, 'Reusable features', 'head');
  b += T(560, 692, 'filtered signal · STFT frames', 'body muted');
  b += T(560, 724, 'local encoder state · graph edges', 'body muted');
  b += T(84, 810, 'CPU: ONNX Runtime / OpenVINO / INT8', 'body muted');
  b += T(84, 842, 'GPU: TensorRT / FP16 or BF16 / dynamic batch', 'body muted');
  b += T(1028, 560, 'Fast chain', 'head');
  b += R(1000, 600, 878, 92, 'panel');
  b += T(1028, 638, 'state + boundary + recruitment + graph outflow', 'body muted');
  b += T(1028, 670, 'no reverse-mode explanation in the formal path', 'small muted');
  b += T(1028, 746, 'Deep explanation chain', 'head');
  b += R(1000, 784, 878, 82, 'dashbox');
  b += T(1028, 818, 'Integrated Gradients · SmoothGrad · occlusion · perturbation stability', 'body muted');
  b += T(1028, 848, 'offline validation and difficult-case review only', 'small muted');
  b += P('M1440 692 V772', C.teal, 3, '7 7', 'arrow-teal');
  b += T(1472, 736, 'QA branch', 'micro muted');
  b += R(1540, 562, 320, 112, 'panel-ochre');
  b += T(1568, 600, 'Latency budget', 'head');
  b += T(1568, 634, 'I/O · preprocess · forward · postprocess', 'small muted');
  b += T(1568, 660, 'report cold-start and steady-state P50/P95', 'small muted');
  b += T(1470, 886, 'Neural-network time and end-to-end system time are reported separately.', 'small muted', 'middle');
  return frame('Streaming inference, cache reuse and explanation separation', 'formal fast path · CPU/GPU deployment · offline validation', b);
}

// Figure 6: lightweight optimization.
function figLightweight() {
  let b = '';
  b += R(54, 108, 610, 790, 'panel');
  b += R(704, 108, 592, 790, 'panel-teal');
  b += R(1336, 108, 610, 790, 'panel');
  b += T(82, 148, 'A  TEACHER -> STUDENT DISTILLATION', 'section', 'start', C.navy);
  b += T(732, 148, 'B  HARDWARE-AWARE COMPRESSION', 'section', 'start', C.teal);
  b += T(1364, 148, 'C  DEPLOYMENT GATES', 'section', 'start', C.coral);

  b += R(94, 224, 232, 280, 'panel-navy');
  b += T(210, 264, 'Teacher', 'head', 'middle');
  b += T(210, 298, 'full QST-DPGNet', 'body muted', 'middle');
  b += T(210, 332, 'wide graph + long context', 'small muted', 'middle');
  b += wave(120, 390, 180, C.navy, 10, 5);
  b += Dot(132, 438, 7, C.navy); b += Dot(180, 416, 7, C.teal); b += Dot(230, 444, 7, C.coral); b += Dot(274, 420, 7, C.ochre);
  b += P('M132 438 L180 416 L230 444 L274 420 M132 438 L230 444', C.navy, 2);
  b += T(210, 492, 'soft logits + frame curves', 'micro muted', 'middle');
  b += R(392, 224, 232, 280, 'panel-teal');
  b += T(508, 264, 'Student', 'head', 'middle');
  b += T(508, 298, 'compact deployment model', 'body muted', 'middle');
  b += T(508, 332, 'fewer graph layers and blocks', 'small muted', 'middle');
  b += wave(418, 390, 180, C.teal, 8, 5);
  b += Dot(438, 438, 7, C.teal); b += Dot(492, 416, 7, C.navy); b += Dot(560, 438, 7, C.coral);
  b += T(508, 492, 'rank-preserving outputs', 'micro muted', 'middle');
  b += P('M326 350 H380', C.navy, 3, '', 'arrow-navy');
  b += T(354, 332, 'distill', 'micro muted', 'middle');
  b += R(94, 560, 530, 230, 'panel-ochre');
  b += T(122, 600, 'Knowledge transfer targets', 'head');
  b += T(122, 638, 'L_KD = alpha L_logit + beta L_frame', 'formula');
  b += T(122, 670, '+ chi L_feature + delta L_rank', 'formula');
  b += T(122, 714, 'fragment probability · frame state · intermediate features', 'small muted');
  b += T(122, 746, 'Top-10 ranking stability', 'small muted');

  b += R(746, 224, 506, 136, 'panel-navy');
  b += T(774, 262, 'Structured pruning', 'head');
  b += T(774, 296, 'conv channels · attention heads · graph width', 'body muted');
  b += T(774, 328, 'keep only hardware-effective sparsity', 'small muted');
  b += R(746, 402, 506, 136, 'panel-ochre');
  b += T(774, 440, 'Quantization', 'head');
  b += T(774, 474, 'INT8 conv / linear layers on CPU', 'body muted');
  b += T(774, 506, 'keep calibration and onset postprocess in FP32', 'small muted');
  b += R(746, 580, 506, 136, 'panel-teal');
  b += T(774, 618, 'Cache reuse', 'head');
  b += T(774, 652, 'share filter, STFT and local features across windows', 'body muted');
  b += T(774, 684, 'new computation only for the 0.5 s increment', 'small muted');
  b += P('M998 360 V392', C.navy, 3, '', 'arrow-navy');
  b += P('M998 538 V570', C.ochre, 3, '', 'arrow-ochre');
  b += T(998, 788, 'precision and latency are measured after export', 'small muted', 'middle');

  b += R(1380, 224, 520, 110, 'panel-navy');
  b += T(1408, 262, 'TensorRT', 'head');
  b += T(1408, 296, 'GPU · FP16 · operator fusion', 'body muted');
  b += R(1380, 372, 520, 110, 'panel-teal');
  b += T(1408, 410, 'ONNX Runtime / OpenVINO', 'head');
  b += T(1408, 444, 'CPU · INT8 · thread binding', 'body muted');
  b += R(1380, 520, 520, 110, 'panel-ochre');
  b += T(1408, 558, 'TorchScript', 'head');
  b += T(1408, 592, 'research reproduction · fixed graph', 'body muted');
  b += T(1380, 694, 'Acceptance gates', 'head');
  const gates = [
    ['AUC / F1', 'classification drop <= 0.5-1.0 pp', C.coral],
    ['onset MAE', 'increase <= 10%', C.ochre],
    ['Top-10 Jaccard', 'ranking stability above threshold', C.teal],
    ['P50 / P95', 'end-to-end target hardware latency', C.navy]
  ];
  gates.forEach((g, i) => {
    const yy = 742 + i * 34;
    b += Dot(1392, yy - 5, 6, g[2]);
    b += T(1412, yy, g[0], 'small ink');
    b += T(1580, yy, g[1], 'small muted');
  });
  b += T(1000, 866, 'Validation gates cover probability, onset and ranking.', 'small muted', 'middle');
  return frame('Model lightweight optimization and deployment acceptance gates', 'distillation · quantization · cache reuse · deployment gates', b);
}

save('seeg_data_preprocessing_nature', figData());
save('seeg_qst_dpgnet_architecture_nature', figModel());
save('seeg_onset_localization_nature', figOnset());
save('seeg_top10_channel_explanation_nature', figChannels());
save('seeg_inference_deployment_nature', figDeployment());
save('seeg_lightweight_optimization_nature', figLightweight());
console.log('Generated six SEEG figure SVGs in', outDir);
