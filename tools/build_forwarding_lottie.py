#!/usr/bin/env python3
"""The call-forwarding walkthrough as a Lottie: the build's `ForwardingWalkthrough` (copy flow,
iOS 27+) drawn into the voicemail Lottie's phone, so the two setup animations match: same canvas
(512 × 720), same phone and bezel (copied from voicemail.json), cut at the same point.

Everything follows `Screens/ForwardingWalkthrough.swift`: its 11.5 s loop, its beats, and its
layout in the same points, scaled so its 230-pt-wide screen fills the voicemail phone's screen.
Text is turned into outlines (tools/lottie_glyphs.swift: DM Sans for Equal, SF for iOS), so the
file needs no fonts.

Colours are slots for theming (see tools/theme_lotties.py):
  equal_*     Equal's screen                    → Equal alias tokens
  iosPhone_*  the Phone keypad                  → iOS light / dark
  ios_statusBar                                 → iOS light / dark
The carrier's reply (a dark system sheet), the finger marks and the green done tick stay as drawn.

`build()` returns (animation, slots); theme_lotties.py packages it.
"""
import json
import math
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICEMAIL = os.path.join(ROOT, 'EqualOrbOnboarding', 'Resources', 'Lottie', 'voicemail.json')

FPS = 60
PERIOD = 11.5
OP = round(PERIOD * FPS)          # 690 frames

# The voicemail phone's screen, measured from its bezel: left edge, top edge, width (canvas px).
SCREEN_X, SCREEN_Y, SCREEN_W = 57.0, 83.0, 399.0
ISLAND_Y = 112.5                   # centre of the island
W = 230.0                          # the build's screen width, in points
S = SCREEN_W / W                   # points → canvas px
RADIUS = 52 / S                    # the screen's corner radius
H = (720 - SCREEN_Y) / S + RADIUS + 8   # screen height: its bottom corners fall past the cut


def M(x, y):
    return [round(SCREEN_X + x * S, 3), round(SCREEN_Y + y * S, 3)]


def hexc(h):
    h = h.lstrip('#')
    return [round(int(h[i:i + 2], 16) / 255, 4) for i in (0, 2, 4)]


# Light values (Equal tokens for Equal, iOS light for iOS). Themes override these.
SLOTS = {
    'equal_screenBg': '#F7F7F7',
    'equal_surface': '#FFFFFF',
    'equal_textPrimary': '#111111',
    'equal_textSecondary': '#555555',
    'equal_strokeSubtle': '#000000',
    'equal_action': '#00B140',
    'equal_onAction': '#FFFFFF',
    'equal_actionSoft': '#E8FFED',
    'equal_onActionSoft': '#006223',
    'iosPhone_bg': '#FFFFFF',
    'iosPhone_key': '#E5E5EA',
    'iosPhone_label': '#000000',
    'iosPhone_call': '#34C759',
    'ios_statusBar': '#000000',
}

# ---------------------------------------------------------------- timeline (as in the Swift)

APP, DIAL, CARRIER, BACK, DONE = (0.0, 2.3), (2.3, 4.6), (4.6, 7.4), (7.4, 9.2), (9.2, 11.5)
TAP_ACTION, TAP_PASTE, TAP_DIAL, TAP_CONFIRM = 1.25, 2.85, 3.75, 8.5


def ramp(t, a, b):
    x = min(max((t - a) / (b - a), 0), 1)
    return x * x * (3 - 2 * x)


def window(t, a, b, fade=0.3):
    return ramp(t, a - fade, a) * (1 - ramp(t, b, b + fade))


def press(t, at, depth):
    return 1 - depth * ramp(t, at - 0.12, at) * (1 - ramp(t, at, at + 0.18))


# ---------------------------------------------------------------- keyframes

