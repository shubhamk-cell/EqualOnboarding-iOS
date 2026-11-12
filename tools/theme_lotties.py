#!/usr/bin/env python3
"""Builds the themed dotLottie files for the two setup steps (docs/lottie/*.lottie).

- forwarding.lottie: the build's call-forwarding walkthrough (copy flow), drawn into the
  voicemail Lottie's phone by tools/build_forwarding_lottie.py.
- voicemail.lottie: the app's voicemail.json, with each colour slot renamed for the screen it
  sits on.

Both fade out at the bottom as the app fades them (opaque to 62 % of the height, then eased).

Equal's own screens, tips and highlights take Equal's alias tokens (Figma "Colour Guide — Alias
Tokens"); iOS screens (Phone keypad, Settings, status bar) take iOS's own light/dark colours.
Some parts stay as drawn in both themes: the home screen (wallpaper and app icons), the
carrier's reply (already a dark system sheet), the finger marks, the green done tick and the
phone itself.

Slot prefixes:
  equal_*     Equal's screens, tips and highlights → Equal alias tokens
  iosPhone_*  the Phone app keypad                 → iOS system colours
  ios_*       iOS Settings pages and status bar    → iOS system colours

Each file has two themes, "light" and "dark"; "light" is the initial one. The app itself plays
voicemail.json and draws the forwarding walkthrough in SwiftUI (Lottie for iOS ignores slots),
so this only produces files to share. Run from the repo root:

    python3 tools/theme_lotties.py
"""
import copy
import json
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'EqualOrbOnboarding', 'Resources', 'Lottie')
OUT = os.path.join(ROOT, 'docs', 'lottie')


def hx(s, a=1.0):
    s = s.lstrip('#')
    return [round(int(s[i:i + 2], 16) / 255, 4) for i in (0, 2, 4)] + [a]


def color(slot, light, dark):
    return slot, {'light': light, 'dark': dark}


# Equal alias tokens (light, dark), from Figma.
EQ = {
    'bg/primary': ('#F7F7F7', '#000000'),
    'bg/surface': ('#FFFFFF', '#222222'),
    'text/primary': ('#111111', '#F7F7F7'),
    'text/secondary': ('#555555', '#BBBBBB'),
    'text/placeholder': ('#AAAAAA', '#777777'),
    'text/action': ('#00B140', '#BAFF29'),
    'text/on-action': ('#FFFFFF', '#000000'),
    'text/on-action-disabled': ('#888888', '#888888'),
    'chat-bubble/user-bg': ('#E8FFED', '#1E2C22'),
    'chat-bubble/user-title': ('#006223', '#BBFF9C'),
    'button/primary': ('#00B140', '#BAFF29'),
    'button/disabled': ('#DDDDDD', '#444444'),
    'grey08': ('#888888', '#888888'),
    'grey11': ('#BBBBBB', '#555555'),
    'grey12': ('#CCCCCC', '#555555'),
}


def tok(name):
    return EQ[name]


# ---------------------------------------------------------------- forwarding

# Built by tools/build_forwarding_lottie.py (the build's walkthrough in the voicemail phone), with
# its colours already in named slots.
FWD_THEME = {
    'equal_screenBg': tok('bg/primary'),
    'equal_surface': tok('bg/surface'),
    'equal_textPrimary': tok('text/primary'),
    'equal_textSecondary': tok('text/secondary'),
    'equal_strokeSubtle': ('#000000', '#FFFFFF'),          # stroke/subtle, drawn at 6 %
    'equal_action': tok('button/primary'),
    'equal_onAction': tok('text/on-action'),
    'equal_actionSoft': tok('chat-bubble/user-bg'),         # "Copied": soft green
    'equal_onActionSoft': tok('chat-bubble/user-title'),
    # iOS: light as iOS draws it, and iOS dark.
    'iosPhone_bg': ('#FFFFFF', '#000000'),
    'iosPhone_key': ('#E5E5EA', '#333333'),
    'iosPhone_label': ('#000000', '#FFFFFF'),
    'iosPhone_call': ('#34C759', '#30D158'),
    'ios_statusBar': ('#000000', '#FFFFFF'),
}


