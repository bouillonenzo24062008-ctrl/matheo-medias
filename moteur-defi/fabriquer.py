#!/usr/bin/env python3
"""
Fabrique une vidéo « Le défi » (8 à 9 s) à partir d'un fichier defis/<nom>.json.

  python fabriquer.py defis/exponentielle.json             vérifie le calcul, prépare, rend la vidéo
  python fabriquer.py defis/exponentielle.json --glyphes   planche out/glyphes.png : le numéro de chaque
                                                           glyphe de chaque étape, pour écrire les clés
  python fabriquer.py defis/exponentielle.json --apercu    seulement la planche d'aperçu out/apercu.png

Le fichier du défi (voir defis/exponentielle.json, l'exemple complet) :
  etapes      liste des formules (LaTeX matplotlib, entre $...$) ; la DERNIÈRE est la réponse encadrée.
              Chaque formule a des « cles » : une par glyphe, dans l'ordre de la planche --glyphes,
              puis une par trait (barre de fraction, racine). Même clé d'une étape à la suivante =
              même terme : il glisse de sa place à la nouvelle. Clés uniques dans une étape.
  lettres_bleues   lettres affichées en bleu (la nouvelle inconnue, par exemple ["X"]).
  encadres    facultatif : {"etape": i, "groupes": [[clés], ...], "vers": [clé, ...]} : des cadres
              entourent ces groupes à l'étape i puis glissent sur les clés « vers » de l'étape i+1.
  barre       facultatif : {"etape": i, "cles": [...], "note": {"tex", "cles"}} : la solution
              impossible est barrée, avec une petite note dessous (« eˣ > 0 »).
  etiquettes  facultatif : [{"depuis": i, "tex", "cles"}, ...] : petite formule au-dessus
              (« X = eˣ »), qui se transforme en la suivante à l'étape « depuis » de celle-ci.
  verification     OBLIGATOIRE, le calcul est contrôlé numériquement avant tout rendu :
              {"type": "equation", "equation": "exp(2*x) - exp(x) - 2", "domaine": [-10, 10],
               "solutions": ["log(2)"]}          toutes les solutions du domaine, et elles seules
              {"type": "valeur", "expression": "(exp(x) - 1)/x", "point": 0, "valeur": "1"}
                                                  limite en un point (approchée des deux côtés)
              {"type": "valeur", "expression": "integrale(lambda t: t*exp(t), 0, 1)", "valeur": "1"}
  texte       facultatif : les deux lignes du titre (par défaut « TU SAURAIS » / « RÉSOUDRE **ÇA** ? »).

Sorties : out/<nom>.mp4 (vidéo finale avec son), out/<nom>-couverture.jpg, out/apercu.png.
"""
import argparse, json, math, shutil, subprocess, sys
from pathlib import Path

import matplotlib
matplotlib.rcParams["mathtext.fontset"] = "cm"
from matplotlib.textpath import TextToPath
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MPath

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
LARGEUR_MAX = 960          # au-delà (police 100), la formule devient trop petite une fois mise à l'échelle


# ------------------------------------------------------------------ vérification du calcul
def integrale(f, a, b, n=20000):
    h = (b - a) / n
    return h / 3 * (f(a) + f(b) + sum((4 if i % 2 else 2) * f(a + i * h) for i in range(1, n)))


ESPACE = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
ESPACE.update(ln=math.log, integrale=integrale, abs=abs)


def evaluer(expr, **v):
    return eval(expr, {"__builtins__": {}}, {**ESPACE, **v})


def racines(f, a, b, n=200000):
    """Toutes les racines de f sur [a, b] : changements de signe et minimums qui touchent 0."""
    xs = [a + (b - a) * i / n for i in range(n + 1)]
    ys = []
    for x in xs:
        try:
            y = f(x)
            ys.append(y if math.isfinite(y) else None)
        except (ValueError, ZeroDivisionError, OverflowError):
            ys.append(None)
    out = []
    for i in range(n):
        y0, y1 = ys[i], ys[i + 1]
        if y0 is None or y1 is None:
            continue
        if y0 == 0 or y0 * y1 < 0:
            lo, hi = xs[i], xs[i + 1]
            for _ in range(80):
                m = (lo + hi) / 2
                if f(lo) * f(m) <= 0:
                    hi = m
                else:
                    lo = m
            out.append((lo + hi) / 2)
        elif 0 < i and ys[i - 1] is not None and abs(y0) < 1e-9 and abs(y0) <= abs(ys[i - 1]) and abs(y0) <= abs(y1):
            out.append(xs[i])                                  # racine double (contact sans changement de signe)
    fusion = []
    for r in out:
        if not fusion or abs(r - fusion[-1]) > 1e-6:
            fusion.append(r)
    return fusion