def anim(fn, dims=1, tol=0.02):
    """Samples fn(t) every frame; keeps only the frames a linear ramp can't reproduce."""
    vals = []
    for f in range(OP + 1):
        v = fn(f / FPS)
        vals.append(list(v) if isinstance(v, (list, tuple)) else [v])
    if all(max(abs(a - b) for a, b in zip(v, vals[0])) < 1e-9 for v in vals):
        k = vals[0]
        return {'a': 0, 'k': k if dims > 1 else k[0]}
    keep = [0]
    for f in range(1, OP):
        a, b = keep[-1], f + 1
        # Drop f if the straight line from the last kept frame to f+1 stays within tolerance.
        ok = True
        for g in range(a + 1, b):
            u = (g - a) / (b - a)
            if any(abs(vals[a][d] + (vals[b][d] - vals[a][d]) * u - vals[g][d]) > tol for d in range(len(vals[0]))):
                ok = False
                break
        if not ok:
            keep.append(f)
    keep.append(OP)
    kfs = []
    for f in keep:
        kfs.append({'t': f, 's': [round(x, 4) for x in vals[f]],
                    'o': {'x': 0, 'y': 0}, 'i': {'x': 1, 'y': 1}})
    return {'a': 1, 'k': kfs}


def static(v):
    return {'a': 0, 'k': v}


# ---------------------------------------------------------------- shapes

def color(c):
    return hexc(SLOTS[c]) + [1] if c in SLOTS else hexc(c) + [1]


def fill(c, opacity=100):
    p = {'ty': 'fl', 'c': {'a': 0, 'k': color(c)}, 'o': opacity if isinstance(opacity, dict) else static(opacity), 'r': 1}
    if c in SLOTS:
        p['c']['sid'] = c
    return p


def stroke(c, width, opacity=100, cap=2, join=2):
    p = {'ty': 'st', 'c': {'a': 0, 'k': color(c)}, 'o': opacity if isinstance(opacity, dict) else static(opacity),
         'w': static(width), 'lc': cap, 'lj': join, 'ml': 4}
    if c in SLOTS:
        p['c']['sid'] = c
    return p


def rect(cx, cy, w, h, r):
    return {'ty': 'rc', 'd': 1, 'p': static([cx, cy]), 's': static([w, h]), 'r': static(r)}


def ellipse(cx, cy, d):
    return {'ty': 'el', 'd': 1, 'p': static([cx, cy]), 's': static([d, d])}


def bez(v, i, o, closed=True):
    return {'ty': 'sh', 'ks': static({'c': closed, 'v': v, 'i': i, 'o': o})}


def poly(points, closed=False):
    z = [[0, 0]] * len(points)
    return bez(points, z, z, closed)


def arc(cx, cy, r, a0, a1):
    """A circular arc as one open bezier (angles in degrees, 0 = up, clockwise)."""
    n = max(1, math.ceil(abs(a1 - a0) / 90))
    step = (a1 - a0) / n
    k = 4 / 3 * math.tan(math.radians(step) / 4) * r
    pts, ins, outs = [], [], []
    for j in range(n + 1):
        a = math.radians(a0 + step * j)
        px, py = cx + r * math.sin(a), cy - r * math.cos(a)
        tx, ty = math.cos(a), math.sin(a)          # tangent, clockwise
        pts.append([px, py])
        ins.append([-tx * k, -ty * k] if j > 0 else [0, 0])
        outs.append([tx * k, ty * k] if j < n else [0, 0])
    return bez(pts, ins, outs, False)


def group(items, name='g', x=0, y=0, scale=100, opacity=100):
    tr = {'ty': 'tr', 'p': static([x, y]), 'a': static([0, 0]), 's': static([scale, scale]),
          'r': static(0), 'o': static(opacity), 'sk': static(0), 'sa': static(0)}
    return {'ty': 'gr', 'nm': name, 'it': items + [tr]}


