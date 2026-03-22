#!/usr/bin/env python3
"""
Draw Assistant — Symbol Placer
Inkscape 1.x extension (tested on 1.4).

Workflow
--------
1. Open via:  Extensions > Draw Assistant > Place Symbol
2. Choose the library, type the exact Symbol ID, click Apply.

The symbol is embedded (inline) into the current layer at its original scale.
- If an object is selected the symbol is centred on that object's bounding box.
- Otherwise it is placed at the current page centre.
- Enable "Replace selected shape" to delete the placeholder after placing.

Symbol library SVG files are downloaded automatically on first use and cached
in the 'symbols/' sub-folder next to this script.
"""

import os
import re
import copy
import urllib.request
import inkex
from lxml import etree

# Namespaces
SVG_NS      = 'http://www.w3.org/2000/svg'
INKSCAPE_NS = 'http://www.inkscape.org/namespaces/inkscape'

# Library download URLs
LIBRARY_URLS = {
    'AH-analog':
        'https://raw.githubusercontent.com/analoghub-ie/art/main/inkscapeSymbols/AH-analog.svg',
    'AH-behavioural':
        'https://raw.githubusercontent.com/analoghub-ie/art/main/inkscapeSymbols/AH-behavioural.svg',
    'AH-logic-gates':
        'https://raw.githubusercontent.com/analoghub-ie/art/main/inkscapeSymbols/AH-logic-gates.svg',
}


class DrawAssistant(inkex.EffectExtension):

    def add_arguments(self, pars):
        pars.add_argument('--library',   type=str,           default='AH-analog')
        pars.add_argument('--symbol_id', type=str,           default='')
        pars.add_argument('--replace',   type=inkex.Boolean, default=False)

    # ------------------------------------------------------------------
    def effect(self):
        lib_root = self._load_library(self.options.library)
        if lib_root is None:
            return  # error already reported

        if self.options.replace and self.svg.selection:
            # Replace every selected shape whose inkscape:label / id matches a symbol
            replaced = 0
            for elem in list(self.svg.selection.values()):
                label = (
                    elem.get('{%s}label' % INKSCAPE_NS)
                    or elem.get('id')
                    or ''
                ).strip()
                sym = self._find_symbol(lib_root, label)
                if sym is not None:
                    self._replace_element(elem, sym)
                    replaced += 1
            if replaced == 0:
                inkex.errormsg(
                    "No selected object has a label/ID matching a symbol in the "
                    "chosen library.\n\nSet the object label via "
                    "Object > Object Properties, then try again."
                )
        else:
            symbol_id = self.options.symbol_id.strip()
            if not symbol_id:
                inkex.errormsg("Please enter a Symbol ID (e.g. 'Opamp' or 'NMOS').")
                return

            sym = self._find_symbol(lib_root, symbol_id)
            if sym is None:
                inkex.errormsg(
                    "Symbol '%s' was not found in '%s'.\n\n"
                    "The ID is case-sensitive. See README for the full symbol list."
                    % (symbol_id, self.options.library)
                )
                return

            cx, cy = self._target_centre()
            group  = self._symbol_to_group(sym)
            self._centre_group(group, cx, cy)
            self.svg.get_current_layer().append(group)

    # ------------------------------------------------------------------
    def _load_library(self, lib_name):
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
                inkex.utils.debug("Downloading %s.svg ..." % lib_name)
                urllib.request.urlretrieve(url, lib_path)
            except Exception as exc:
                inkex.errormsg(
                    "Could not download library '%s':\n%s\n\n"
                    "Check your internet connection, or manually place the SVG at:\n%s"
                    % (lib_name, exc, lib_path)
                )
                return None

        try:
            return etree.parse(lib_path).getroot()
        except Exception as exc:
            inkex.errormsg("Could not parse library SVG:\n%s" % exc)
            return None

    # ------------------------------------------------------------------
    def _find_symbol(self, root, symbol_id):
        if not symbol_id:
            return None
        return root.find('.//{%s}symbol[@id="%s"]' % (SVG_NS, symbol_id))

    # ------------------------------------------------------------------
    def _symbol_to_group(self, symbol):
        """Deep-copy symbol children (skip <title>) into a new <g>."""
        group = etree.Element('{%s}g' % SVG_NS)
        group.set('{%s}label' % INKSCAPE_NS, symbol.get('id', 'symbol'))
        for child in symbol:
            tag = child.tag if isinstance(child.tag, str) else ''
            if 'title' in tag:
                continue
            group.append(copy.deepcopy(child))
        return group

    # ------------------------------------------------------------------
    def _rough_centre(self, group):
        """
        Estimate the visual centre of a group from numeric coordinate attributes
        and the first M/m coordinate in path 'd' data.
        """
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

    def _centre_group(self, group, target_cx, target_cy):
        """Translate the group so its rough centre lands on (target_cx, target_cy)."""
        sym_cx, sym_cy = self._rough_centre(group)
        dx = target_cx - sym_cx
        dy = target_cy - sym_cy
        if dx or dy:
            group.set('transform', 'translate(%.6f,%.6f)' % (dx, dy))

    def _target_centre(self):
        """Return (cx, cy) where the symbol should be centred."""
        if self.svg.selection:
            try:
                elem = list(self.svg.selection.values())[0]
                bb = elem.bounding_box()
                if bb:
                    return bb.center_x, bb.center_y
            except Exception:
                pass
        # Fall back to page centre
        try:
            vb = self.svg.get_viewbox()
            return vb[0] + vb[2] / 2, vb[1] + vb[3] / 2
        except Exception:
            return self.svg.viewbox_width / 2, self.svg.viewbox_height / 2

    # ------------------------------------------------------------------
    def _replace_element(self, elem, symbol):
        """Replace elem with the symbol centred at elem's bounding-box centre."""
        try:
            bb = elem.bounding_box()
            cx, cy = bb.center_x, bb.center_y
        except Exception:
            cx, cy = 0, 0

        parent = elem.getparent()
        idx    = list(parent).index(elem)
        parent.remove(elem)

        group = self._symbol_to_group(symbol)
        self._centre_group(group, cx, cy)
        parent.insert(idx, group)


if __name__ == '__main__':
    DrawAssistant().run()
