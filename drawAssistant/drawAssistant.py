#!/usr/bin/env python3
"""
Draw Assistant — Symbol Placer + Shape Detector
Inkscape 1.x extension (tested on 1.4).

Actions
-------
place    Place a symbol from the library by ID.
register Register the selected shape(s) as a training example for a symbol.
detect   Detect what symbol each selected shape resembles and replace it.
"""

import os
import re
import copy
import json
import math
import ssl
import urllib.request
import inkex
from lxml import etree

# ── Namespaces ────────────────────────────────────────────────────────────────
SVG_NS      = 'http://www.w3.org/2000/svg'
INKSCAPE_NS = 'http://www.inkscape.org/namespaces/inkscape'

SHAPE_TAGS = {'path', 'rect', 'ellipse', 'circle', 'polygon', 'polyline', 'line'}

# ── Library sources ───────────────────────────────────────────────────────────
LIBRARY_URLS = {
    'AH-analog':
        'https://raw.githubusercontent.com/analoghub-ie/art/main/inkscapeSymbols/AH-analog.svg',
    'AH-behavioural':
        'https://raw.githubusercontent.com/analoghub-ie/art/main/inkscapeSymbols/AH-behavioural.svg',
    'AH-logic-gates':
        'https://raw.githubusercontent.com/analoghub-ie/art/main/inkscapeSymbols/AH-logic-gates.svg',
}

# Feature weights for matching (higher = more important)
FEATURE_WEIGHTS = {
    'ar':           3.0,   # aspect ratio — most discriminative
    'n_paths':      2.0,   # number of separate path elements
    'closed_ratio': 2.5,   # proportion of closed paths
    'curve_ratio':  1.5,   # proportion of paths with bezier/arc curves
    'node_norm':    1.0,   # node count normalised by bounding box perimeter
}

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode    = ssl.CERT_NONE


# ══════════════════════════════════════════════════════════════════════════════
#  Feature extraction
# ══════════════════════════════════════════════════════════════════════════════

def _parse_path_d(d):
    """
    Return (n_nodes, is_closed, has_curves) from an SVG path 'd' attribute.
    n_nodes  = number of drawing commands (proxy for complexity).
    """
    if not d:
        return 0, False, False
    commands  = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]', d)
    n_nodes   = len([c for c in commands if c not in ('Z', 'z')])
    is_closed = bool(re.search(r'[Zz]', d))
    has_curves = bool(re.search(r'[CcSsQqTtAa]', d))
    return n_nodes, is_closed, has_curves


def _collect_shapes(elem):
    """
    Return a flat list of shape elements under elem (or elem itself if it is
    a shape).  Recurse into groups.
    """
    shapes = []
    tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

    if tag in SHAPE_TAGS:
        shapes.append(elem)
    elif tag == 'g':
        for child in elem:
            shapes.extend(_collect_shapes(child))
    return shapes


def extract_features(elem):
    """
    Extract a scale-invariant feature dict from an Inkscape element.
    Works for single paths, groups of paths, rects, ellipses, etc.
    """
    try:
        bbox = elem.bounding_box()
        if bbox is None:
            return None
        w, h = max(bbox.width,  1e-6), max(bbox.height, 1e-6)
    except Exception:
        return None

    shapes = _collect_shapes(elem)
    if not shapes:
        return None

    n_paths     = len(shapes)
    n_nodes     = 0
    closed_cnt  = 0
    curve_cnt   = 0

    for s in shapes:
        tag = s.tag.split('}')[-1] if '}' in s.tag else s.tag

        if tag == 'path':
            nodes, closed, curves = _parse_path_d(s.get('d', ''))
            n_nodes    += nodes
            if closed:  closed_cnt += 1
            if curves:  curve_cnt  += 1

        elif tag in ('rect', 'polygon'):
            n_nodes    += 4
            closed_cnt += 1

        elif tag in ('ellipse', 'circle'):
            n_nodes    += 4
            closed_cnt += 1
            curve_cnt  += 1

        elif tag == 'polyline':
            pts = len((s.get('points') or '').split())
            n_nodes += pts

        elif tag == 'line':
            n_nodes    += 2

    perimeter   = 2 * (w + h)
    ar          = w / h
    closed_ratio = closed_cnt / n_paths
    curve_ratio  = curve_cnt  / n_paths
    node_norm    = n_nodes    / perimeter   # nodes per unit perimeter

    return {
        'ar':           ar,
        'n_paths':      n_paths,
        'closed_ratio': closed_ratio,
        'curve_ratio':  curve_ratio,
        'node_norm':    node_norm,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  References database
# ══════════════════════════════════════════════════════════════════════════════

def _refs_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'symbols', 'references.json')