def svg_path(d, scale=1.0, dx=0.0, dy=0.0):
    """M/L/H/V/C/S/Z (absolute and relative) → list of Lottie beziers."""
    toks = re.findall(r'[MmLlHhVvCcSsZz]|-?\d*\.?\d+(?:e-?\d+)?', d)
    out, v, ins, outs = [], [], [], []
    x = y = sx = sy = 0.0
    last_c2 = None
    i, cmd = 0, None

    def num():
        nonlocal i
        i += 1
        return float(toks[i - 1])

    def P(px, py):
        return [px * scale + dx, py * scale + dy]

    def close():
        nonlocal v, ins, outs
        if len(v) > 1:
            if abs(v[0][0] - v[-1][0]) < 1e-6 and abs(v[0][1] - v[-1][1]) < 1e-6:
                ins[0] = ins.pop(); v.pop(); outs.pop()
            out.append(bez(v, ins, outs, True))
        v, ins, outs = [], [], []

    while i < len(toks):
        if re.match(r'[A-Za-z]', toks[i]):
            cmd = toks[i]; i += 1
            if cmd in 'Zz':
                close(); x, y = sx, sy; last_c2 = None
                continue
        rel = cmd.islower()
        c = cmd.upper()
        ox, oy = (x, y) if rel else (0, 0)
        if c == 'M':
            close()
            x, y = num() + ox, num() + oy; sx, sy = x, y
            v.append(P(x, y)); ins.append([0, 0]); outs.append([0, 0])
            cmd = 'l' if rel else 'L'; last_c2 = None
        elif c in 'LHV':
            if c == 'L':
                x, y = num() + ox, num() + oy
            elif c == 'H':
                x = num() + (x if rel else 0)
            else:
                y = num() + (y if rel else 0)
            v.append(P(x, y)); ins.append([0, 0]); outs.append([0, 0]); last_c2 = None
        elif c in 'CS':
            if c == 'C':
                x1, y1 = num() + ox, num() + oy
            else:
                x1, y1 = (2 * x - last_c2[0], 2 * y - last_c2[1]) if last_c2 else (x, y)
            x2, y2, ex, ey = num() + ox, num() + oy, num() + ox, num() + oy
            outs[-1] = [(x1 - x) * scale, (y1 - y) * scale]
            v.append(P(ex, ey)); ins.append([(x2 - ex) * scale, (y2 - ey) * scale]); outs.append([0, 0])
            x, y = ex, ey; last_c2 = (x2, y2)
    close()
    return out


# SF Symbols' phone.fill isn't reachable from CoreText; Material's call icon (Apache 2.0) has the
# same handset.
HANDSET = ('M20.01 15.38c-1.23 0-2.42-.2-3.53-.56-.35-.12-.74-.03-1.01.24l-1.57 1.97c-2.83-1.35-5.48-3.9-6.89-6.83'
           'l1.95-1.66c.27-.28.35-.67.24-1.02-.37-1.11-.56-2.3-.56-3.53 0-.54-.45-.99-.99-.99H4.19C3.65 3 3 3.24 3 3.99'
           ' 3 13.28 10.73 21 20.01 21c.71 0 .99-.63.99-1.18v-3.45c0-.54-.45-.99-.99-.99z')

# ---------------------------------------------------------------- text

CODE = '**67*04048938092#'
TEXTS = {
    'title': ('Call forwarding', 'dm', 17, 700, -0.3, False),
    'subtitle': ('Copy the code, dial it in Phone', 'dm', 12.5, 400, None, False),
    'code': (CODE, 'dm', 12.5, 500, None, True),
    'copy': ('Copy', 'dm', 12.5, 600, None, False),
    'copied': ('Copied', 'dm', 12.5, 600, None, False),
    'activated': ('I have activated call forwarding', 'dm', 11, 500, None, False),
    'continue': ('Continue', 'dm', 14, 600, None, False),
    'time': ('9:41', 'sf', 12, 600, None, False),
    'dialled': (CODE, 'sf', 17, 400, None, False),
    'paste': ('Paste', 'sf', 13, 500, None, False),
    'calling': ('Calling…', 'sf', 12.5, 400, None, False),
    'succeeded': ('Setting Registration Succeeded', 'sf', 12.5, 600, None, False),
    'dismiss': ('Dismiss', 'sf', 13, 600, None, False),
}
for k in '1234567890*#':
    TEXTS[f'key{k}'] = (k, 'sf', 16, 400, None, False)