def verifier(v):
    if v["type"] == "equation":
        f = lambda x: evaluer(v["equation"], x=x)
        a, b = v.get("domaine", [-20, 20])
        trouve = racines(f, a, b)
        attendu = sorted(evaluer(s) for s in v["solutions"])
        ok = len(trouve) == len(attendu) and all(abs(p - q) < 1e-6 for p, q in zip(trouve, attendu))
        print(f"Équation {v['equation']} = 0 sur [{a}, {b}] : solutions trouvées {[round(r, 6) for r in trouve]}, "
              f"annoncées {[round(r, 6) for r in attendu]}")
    elif v["type"] == "valeur":
        attendu = evaluer(v["valeur"])
        if "point" in v:
            p = v["point"]
            vals = [evaluer(v["expression"], x=p + s * h) for h in (1e-4, 1e-5) for s in (-1, 1)]
            ok = all(abs(y - attendu) < 1e-3 for y in vals)
            print(f"Limite de {v['expression']} en {p} : {[round(y, 6) for y in vals]} ; annoncée {attendu}")
        else:
            y = evaluer(v["expression"])
            ok = abs(y - attendu) < 1e-6
            print(f"{v['expression']} = {y:.8f} ; annoncée {attendu}")
    else:
        sys.exit(f"type de vérification inconnu : {v['type']}")
    if not ok:
        sys.exit("CALCUL FAUX : la vidéo n'est pas fabriquée. Corrige le défi.")
    print("Calcul vérifié.")


# ------------------------------------------------------------------ formules -> glyphes
def chemin_svg(verts, codes, dx=0.0, dy=0.0):
    out, i, n = [], 0, len(codes)
    f = lambda v: f"{v[0] - dx:.1f} {v[1] - dy:.1f}"
    while i < n:
        c = codes[i]
        if c == MPath.MOVETO:
            out.append("M" + f(verts[i])); i += 1
        elif c == MPath.LINETO:
            out.append("L" + f(verts[i])); i += 1
        elif c == MPath.CURVE3:
            out.append("Q" + f(verts[i]) + " " + f(verts[i + 1])); i += 2
        elif c == MPath.CURVE4:
            out.append("C" + f(verts[i]) + " " + f(verts[i + 1]) + " " + f(verts[i + 2])); i += 3
        elif c == MPath.CLOSEPOLY:
            out.append("Z"); i += 1
        else:
            i += 1
    return "".join(out)


TTP, PROP = TextToPath(), FontProperties(size=100)


def glyphes_de(formule):
    """[(gid, x, y, s)] glyphes puis traits, et les chemins/boîtes de chaque gid."""
    infos, carte, rects = TTP.get_glyphs_mathtext(PROP, formule)
    chemins, boites, liste = {}, {}, list(infos)
    for gid, (verts, codes) in carte.items():
        if len(verts):
            chemins[gid] = chemin_svg(verts, codes)
            xs, ys = [v[0] for v in verts], [v[1] for v in verts]
            boites[gid] = [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)]
    for verts, codes in rects:                                 # traits : rectangle en coordonnées absolues
        pts = [v for v, c in zip(verts, codes) if c != MPath.CLOSEPOLY][:4]
        x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
        x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
        gid = f"R{x1 - x0:.1f}x{y1 - y0:.1f}"
        chemins[gid] = f"M0 0L{x1 - x0:.1f} 0L{x1 - x0:.1f} {y1 - y0:.1f}L0 {y1 - y0:.1f}Z"
        boites[gid] = [0, 0, round(x1 - x0, 1), round(y1 - y0, 1)]
        liste.append((gid, x0, y0, 1.0))
    return liste, chemins, boites


def formules(defi):
    """Toutes les formules du défi, nommées : E0..En (étapes), T0.. (étiquettes), N (note)."""
    f = {f"E{i}": e for i, e in enumerate(defi["etapes"])}
    for i, e in enumerate(defi.get("etiquettes", [])):
        f[f"T{i}"] = e
    if defi.get("barre", {}).get("note"):
        f["N"] = defi["barre"]["note"]
    return f