def build_forwarding():
    import build_forwarding_lottie
    d = build_forwarding_lottie.build()
    assert set(d['slots']) == set(FWD_THEME), set(d['slots']) ^ set(FWD_THEME)
    rules = {theme: [{'id': s, 'type': 'Color', 'value': hx(v[i])} for s, v in FWD_THEME.items()]
             for i, theme in enumerate(('light', 'dark'))}
    return d, rules


# ---------------------------------------------------------------- voicemail

VM_THEME = {
    # iOS Settings pages: iOS light as drawn, iOS dark.
    'ios_page': ('#FFFFFF', '#000000'),
    'ios_screen': ('#ECECEC', '#000000'),
    'ios_container': ('#FFFFFF', '#1C1C1E'),
    'ios_bg': ('#F5F5F5', '#1C1C1E'),
    'ios_title': ('#000000', '#FFFFFF'),
    'ios_subtext': ('#000000', '#FFFFFF'),
    'ios_skeleton': ('#D9D9D9', '#3A3A3C'),
    'ios_handle': ('#FFFFFF', '#FFFFFF'),
    # Equal's own guidance on top of iOS: the row highlight and the tips.
    'equal_highlight': tok('text/action'),
    'equal_tipFill': tok('text/primary'),
    'equal_tipText': ('#FFFFFF', '#111111'),
}
# Live Voicemail's switch turning off (frames 194→206): iOS green → iOS off track.
VM_TOGGLE = {'light': ('#33C759', '#B9B9B9'), 'dark': ('#30D158', '#39393D')}


def split_voicemail(d):
    assets = {a['id']: a for a in d['assets']}
    base = d['slots']
    slots = {}

    def name_for(kind, sid):
        if sid == 'primary':
            return 'equal_highlight' if kind == 'st' else 'ios_toggle'
        return {'chat': 'equal_tipFill', 'textInv': 'equal_tipText', 'light': 'ios_light'}.get(sid, f'ios_{sid}')

    def walk(o, seen):
        if isinstance(o, dict):
            if o.get('ty') in ('fl', 'st') and isinstance(o.get('c'), dict) and 'sid' in o['c']:
                c = o['c']
                n = name_for(o['ty'], c['sid'])
                if n not in slots:
                    slots[n] = copy.deepcopy(base[c['sid']]) if 'p' in base.get(c['sid'], {}) \
                        else {'p': {'a': c.get('a', 0), 'k': copy.deepcopy(c['k'])}}
                c['sid'] = n
            for k, v in o.items():
                if k == 'refId' and v in assets and 'layers' in assets[v]:
                    if v not in seen:
                        seen.add(v)
                        walk(assets[v]['layers'], seen)
                else:
                    walk(v, seen)
        elif isinstance(o, list):
            for v in o:
                walk(v, seen)

    walk(d['layers'], set())
    # The white page under the Live Voicemail screen.
    page = next(l for l in d['layers'] if l.get('nm') == 'screen-fill')
    fill = next(i for i in page['shapes'][0]['it'] if i['ty'] == 'fl')
    fill['c'] = {'a': 0, 'k': [1, 1, 1, 1], 'sid': 'ios_page'}
    slots['ios_page'] = {'p': {'a': 0, 'k': [1, 1, 1]}}
    # Equal's highlight is a still colour (it's gone before the switch animates).
    slots['equal_highlight'] = {'p': {'a': 0, 'k': hx(EQ['text/action'][0])[:3]}}
    d['slots'] = dict(sorted(slots.items()))

    kf = base['primary']['p']['k']
    rules = {}
    for theme in ('light', 'dark'):
        i = 0 if theme == 'light' else 1
        on, off = VM_TOGGLE[theme]
        rules[theme] = [{'id': s, 'type': 'Color', 'value': hx(v[i])}
                        for s, v in VM_THEME.items() if s in d['slots']]
        rules[theme].append({'id': 'ios_toggle', 'type': 'Color', 'keyframes': [
            {'frame': kf[0]['t'], 'value': hx(on), 'outTangent': kf[0]['o'], 'inTangent': kf[0]['i']},
            {'frame': kf[1]['t'], 'value': hx(off)}]})
    return d, rules