for kind in ('Voice', 'Data', 'SMS'):
    TEXTS[f'kind{kind}'] = (f'{kind} Call Forwarding', 'sf', 12, 400, None, False)

G = {}


def load_glyphs():
    reqs = [{'id': k, 'text': t, 'font': f, 'size': s, 'weight': w, 'tracking': tr, 'tnum': tn}
            for k, (t, f, s, w, tr, tn) in TEXTS.items()]
    for r in reqs:
        if r['tracking'] is None:
            del r['tracking']
    out = subprocess.run(['swift', 'tools/lottie_glyphs.swift'], cwd=ROOT, input=json.dumps(reqs),
                         capture_output=True, text=True, check=True).stdout
    G.update(json.loads(out))


def lh(key):
    g = G[key]
    return g['ascent'] + g['descent'] + g['leading']


def text(key, c, x, top=None, center_y=None, align='left', scale=1.0, opacity=100):
    """Text as outlines. x is the left edge (or centre, align='center'); the line box sits at
    `top`, or is centred on `center_y`, as SwiftUI lays out a single line."""
    g = G[key]
    w = g['width'] * scale
    left = x - w / 2 if align == 'center' else x
    box = lh(key) * scale
    t = top if top is not None else center_y - box / 2
    base = t + g['ascent'] * scale
    paths = [bez(cn['v'], cn['i'], cn['o'], True) for cn in g['contours']]
    return group(paths + [fill(c, opacity)], key, left, base, scale * 100)


def width(key):
    return G[key]['width']


# ---------------------------------------------------------------- layers

LAYERS = []


def layer(name, shapes, cx=0.0, cy=0.0, opacity=None, scale=None, dy=None):
    """A shape layer drawn in screen points around (cx, cy), placed on the canvas. Layers are
    added bottom first; build() flips the list into Lottie's top-first order."""
    ks = {
        'a': static([0, 0]),
        'p': anim(lambda t: M(cx, cy + dy(t)), 2) if dy else static(M(cx, cy)),
        's': anim(lambda t: [S * 100 * scale(t)] * 2, 2) if scale else static([S * 100, S * 100]),
        'r': static(0),
        'o': anim(lambda t: 100 * opacity(t)) if opacity else static(100),
    }
    LAYERS.append({'ddd': 0, 'ind': len(LAYERS) + 1, 'ty': 4, 'nm': name, 'sr': 1, 'ks': ks, 'ao': 0,
                   'shapes': shapes, 'ip': 0, 'op': OP, 'st': 0, 'bm': 0})


def screen_bg(c):
    return [group([rect(W / 2, H / 2, W + 4, H, RADIUS), fill(c)], 'screen')]


# ---- Equal

def equal_layout():
    title_top = 62
    sub_top = title_top + lh('title') + 3
    pill_top = sub_top + lh('subtitle') + 16
    return title_top, sub_top, pill_top