def preparer(defi):
    chemins, boites, etapes = {}, {}, {}
    for nom, e in formules(defi).items():
        liste, ch, bo = glyphes_de(e["tex"])
        chemins.update(ch); boites.update(bo)
        cles = e["cles"]
        assert len(liste) == len(cles), (f"{nom} ({e['tex']}) : {len(liste)} glyphes et traits pour {len(cles)} clés. "
                                         "Lance  --glyphes  pour voir la numérotation.")
        assert len(set(cles)) == len(cles), f"{nom} : clés en double {cles}"
        gl = [{"g": g, "k": k, "x": round(x, 2), "y": round(y, 2), "s": round(s, 4)} for (g, x, y, s), k in zip(liste, cles)]
        x0 = min(g["x"] + boites[g["g"]][0] * g["s"] for g in gl)
        x1 = max(g["x"] + boites[g["g"]][2] * g["s"] for g in gl)
        if nom.startswith("E") and x1 - x0 > LARGEUR_MAX:
            print(f"ATTENTION {nom} : {x1 - x0:.0f} px de large (max conseillé {LARGEUR_MAX}) : elle sera petite à l'écran.")
        etapes[nom] = {"tex": e["tex"], "x0": round(x0, 1), "x1": round(x1, 1), "glyphes": gl}
    bleus = []
    for lettre in defi.get("lettres_bleues", []):
        bleus += [g for g, *_ in glyphes_de(f"${lettre}$")[0]]
    n = len(defi["etapes"])
    data = {"chemins": chemins, "boites": boites, "etapes": etapes, "bleus": bleus,
            "reponse": f"E{n - 1}", "ordre": [f"E{i}" for i in range(n)]}
    if "encadres" in defi:
        c = defi["encadres"]
        data["encadres"] = {"etape": f"E{c['etape']}", "suivante": f"E{c['etape'] + 1}", "groupes": c["groupes"], "vers": c["vers"]}
    if "barre" in defi:
        data["barre"] = {"etape": f"E{defi['barre']['etape']}", "cles": defi["barre"]["cles"], "note": "N" in etapes}
    data["etiquettes"] = [{"nom": f"T{i}", "depuis": f"E{e['depuis']}"} for i, e in enumerate(defi.get("etiquettes", []))]
    (ROOT / "assets" / "defi.json").write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    return data