# ---------------------------------------------------------------- bottom fade

def fade_bottom(d, start=0.62):
    """Fades the whole animation out at the bottom, as the app's SoftBottomFade does: opaque to
    `start` of the height, then an eased (smoothstep) ramp to nothing at the bottom edge. The
    animation moves into a precomp under an alpha matte holding that gradient."""
    w, h, ip, op = d['w'], d['h'], d['ip'], d['op']
    steps = 10
    stops = [(0.0, 1.0)] + [(start + (1 - start) * i / steps,
                              1 - (i / steps) ** 2 * (3 - 2 * i / steps)) for i in range(steps + 1)]
    colours = [0, 0, 0, 0, 1, 0, 0, 0]
    alphas = [x for pos, a in stops for x in (round(pos, 4), round(a, 4))]
    static = lambda v: {'a': 0, 'k': v}
    matte = {
        'ddd': 0, 'ind': 1, 'ty': 4, 'nm': 'bottom fade (matte)', 'td': 1, 'sr': 1, 'ao': 0,
        'ks': {'a': static([0, 0]), 'p': static([0, 0]), 's': static([100, 100]), 'r': static(0), 'o': static(100)},
        'shapes': [{'ty': 'gr', 'nm': 'fade', 'it': [
            {'ty': 'rc', 'd': 1, 'p': static([w / 2, h / 2]), 's': static([w, h]), 'r': static(0)},
            {'ty': 'gf', 'o': static(100), 'r': 1, 't': 1, 's': static([w / 2, 0]), 'e': static([w / 2, h]),
             'g': {'p': 2, 'k': static(colours + alphas)}},
            {'ty': 'tr', 'p': static([0, 0]), 'a': static([0, 0]), 's': static([100, 100]), 'r': static(0),
             'o': static(100), 'sk': static(0), 'sa': static(0)}]}],
        'ip': ip, 'op': op, 'st': 0, 'bm': 0,
    }
    d['assets'].append({'id': 'content', 'nm': 'content', 'layers': d['layers']})
    content = {'ddd': 0, 'ind': 2, 'ty': 0, 'nm': 'content', 'refId': 'content', 'tt': 1, 'sr': 1, 'ao': 0,
               'ks': {'a': static([0, 0]), 'p': static([0, 0]), 's': static([100, 100]), 'r': static(0),
                      'o': static(100)},
               'w': w, 'h': h, 'ip': ip, 'op': op, 'st': 0, 'bm': 0}
    d['layers'] = [matte, content]
    return d


# ---------------------------------------------------------------- packaging

def pack(d, anim_id, rules, out):
    themes = list(rules)
    manifest = {'version': '2', 'generator': 'EqualOnboarding tools/theme_lotties.py',
                'animations': [{'id': anim_id, 'initialTheme': 'light', 'themes': themes}],
                'themes': [{'id': t} for t in themes]}
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json', json.dumps(manifest, indent=2))
        z.writestr(f'a/{anim_id}.json', json.dumps(d, separators=(',', ':')))
        for t, r in rules.items():
            z.writestr(f't/{t}.json', json.dumps({'rules': r}, indent=1))
    print(f'{os.path.relpath(out, ROOT)}: {len(d["slots"])} slots, themes {themes}, '
          f'{os.path.getsize(out) // 1024} KB')


def main():
    os.makedirs(OUT, exist_ok=True)
    d, rules = build_forwarding()
    pack(fade_bottom(d), 'forwarding', rules, os.path.join(OUT, 'forwarding.lottie'))
    with open(os.path.join(SRC, 'voicemail.json')) as f:
        d, rules = split_voicemail(json.load(f))
    pack(fade_bottom(d), 'voicemail', rules, os.path.join(OUT, 'voicemail.lottie'))


if __name__ == '__main__':
    main()