def equal_screen(name, after, opacity):
    title_top, sub_top, pill_top = equal_layout()
    pill_cy = pill_top + 20
    # Within a layer, shapes listed first draw on top.
    layer(f'{name} · screen', [
        text('title', 'equal_textPrimary', W / 2, top=title_top, align='center'),
        text('subtitle', 'equal_textSecondary', W / 2, top=sub_top, align='center'),
        group([rect(W / 2, pill_cy, W - 32, 40, 20), stroke('equal_strokeSubtle', 1, 6),
               fill('equal_surface')], 'pill'),
    ] + screen_bg('equal_screenBg'), opacity=opacity)

    def button(label, used, shown):
        bw = width(label) + 24
        cx = 214 - 5 - bw / 2
        avail = (W - 32) - 12 - 5 - 6 - bw
        k = max(0.8, min(1.0, avail / width('code')))
        layer(f'{name} · code ({label})', [text('code', 'equal_textPrimary', 28, center_y=0, scale=k)],
              0, pill_cy, opacity=lambda t: opacity(t) * shown(t))
        items = [text(label, 'equal_onActionSoft' if used else 'equal_onAction', 0, center_y=0, align='center'),
                 group([rect(0, 0, bw, 30, 15), fill('equal_actionSoft' if used else 'equal_action')])]
        if used:
            items.insert(1, group([rect(0, 0, bw - 1, 29, 14.5), stroke('equal_action', 1, 25)]))
        layer(f'{name} · {label} button', items, cx, pill_cy,
              opacity=lambda t: opacity(t) * shown(t),
              scale=None if after else (lambda t: press(t, TAP_ACTION, 0.08)))

    if after:
        button('copy', True, lambda t: 1)
        row_top = pill_top + 40 + 24
        row_h = max(15, lh('activated'))
        row_cy = row_top + row_h / 2
        row_w = 15 + 6 + width('activated')
        left = W / 2 - row_w / 2
        tick = lambda t: 1 - (1 - min(max((t - (TAP_CONFIRM + 0.05)) / 0.2, 0), 1)) ** 2   # easeOut 0.2 s
        layer(f'{name} · checkbox', [
            group([rect(0, 0, 13.8, 13.8, 3.4), stroke('equal_textPrimary', 1.2, 30)], 'border'),
            group([rect(0, 0, 15, 15, 4), fill('equal_surface')], 'box'),
        ], left + 7.5, row_cy, opacity=lambda t: opacity(t) * (1 - tick(t)))
        layer(f'{name} · checkbox ticked', [
            group([poly([[-3.4, 0.2], [-1.1, 2.6], [3.6, -2.4]]), stroke('equal_onAction', 1.8)], 'check'),
            group([rect(0, 0, 15, 15, 4), fill('equal_action')], 'box'),
        ], left + 7.5, row_cy, opacity=lambda t: opacity(t) * tick(t))
        layer(f'{name} · activated', [text('activated', 'equal_textPrimary', left + 21, center_y=row_cy)],
              opacity=opacity)
        cta_cy = row_top + row_h + 10 + 20
        layer(f'{name} · continue', [
            text('continue', 'equal_onAction', 0, center_y=0, align='center',
                 opacity=anim(lambda t: 100 * (0.8 + 0.2 * tick(t)))),
            group([rect(0, 0, W - 32, 40, 20), fill('equal_action', anim(lambda t: 100 * (0.38 + 0.62 * tick(t))))]),
        ], W / 2, cta_cy, opacity=opacity)
    else:
        copied = lambda t: 1.0 if TAP_ACTION + 0.05 < t < 9 else 0.0
        button('copy', False, lambda t: 1 - copied(t))
        button('copied', True, copied)


# ---- iOS Phone keypad

def keypad(opacity):
    field_cy = 46 + 14
    layer('keypad · screen', screen_bg('iosPhone_bg'), opacity=opacity)
    keys = '123456789*0#'
    items = []
    for n, k in enumerate(keys):
        r, c = divmod(n, 3)
        cx, cy = 46 + 17 + c * 52, 82 + 17 + r * 39
        items.append(group([text(f'key{k}', 'iosPhone_label', cx, center_y=cy, align='center'),
                            group([ellipse(cx, cy, 34), fill('iosPhone_key')], 'circle')], f'key {k}'))
    layer('keypad · keys', items, opacity=opacity)
    k = min(1.0, max(0.7, (W - 32) / width('dialled')))
    layer('keypad · pasted code', [text('dialled', 'iosPhone_label', 0, center_y=0, align='center', scale=k)],
          W / 2, field_cy, opacity=lambda t: opacity(t) * (1.0 if t > TAP_PASTE + 0.1 else 0.0))
    pw = width('paste') + 28
    layer('keypad · Paste', [text('paste', '#FFFFFF', 0, center_y=0, align='center'),
                             group([rect(0, 0, pw, 28, 14), fill('#2C2C2E')])],
          W / 2, field_cy, opacity=lambda t: opacity(t) * window(t, TAP_PASTE - 0.35, TAP_PASTE + 0.1, 0.15))
    layer('keypad · call', [group(svg_path(HANDSET, 15 / 24, -7.5, -7.5) + [fill('#FFFFFF')], 'handset'),
                            group([ellipse(0, 0, 36), fill('iosPhone_call')], 'button')],
          W / 2, 239 + 18, opacity=opacity, scale=lambda t: press(t, TAP_DIAL, 0.1))