# ------------------------------------------------------------------ montage, sons, lumières
def montage(defi):
    cfg = json.loads((ROOT / "config-base.json").read_text(encoding="utf-8"))
    n = len(defi["etapes"])
    assert 3 <= n <= 8, "il faut entre 3 et 8 étapes (la dernière est la réponse)"
    b = defi.get("barre", {}).get("etape")
    ts = [0.0] + [round(1.0 + 0.4 * i, 2) for i in range(n - 2)]            # les étapes s'accélèrent : toutes les 0,4 s
    tg = round(ts[-1] + (0.8 if b == n - 2 else 0.6), 2)                    # la réponse (laisse lire la solution barrée)
    tg = max(tg, 2.6)
    ts.append(tg)
    tl = {"etapes": [[f"E{i}", t] for i, t in enumerate(ts)],
          "barre": round(ts[b] + 0.25, 2) if b is not None else None,
          "roulement": b, "lumiere": round(tg + 0.8, 2), "marque": round(tg + 1.0, 2)}
    tm = tl["marque"]
    tl.update(mots=[round(tm + 0.5, 2), round(tm + 1.0, 2)], final=round(tm + 2.0, 2), cta=round(tm + 2.4, 2), fin=round(tm + 3.5, 2))
    cfg["timeline"] = tl
    cfg["duration"] = round(tl["fin"] + 0.5, 2)
    if defi.get("texte"):
        cfg["texts"]["defi"] = defi["texte"]
    tf, tc, fin = tl["final"], tl["cta"], tl["fin"]
    sfx = [{"type": "impact", "at": 0.0, "size": 1.5, "gain": 3}, {"type": "whoosh", "at": 0.08, "dur": 0.35, "gain": -4}]
    for t in ts[1:-1]:
        sfx += [{"type": "whoosh", "at": round(t + 0.07, 2), "dur": 0.28, "gain": -11}, {"type": "tick", "at": round(t + 0.14, 2), "gain": -9}]
    if tl["barre"] is not None:
        sfx.append({"type": "click", "at": round(tl["barre"] + 0.02, 2), "gain": -8})
    sfx += [{"type": "riser", "at": tg, "dur": 1.6, "gain": -12}, {"type": "impact", "at": tg, "size": 0.6, "gain": -7},
            {"type": "shimmer", "at": round(tg + 0.02, 2), "dur": 0.9, "gain": -6},
            {"type": "riser", "at": tm, "dur": 0.9, "gain": -6}, {"type": "impact", "at": tm, "size": 1.5, "gain": 0},
            {"type": "shimmer", "at": round(tm + 0.05, 2), "dur": 1.4, "gain": -6}]
    sfx += [{"type": "tick", "at": m, "gain": -8} for m in tl["mots"]]
    sfx += [{"type": "whoosh", "at": tf, "dur": 0.4, "gain": -9}, {"type": "tick", "at": round(tf + 0.1, 2), "gain": -8},
            {"type": "tick", "at": round(tc + 0.05, 2), "gain": -6}, {"type": "tick", "at": round(tc + 0.25, 2), "gain": -8},
            {"type": "impact", "at": fin, "size": 0.8, "gain": -5}, {"type": "shimmer", "at": fin, "dur": 0.45, "gain": -9}]
    cfg["sfx"] = sfx
    cfg["flashes"] = [[0.02, 0.5, 0.02, 0.3], [tg, 0.3, 0.03, 0.3], [tm, 0.95, 0.05, 0.6], [fin, 0.25, 0.03, 0.35]]
    cfg["shakes"] = [[0.02, 20]] + [[t, 4] for t in ts[1:-1]] + [[tg, 9], [tm, 15]] + [[m, 5] for m in tl["mots"]] + [[fin, 6]]
    (ROOT / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Montage : étapes " + ", ".join(f"{t:g}" for t in ts) + f" s ; marque {tm:g} s ; durée {cfg['duration']:g} s")
    return cfg


def planche_glyphes(defi):
    """Planche : chaque formule avec le numéro de chaque glyphe (puis des traits) sous lui."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    F = formules(defi)
    fig, axes = plt.subplots(len(F), 1, figsize=(14, 2.2 * len(F)))
    axes = [axes] if len(F) == 1 else axes
    for ax, (nom, e) in zip(axes, F.items()):
        liste, ch, bo = glyphes_de(e["tex"])
        for i, (g, x, y, s) in enumerate(liste):
            from matplotlib import transforms
            path = parse_svg(ch[g])
            path = path.transformed(transforms.Affine2D().scale(s).translate(x, y))
            ax.add_patch(PathPatch(path, color="black"))
            b = bo[g]
            cx = x + (b[0] + b[2]) / 2 * s
            ax.text(cx, -45, str(i), ha="center", fontsize=9, color="crimson")
            k = e["cles"][i] if i < len(e["cles"]) else "?"
            ax.text(cx, -70, k, ha="center", fontsize=7, color="royalblue")
        ax.set_xlim(-20, max(900, max(x for _, x, *_ in liste) + 120)); ax.set_ylim(-90, 140)
        ax.set_aspect("equal"); ax.axis("off")
        ax.set_title(f"{nom} : {e['tex']}   ({len(liste)} glyphes et traits, {len(e['cles'])} clés)", fontsize=9, loc="left")
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / "glyphes.png", dpi=90, bbox_inches="tight")
    print("Planche :", OUT / "glyphes.png", "(rouge = numéro, bleu = clé donnée)")


def parse_svg(d):
    import re
    verts, codes = [], []
    for cmd, nums in re.findall(r"([MLQCZ])([^MLQCZ]*)", d):
        v = [float(n) for n in nums.split()]
        pts = list(zip(v[0::2], v[1::2]))
        if cmd == "M": verts += pts; codes += [MPath.MOVETO]
        elif cmd == "L": verts += pts; codes += [MPath.LINETO]
        elif cmd == "Q": verts += pts; codes += [MPath.CURVE3] * 2
        elif cmd == "C": verts += pts; codes += [MPath.CURVE4] * 3
        elif cmd == "Z": verts += [(0, 0)]; codes += [MPath.CLOSEPOLY]
    return MPath(verts, codes)


def main():
    ap = argparse.ArgumentParser(description="Fabrique une vidéo « Le défi » à partir de defis/<nom>.json")
    ap.add_argument("defi")
    ap.add_argument("--glyphes", action="store_true", help="planche des glyphes numérotés, rien d'autre")
    ap.add_argument("--apercu", action="store_true", help="prépare et fait seulement la planche d'aperçu")
    a = ap.parse_args()
    chemin = Path(a.defi)
    defi = json.loads(chemin.read_text(encoding="utf-8"))
    nom = chemin.stem
    if a.glyphes:
        return planche_glyphes(defi)
    verifier(defi["verification"])
    preparer(defi)
    cfg = montage(defi)
    py = sys.executable
    subprocess.run([py, "rendre.py", "--apercu"], cwd=ROOT, check=True)
    if a.apercu:
        return
    subprocess.run([py, "verifier.py"], cwd=ROOT, check=True)
    subprocess.run([py, "rendre.py"], cwd=ROOT, check=True)
    final = OUT / f"{nom}.mp4"
    shutil.copy(OUT / "matheo-plus-defi-son.mp4", final)
    t_couv = cfg["timeline"]["etapes"][1][1] - 0.1                  # titre en grand + équation : la couverture
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t_couv}", "-i", str(final), "-frames:v", "1", "-q:v", "2",
                    str(OUT / f"{nom}-couverture.jpg")], check=True)
    taille = final.stat().st_size / 1e6
    print(f"\nVIDÉO : {final} ({taille:.1f} Mo{' : TROP LOURDE pour TikTok (20 Mo max)' if taille > 20 else ''})")
    print("COUVERTURE :", OUT / f"{nom}-couverture.jpg")


if __name__ == "__main__":
    main()
