#!/usr/bin/env python3
"""Builds themed dotLottie files (docs/lottie/*.lottie) from the app's two setup Lotties.

Each colour gets a slot named for the screen it sits on, so a theme can colour Equal's own
screens with Equal's alias tokens (Figma "Colour Guide — Alias Tokens") and the iOS screens
(Phone keypad, Settings) with iOS's own light/dark system colours. Some parts stay as drawn in
both themes: the home screen (wallpaper and app icons), the carrier's reply (already a dark
system sheet), the brand gradients and the phone itself.

Slot prefixes:
  equal_*     Equal app screens and Equal's own tips/highlights → Equal alias tokens
  iosPhone_*  the Phone app keypad                              → iOS system colours
  iosAlert_*  the carrier's reply sheet                         → left as drawn (no rules)
  ios_*       iOS Settings pages (voicemail)                    → iOS system colours

Each file has two themes, "light" and "dark"; "light" is the initial one. The app itself plays
the plain JSONs (Lottie for iOS ignores slots), so this only produces files to share.

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
    'text/on-action-disabled': ('#888888', '#888888'),
    'button/primary': ('#00B140', '#BAFF29'),
    'button/disabled': ('#DDDDDD', '#444444'),
    'grey08': ('#888888', '#888888'),
    'grey11': ('#BBBBBB', '#555555'),
    'grey12': ('#CCCCCC', '#555555'),
}


def tok(name):
    return EQ[name]


# ---------------------------------------------------------------- forwarding

# Which precomp (asset id) or layer belongs to which screen.
FWD_GROUPS = {
    'asset:1552': 'equal',      # Equal's call-forwarding screen
    'asset:227': 'equal',       # its "Use this code" card, lifted out
    'asset:237': 'equal',       # the success badge
    'layer:ROOT:233': 'equal',  # the badge's tick
    'asset:1974': 'iosPhone',   # Phone keypad
    'asset:506': 'iosPhone',    # the pasted code on the keypad
    'asset:416': 'iosAlert',    # the carrier's reply
    'layer:1981:242': None,     # phone hardware / masks: not themable
    'layer:1981:1980': None,
    'layer:1977:1555': None,
}

FWD_THEME = {
    # Equal screen
    'equal_screenBg': tok('bg/primary'),
    'equal_surface': tok('bg/surface'),
    'equal_textPrimary': tok('text/primary'),
    'equal_textSecondary': tok('text/secondary'),
    'equal_textTertiary': ('#888888', '#888888'),
    'equal_textQuaternary': tok('text/placeholder'),
    'equal_brandPrimary': tok('button/primary'),
    'equal_skeleton': tok('button/disabled'),
    'equal_skeletonAlt': tok('button/disabled'),
    'equal_skeletonDeep': tok('grey12'),
    'equal_neutralLight': tok('grey11'),
    'equal_ctaLabel': tok('text/on-action-disabled'),
    'equal_surfaceMuted': tok('button/disabled'),
    'equal_tintBlue': ('#DFECFF', '#1B2633'),
    'equal_tintYellow': ('#FFFCAF', '#33321C'),
    # iOS Phone keypad: iOS light as drawn, iOS dark.
    'iosPhone_surface': ('#FFFFFF', '#000000'),
    'iosPhone_textPrimary': ('#000000', '#FFFFFF'),
    'iosPhone_keypadKey': ('#E2E2E2', '#333333'),
    'iosPhone_keypadSurface': ('#E6E6E6', '#2C2C2E'),
    'iosPhone_neutral': ('#A3A3A3', '#8E8E93'),
    'iosPhone_neutralLight': ('#B8B8B8', '#48484A'),
    'iosPhone_textTertiary': ('#858484', '#8E8E93'),
    'iosPhone_textQuaternary': ('#929292', '#636366'),
    'iosPhone_systemBlue': ('#216ED6', '#0A84FF'),
    'iosPhone_successFill': ('#31C75C', '#30D158'),
    'iosPhone_tintBlue': ('#DFECFF', '#0A2440'),
    'iosPhone_tintYellow': ('#FFFCAF', '#3A3510'),
}


def fwd_gradient_rules():
    """The Equal screen's bottom scrim fades into the screen colour."""
    rules = {}
    for theme, (r, g, b, _) in (('light', hx(EQ['bg/primary'][0])), ('dark', hx(EQ['bg/primary'][1]))):
        rules[theme] = [{'id': 'equal_gradientScrim', 'type': 'Gradient',
                         'value': [{'color': [r, g, b, 0], 'offset': 0},
                                   {'color': [r, g, b, 1], 'offset': 0.044}]}]
    return rules


def split_forwarding(d):
    assets = {a['id']: a for a in d['assets']}
    base = d['slots']
    used = {}

    def rename(o, g):
        if isinstance(o, dict):
            if isinstance(o.get('sid'), str):
                old = o['sid']
                if g is None:
                    del o['sid']
                else:
                    o['sid'] = f'{g}_{old}'
                    used[o['sid']] = old
            for k, v in o.items():
                if k != 'refId':
                    rename(v, g)
        elif isinstance(o, list):
            for v in o:
                rename(v, g)

    done = set()

    def visit(layers, owner, g):
        for l in layers:
            key = f'layer:{owner}:{l.get("ind")}'
            lg = FWD_GROUPS[key] if key in FWD_GROUPS else g
            aid = l.get('refId')
            if aid in assets and 'layers' in assets[aid]:
                rename(l, lg)
                if aid in done:
                    continue
                done.add(aid)
                ak = f'asset:{aid}'
                visit(assets[aid]['layers'], aid, FWD_GROUPS[ak] if ak in FWD_GROUPS else lg)
            else:
                rename(l, lg)

    visit(d['layers'], 'ROOT', None)
    missing = [k for k in used if k.startswith(('equal_', 'iosPhone_')) and k not in FWD_THEME
               and k not in ('equal_gradientScrim', 'equal_gradientBrand', 'equal_gradientSuccess')]
    assert not missing, f'no theme value for {missing}'
    d['slots'] = {new: copy.deepcopy(base[old]) for new, old in sorted(used.items())}
    rules = fwd_gradient_rules()
    for theme in ('light', 'dark'):
        i = 0 if theme == 'light' else 1
        rules[theme] = [{'id': s, 'type': 'Color', 'value': hx(v[i])}
                        for s, v in FWD_THEME.items() if s in d['slots']] + rules[theme]
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
    for name, split in (('forwarding', split_forwarding), ('voicemail', split_voicemail)):
        with open(os.path.join(SRC, f'{name}.json')) as f:
            d = json.load(f)
        d, rules = split(d)
        pack(d, name, rules, os.path.join(OUT, f'{name}.lottie'))


if __name__ == '__main__':
    main()