# ---- the carrier's reply

def carrier(opacity):
    layer('carrier · screen', screen_bg('#111111'), opacity=opacity)
    y = 58
    layer('carrier · calling', [text('calling', '#FFFFFF', W / 2, top=y, align='center', opacity=60)], opacity=opacity)
    y += lh('calling')
    for i, kind in enumerate(('Voice', 'Data', 'SMS')):
        y += 12
        top = y
        y += lh('succeeded') + 1 + lh(f'kind{kind}')
        a = lambda t, i=i: ramp(t, CARRIER[0] + 0.6 + i * 0.35, CARRIER[0] + 0.9 + i * 0.35)
        strength = 1 if i == 0 else 0.8
        layer(f'carrier · {kind}', [
            text('succeeded', '#FFFFFF', W / 2, top=top, align='center'),
            text(f'kind{kind}', '#FFFFFF', W / 2, top=top + lh('succeeded') + 1, align='center', opacity=75),
        ], opacity=lambda t, a=a: opacity(t) * a(t) * strength, dy=lambda t, a=a: 6 * (1 - a(t)))
    y += 12 + 4
    dw = width('dismiss') + 60
    layer('carrier · Dismiss', [text('dismiss', '#000000', 0, center_y=0, align='center'),
                                group([rect(0, 0, dw, 32, 16), fill('#FFFFFF')])],
          W / 2, y + 16, opacity=lambda t: opacity(t) * ramp(t, CARRIER[0] + 1.8, CARRIER[0] + 2.1))


# ---- chrome

def status_bar(c, opacity):
    cy = (ISLAND_Y - SCREEN_Y) / S
    right = W - 22
    battery = [group([rect(right - 11.5, cy, 21, 10, 3), stroke(c, 1, 40)], 'battery'),
               group([rect(right - 11.5, cy, 17.5, 6.5, 1.7), fill(c)], 'charge'),
               group([rect(right + 0.4, cy, 1.4, 3.6, 0.7), fill(c, 40)], 'nub')]
    wx, wy = right - 21 - 4 - 7.5, cy + 4.6
    wifi = [group([arc(wx, wy, r, -45, 45), stroke(c, 1.7)], f'wifi {r}') for r in (4.4, 7.6)] + \
           [group([ellipse(wx, wy - 1, 2.6), fill(c)], 'wifi dot')]
    bx = wx - 7.5 - 4 - 15
    bars = [group([rect(bx + 1.5 + j * 4, cy + 5 - h / 2, 2.8, h, 0.8), fill(c)], f'bar {j}')
            for j, h in enumerate((3.6, 5.6, 7.6, 9.6))]
    layer(f'status bar ({c})', [text('time', c, 24, center_y=cy)] + battery + wifi + bars, opacity=opacity)


def tap_marks():
    for name, at, (x, y) in (('Copy', TAP_ACTION, (184, 139)), ('Paste', TAP_PASTE, (115, 60)),
                             ('Call', TAP_DIAL, (115, 257)), ('confirm', TAP_CONFIRM, (31, 190))):
        a = lambda t, at=at: ramp(t, at - 0.45, at - 0.15) * (1 - ramp(t, at + 0.2, at + 0.45))
        p = lambda t, at=at: 1 - 0.18 * ramp(t, at - 0.15, at) * (1 - ramp(t, at, at + 0.2))
        layer(f'finger · {name}', [group([ellipse(0, 0, 34), stroke('#FFFFFF', 2.5)], 'ring'),
                                   group([ellipse(0, 0, 34), fill('#000000', 20)], 'dot')],
              x, y, opacity=a, scale=p)