def load_references():
    path = _refs_path()
    if not os.path.isfile(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_references(refs):
    os.makedirs(os.path.dirname(_refs_path()), exist_ok=True)
    with open(_refs_path(), 'w', encoding='utf-8') as f:
        json.dump(refs, f, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
#  Matching
# ══════════════════════════════════════════════════════════════════════════════

def _feature_distance(a, b):
    """Weighted L2 distance between two feature dicts."""
    dist = 0.0
    for key, weight in FEATURE_WEIGHTS.items():
        va = a.get(key, 0.0)
        vb = b.get(key, 0.0)
        # Normalise aspect ratio difference by magnitude
        if key == 'ar':
            diff = abs(va - vb) / max(va, vb, 1e-6)
        else:
            diff = abs(va - vb)
        dist += weight * diff * diff
    return math.sqrt(dist)


def rank_candidates(features, references, top_n=3):
    """
    Return a list of (symbol_id, distance, confidence_pct) sorted best first.
    confidence_pct is a rough 0-100 score (100 = perfect).
    """
    scores = {}
    for symbol_id, examples in references.items():
        # Best distance across all registered examples for this symbol
        best = min(_feature_distance(features, ex) for ex in examples)
        scores[symbol_id] = best

    ranked = sorted(scores.items(), key=lambda x: x[1])[:top_n]

    # Convert distance to confidence %
    # A distance of 0 = 100%, distance ≥ 3 = 0%
    result = []
    for sid, dist in ranked:
        conf = max(0, int(100 - dist * 33))
        result.append((sid, dist, conf))
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  Tkinter candidate dialog
# ══════════════════════════════════════════════════════════════════════════════

def show_candidate_dialog(candidates):
    """
    Show a Tkinter dialog listing the top candidates.
    Returns the chosen symbol_id, or None if the user skips.
    """
    try:
        import tkinter as tk
        from tkinter import font as tkfont
    except ImportError:
        inkex.errormsg("Tkinter is not available — cannot show candidate dialog.")
        return None

    result = [None]

    root = tk.Tk()
    root.title("Draw Assistant — Match")
    root.resizable(False, False)
    root.attributes('-topmost', True)

    try:
        bold = tkfont.Font(family='Arial', size=10, weight='bold')
        norm = tkfont.Font(family='Arial', size=10)
    except Exception:
        bold = norm = None

    tk.Label(root, text="Best symbol matches — pick one:",
             font=bold, pady=8).pack(padx=16)

    for i, (symbol_id, dist, conf) in enumerate(candidates):
        bar = '█' * (conf // 10) + '░' * (10 - conf // 10)
        label = f"  {symbol_id}\n  {bar}  {conf}%"
        btn = tk.Button(
            root,
            text=label,
            font=norm,
            width=34,
            justify='left',
            anchor='w',
            relief='groove',
            pady=4,
            command=lambda sid=symbol_id: (result.__setitem__(0, sid), root.destroy()),
        )
        btn.pack(padx=16, pady=3, fill='x')

    tk.Button(root, text="Skip this shape", fg='gray',
              command=root.destroy).pack(pady=(4, 12))

    root.update_idletasks()
    # Centre on screen
    w = root.winfo_reqwidth()
    h = root.winfo_reqheight()
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f'+{(sw-w)//2}+{(sh-h)//2}')

    root.mainloop()
    return result[0]


# ══════════════════════════════════════════════════════════════════════════════
#  Symbol placement helpers  (shared with place + detect)
# ══════════════════════════════════════════════════════════════════════════════

def _load_library(lib_name):
    ext_dir  = os.path.dirname(os.path.abspath(__file__))
    sym_dir  = os.path.join(ext_dir, 'symbols')
    lib_path = os.path.join(sym_dir, lib_name + '.svg')

    if not os.path.isfile(lib_path):
        url = LIBRARY_URLS.get(lib_name)
        if not url:
            inkex.errormsg("Unknown library: '%s'" % lib_name)
            return None
        try:
            os.makedirs(sym_dir, exist_ok=True)
            req = urllib.request.urlopen(url, context=_SSL_CTX, timeout=15)
            with open(lib_path, 'wb') as f:
                f.write(req.read())
        except Exception as exc:
            inkex.errormsg(
                "Could not download library '%s':\n%s\n\n"
                "Manually place the SVG at:\n%s" % (lib_name, exc, lib_path)
            )
            return None

    try:
        return etree.parse(lib_path).getroot()
    except Exception as exc:
        inkex.errormsg("Could not parse library SVG:\n%s" % exc)
        return None


def _find_symbol_in_any_library(symbol_id):
    """Search all libraries for symbol_id. Returns (lib_root, symbol_elem)."""
    for lib_name in LIBRARY_URLS:
        root = _load_library(lib_name)
        if root is None:
            continue
        sym = root.find('.//{%s}symbol[@id="%s"]' % (SVG_NS, symbol_id))
        if sym is not None:
            return root, sym
    return None, None


def _symbol_to_group(symbol):
    group = etree.Element('{%s}g' % SVG_NS)
    group.set('{%s}label' % INKSCAPE_NS, symbol.get('id', 'symbol'))
    for child in symbol:
        tag = child.tag if isinstance(child.tag, str) else ''
        if 'title' in tag:
            continue
        group.append(copy.deepcopy(child))
    return group


def _rough_centre(group):
    xs, ys = [], []
    for el in group.iter():
        for attr, lst in (('x', xs), ('cx', xs), ('y', ys), ('cy', ys)):
            val = el.get(attr)
            if val:
                try:
                    lst.append(float(val))
                except ValueError:
                    pass
        d = el.get('d', '')
        if d:
            m = re.search(r'[Mm]\s*([-\d.eE+]+)[,\s]+([-\d.eE+]+)', d)
            if m:
                try:
                    xs.append(float(m.group(1)))
                    ys.append(float(m.group(2)))
                except ValueError:
                    pass
    cx = sum(xs) / len(xs) if xs else 0
    cy = sum(ys) / len(ys) if ys else 0
    return cx, cy


def _place_symbol_at(symbol, target_cx, target_cy, layer):
    group = _symbol_to_group(symbol)
    sym_cx, sym_cy = _rough_centre(group)
    dx = target_cx - sym_cx
    dy = target_cy - sym_cy
    if dx or dy:
        group.set('transform', 'translate(%.6f,%.6f)' % (dx, dy))
    layer.append(group)
    return group


def _replace_element_with_symbol(elem, symbol):
    try:
        bb  = elem.bounding_box()
        cx, cy = bb.center_x, bb.center_y
    except Exception:
        cx, cy = 0, 0

    parent = elem.getparent()
    idx    = list(parent).index(elem)
    parent.remove(elem)

    group = _symbol_to_group(symbol)
    sym_cx, sym_cy = _rough_centre(group)
    dx = cx - sym_cx
    dy = cy - sym_cy
    if dx or dy:
        group.set('transform', 'translate(%.6f,%.6f)' % (dx, dy))
    parent.insert(idx, group)


# ══════════════════════════════════════════════════════════════════════════════
#  Extension
# ══════════════════════════════════════════════════════════════════════════════

class DrawAssistant(inkex.EffectExtension):

    def add_arguments(self, pars):
        pars.add_argument('--action',    type=str,           default='place')
        pars.add_argument('--library',   type=str,           default='AH-analog')
        pars.add_argument('--symbol_id', type=str,           default='')
        pars.add_argument('--replace',   type=inkex.Boolean, default=False)

    # ── Dispatch ──────────────────────────────────────────────────────────────
    def effect(self):
        action = self.options.action
        if action == 'place':
            self._do_place()
        elif action == 'register':
            self._do_register()
        elif action == 'detect':
            self._do_detect()
        else:
            inkex.errormsg("Unknown action: '%s'" % action)

    # ── Place ─────────────────────────────────────────────────────────────────
    def _do_place(self):
        lib_root = _load_library(self.options.library)
        if lib_root is None:
            return

        if self.options.replace and self.svg.selection:
            replaced = 0
            for elem in list(self.svg.selection.values()):
                label = (
                    elem.get('{%s}label' % INKSCAPE_NS)
                    or elem.get('id') or ''
                ).strip()
                sym = lib_root.find('.//{%s}symbol[@id="%s"]' % (SVG_NS, label))
                if sym is not None:
                    _replace_element_with_symbol(elem, sym)
                    replaced += 1
            if replaced == 0:
                inkex.errormsg(
                    "No selected object has a label/ID matching a symbol.\n\n"
                    "Set the label via Object > Object Properties."
                )
            return

        symbol_id = self.options.symbol_id.strip()
        if not symbol_id:
            inkex.errormsg("Please enter a Symbol ID.")
            return

        sym = lib_root.find('.//{%s}symbol[@id="%s"]' % (SVG_NS, symbol_id))
        if sym is None:
            inkex.errormsg(
                "Symbol '%s' not found in '%s'.\nID is case-sensitive."
                % (symbol_id, self.options.library)
            )
            return

        cx, cy = self._target_centre()
        _place_symbol_at(sym, cx, cy, self.svg.get_current_layer())

    # ── Register ──────────────────────────────────────────────────────────────
    def _do_register(self):
        if not self.svg.selection:
            inkex.errormsg("Select the shape(s) you want to register, then run again.")
            return

        symbol_id = self.options.symbol_id.strip()
        if not symbol_id:
            inkex.errormsg("Please enter the Symbol ID this shape represents.")
            return

        refs = load_references()

        registered = 0
        for elem in self.svg.selection.values():
            features = extract_features(elem)
            if features is None:
                inkex.errormsg("Could not extract features from one element — skipping.")
                continue
            if symbol_id not in refs:
                refs[symbol_id] = []
            refs[symbol_id].append(features)
            registered += 1

        if registered > 0:
            save_references(refs)
            total = len(refs[symbol_id])
            inkex.utils.debug(
                "Registered %d example(s) for '%s' (total: %d)."
                % (registered, symbol_id, total)
            )
        else:
            inkex.errormsg("No features could be extracted. Make sure you have shapes selected.")

    # ── Detect ────────────────────────────────────────────────────────────────
    def _do_detect(self):
        if not self.svg.selection:
            inkex.errormsg("Select the rough shape(s) to detect, then run again.")
            return

        refs = load_references()
        if not refs:
            inkex.errormsg(
                "No registered examples found.\n\n"
                "Draw some rough shapes, register them first via\n"
                "Extensions > Draw Assistant > Register Shape as Symbol."
            )
            return

        replaced  = 0
        skipped   = 0
        no_match  = 0

        for elem in list(self.svg.selection.values()):
            features = extract_features(elem)
            if features is None:
                skipped += 1
                continue

            candidates = rank_candidates(features, refs, top_n=3)
            if not candidates:
                no_match += 1
                continue

            chosen = show_candidate_dialog(candidates)
            if chosen is None:
                skipped += 1
                continue

            _, sym = _find_symbol_in_any_library(chosen)
            if sym is None:
                inkex.errormsg(
                    "Symbol '%s' not found in any library — skipping." % chosen
                )
                skipped += 1
                continue

            _replace_element_with_symbol(elem, sym)
            replaced += 1

        inkex.utils.debug(
            "Detect complete: %d replaced, %d skipped, %d no-match."
            % (replaced, skipped, no_match)
        )

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _target_centre(self):
        if self.svg.selection:
            try:
                elem = list(self.svg.selection.values())[0]
                bb = elem.bounding_box()
                if bb:
                    return bb.center_x, bb.center_y
            except Exception:
                pass
        try:
            vb = self.svg.get_viewbox()
            return vb[0] + vb[2] / 2, vb[1] + vb[3] / 2
        except Exception:
            return self.svg.viewbox_width / 2, self.svg.viewbox_height / 2


if __name__ == '__main__':
    DrawAssistant().run()
