#!/usr/bin/env python3
"""Listet die verwendeten Schriften in PSD/PSB-Dateien auf, je Datei.

Usage:
    pip install psd-tools
    python3 psd_fonts.py datei.psd ordner/ ...          # je Datei: Schriften
    python3 psd_fonts.py -v ordner/                      # je Datei + Textebene
    python3 psd_fonts.py --summary ordner/               # zusaetzlich Gesamtuebersicht
    python3 psd_fonts.py --csv ordner/ > fonts.csv       # CSV fuer Tabellen

Ausgewertet werden alle Textebenen, auch in Gruppen, ausgeblendete Ebenen und
Textebenen in eingebetteten Smartobjekten (rekursiv). Verknuepfte (externe)
Smartobjekte koennen nicht gelesen werden und werden als Hinweis gemeldet.
Schriften aus ausgeblendeten Ebenen (oder ausgeblendeten Gruppen/Smartobjekten)
werden gekennzeichnet.
Schriften, die nur in der Datei hinterlegt sind, aber von keinem Text verwendet
werden, werden ignoriert. Die Dateien werden ausschliesslich gelesen.
"""
import argparse
import csv
import io
import sys
from collections import defaultdict
from pathlib import Path

from psd_tools import PSDImage

IGNORED_FONTS = {"AdobeInvisFont"}


def _s(v):
    """Decode psd-tools String objects / bytes to plain str."""
    if hasattr(v, "value"):
        v = v.value
    if isinstance(v, bytes):
        v = v.decode("utf-8", "replace")
    return str(v).strip("\x00").strip()


def _default_font_index(resources):
    """Font index of the document's default style sheet (used when a run has no Font)."""
    try:
        for sheet in resources["StyleSheetSet"]:
            data = sheet["StyleSheetData"]
            if "Font" in data:
                return int(data["Font"])
    except Exception:
        pass
    return None


def fonts_in_layer(layer):
    """Return {(font, size)} actually used by the layer's style runs."""
    used = set()
    try:
        resources = layer.resource_dict
        names = [_s(f["Name"]) for f in resources["FontSet"]]
        runs = layer.engine_dict["StyleRun"]["RunArray"]
    except Exception:
        return used
    default_idx = _default_font_index(resources)
    for run in runs:
        try:
            sd = run["StyleSheet"]["StyleSheetData"]
        except Exception:
            continue
        idx = sd.get("Font", default_idx)
        if idx is None:
            continue
        idx = int(idx)
        size = sd.get("FontSize")
        try:
            size = round(float(size), 1) if size is not None else None
        except (TypeError, ValueError):
            size = None
        if 0 <= idx < len(names) and names[idx] not in IGNORED_FONTS:
            used.add((names[idx], size))
    return used


def iter_type_layers(psd, prefix="", notes=None, parent_hidden=False):
    """Yield (layer_path, layer, hidden) for all type layers, descending into embedded smart objects.

    hidden is True if the layer itself, one of its groups or an enclosing smart object is hidden.
    """
    for layer in psd.descendants():
        path = f"{prefix}{layer.name}"
        hidden = parent_hidden or not layer.is_visible()
        if layer.kind == "type":
            yield path, layer, hidden
        elif layer.kind == "smartobject":
            try:
                so = layer.smart_object
                kind = so.kind  # 'data' = eingebettet, 'external'/'alias' = verknuepft
            except Exception as e:
                if notes is not None:
                    notes.append(f"Smartobjekt nicht lesbar: [{path}]: {e}")
                continue
            if kind != "data":
                if notes is not None:
                    notes.append(f"verknuepftes Smartobjekt nicht gelesen: [{path}] -> {so.filename}")
                continue
            try:
                if not so.is_psd():
                    continue
                inner = PSDImage.open(io.BytesIO(so.data))
            except Exception as e:
                if notes is not None:
                    notes.append(f"Smartobjekt nicht lesbar: [{path}]: {e}")
                continue
            yield from iter_type_layers(inner, prefix=f"{path} > ", notes=notes,
                                        parent_hidden=hidden)


def iter_files(paths):
    seen = set()
    for p in map(Path, paths):
        if p.is_dir():
            files = (f for f in sorted(p.rglob("*"))
                     if f.is_file() and f.suffix.lower() in (".psd", ".psb"))
        elif p.is_file():
            files = [p]
        else:
            print(f"!! {p}: nicht gefunden", file=sys.stderr)
            continue
        for f in files:
            key = f.resolve()
            if key not in seen:
                seen.add(key)
                yield f


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="zusaetzlich jede Textebene mit Schrift, Groesse und Text ausgeben")
    ap.add_argument("--summary", action="store_true",
                    help="am Ende Gesamtuebersicht: Schrift -> Anzahl Dateien")
    ap.add_argument("--csv", action="store_true",
                    help="CSV: datei;ebene;text;font;groesse_pt;sichtbar")
    args = ap.parse_args()

    usage = defaultdict(set)  # font -> {files}
    writer = csv.writer(sys.stdout, delimiter=";") if args.csv else None
    if writer:
        writer.writerow(["datei", "ebene", "text", "font", "groesse_pt", "sichtbar"])

    for f in iter_files(args.paths):
        try:
            psd = PSDImage.open(f)
        except Exception as e:
            print(f"!! {f}: {e}", file=sys.stderr)
            continue

        notes = []
        file_fonts = defaultdict(set)  # font -> {sizes}
        visible_fonts = set()          # fonts used in at least one visible layer
        hidden_fonts = set()           # fonts used in at least one hidden layer
        details = []
        for path, layer, hidden in iter_type_layers(psd, notes=notes):
            text = (layer.text or "").replace("\r", " ").replace("\n", " ")[:60]
            for font, size in sorted(fonts_in_layer(layer), key=str):
                file_fonts[font].add(size)
                (hidden_fonts if hidden else visible_fonts).add(font)
                usage[font].add(str(f))
                if writer:
                    writer.writerow([f, path, text, font, size,
                                     "nein" if hidden else "ja"])
                else:
                    details.append((font, size, path, text, hidden))

        if writer:
            for n in notes:
                print(f"!! {f}: {n}", file=sys.stderr)
            continue

        print(f"\n== {f}")
        if not file_fonts:
            print("   (keine Textebenen mit Schriftangaben)")
        for font in sorted(file_fonts):
            sizes = sorted(s for s in file_fonts[font] if s is not None)
            size_txt = ", ".join(f"{s:g}" for s in sizes)
            if font not in visible_fonts:
                mark = "  [nur in ausgeblendeten Ebenen]"
            elif font in hidden_fonts:
                mark = "  [auch in ausgeblendeten Ebenen]"
            else:
                mark = ""
            size_col = size_txt + " pt" if size_txt else ""
            print(f"   {font:<40} {size_col:<14}{mark}".rstrip())
        if args.verbose and details:
            print("   -- Textebenen:")
            for font, size, path, text, hidden in details:
                flag = "(ausgeblendet) " if hidden else ""
                print(f"      {font:<35} {str(size or ''):>6}  {flag}[{path}] {text}")
        for n in notes:
            print(f"   ! {n}")

    if args.summary and not writer:
        print("\nGesamt (PostScript-Name -> Anzahl Dateien):")
        for font, files in sorted(usage.items(), key=lambda x: (-len(x[1]), x[0])):
            print(f"  {len(files):>4}  {font}")


if __name__ == "__main__":
    main()