def done_tick():
    p = lambda t: ramp(t, DONE[0] + 0.2, DONE[0] + 0.55)
    out = lambda t: ramp(t, 11.0, 11.3)

    def scale(t):
        pop = 0.5 + 0.5 * p(t) + 0.12 * math.sin(p(t) * math.pi)
        return pop * (1 - 0.15 * out(t))
    grad = {'ty': 'gf', 'o': static(100), 'r': 1, 't': 1, 's': static([0, -38]), 'e': static([0, 38]),
            'g': {'p': 2, 'k': static([0] + hexc('#5BDB6A') + [1] + hexc('#00B140'))}}
    halo = [group([ellipse(0, 8, 76 + 2 * r), fill('#00B140', o)], f'glow {r}')
            for r, o in ((4, 5), (9, 4), (15, 3))]
    layer('done tick', [group([poly([[-11, 0.5], [-3.6, 8], [12, -8.5]]), stroke('#FFFFFF', 4.6)], 'check'),
                        group([ellipse(0, 0, 76), grad], 'disc')] + halo,
          W / 2, 118 + 38, opacity=lambda t: p(t) * (1 - out(t)), scale=scale)


# ---------------------------------------------------------------- assembly

def build():
    load_glyphs()
    LAYERS.clear()
    carrier_on = lambda t: window(t, CARRIER[0], CARRIER[1], 0.25)
    dark_bar = lambda t: 1.0 if carrier_on(t) > 0.5 else 0.0

    # Bottom first, as in the Swift's ZStack.
    layer('screen', screen_bg('equal_screenBg'))
    equal_screen('Equal', False, lambda t: max(window(t, -1, APP[1], 0.25), ramp(t, 11.1, 11.5)))
    keypad(lambda t: window(t, DIAL[0], DIAL[1], 0.25))
    carrier(carrier_on)
    equal_screen('Equal, back', True, lambda t: window(t, BACK[0], DONE[0], 0.3))
    done_tick()
    status_bar('ios_statusBar', lambda t: 1 - dark_bar(t))
    status_bar('#FFFFFF', dark_bar)
    tap_marks()

    # The voicemail Lottie's phone (bezel and island), on top of everything.
    vm = json.load(open(VOICEMAIL))
    frame = next(l for l in vm['layers'] if l['nm'] == 'frame')
    vm_assets = {a['id']: a for a in vm['assets']}
    pre = vm_assets[frame['refId']]
    image_ids = {l['refId'] for l in pre['layers'] if l.get('ty') == 2}
    frame = dict(frame, ip=0, op=OP, ind=0, st=0)
    frame.pop('tm', None)
    pre = json.loads(json.dumps(pre))
    for l in pre['layers']:
        l['ip'], l['op'] = 0, OP
    layers = [frame] + LAYERS[::-1]
    for n, l in enumerate(layers):
        l['ind'] = n + 1
    anim_json = {
        'v': '5.12.0', 'fr': FPS, 'ip': 0, 'op': OP, 'w': 512, 'h': 720, 'nm': 'Call forwarding', 'ddd': 0,
        'meta': {'g': 'EqualOnboarding tools/build_forwarding_lottie.py'},
        'assets': [vm_assets[i] for i in sorted(image_ids)] + [pre],
        'layers': layers,
        'slots': {k: {'p': {'a': 0, 'k': hexc(v)}} for k, v in SLOTS.items()},
    }
    return anim_json


if __name__ == '__main__':
    import sys
    d = build()
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'docs', 'lottie', 'forwarding.json')
    json.dump(d, open(out, 'w'), separators=(',', ':'))
    print(f'wrote {out}: {len(d["layers"])} layers, {os.path.getsize(out) // 1024} KB')
