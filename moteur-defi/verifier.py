#!/usr/bin/env python3
"""
Contrôles automatiques de la pub (sans fabriquer la vidéo) :
  - chaque texte important : pendant combien de temps il est entièrement lisible (opacité ≥ 90 %) ;
  - s'il sort de l'image (texte coupé) ;
  - s'il entre dans les zones masquées par l'interface TikTok pendant qu'il est lisible.

Usage :  python verifier.py
"""
import asyncio, json
from pathlib import Path

import rendre

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
FPS = CFG["output"]["fps"]
# zone sûre TikTok sur une image 1080 x 1920 : ni sous les onglets du haut, ni sous la colonne
# de boutons à droite (120 px), ni sous la légende et la musique en bas
ZONE = {"gauche": 60, "droite": 960, "haut": 150, "bas": 1440}

ELEMENTS = {
    "q1": "TU SAURAIS", "q2": "RÉSOUDRE ÇA ?", "eqMain": "équation (étapes)", "eqTag": "étiquette (au-dessus)", "eqNote": "note (sous la barre)",
    "fLogo": "logo", "f1": "MATHÉO", "f2": "PLUS", "sl1": "COMPRENDS.", "sl2": "PROGRESSE.",
    "fDispo": "DISPONIBLE MAINTENANT", "cta": "DÉCOUVRE MATHÉO PLUS", "url": "avecmatheo.fr",
}

JS = """ids => ids.map(id => {
  let el = document.getElementById(id); const box = el.tagName === 'svg' ? el : (el.querySelector('.fit') || el);
  let o = 1, vis = true;
  for (let e = box; e && e.id !== 'stage'; e = e.parentElement) {
    const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden') { vis = false; break; }
    o *= parseFloat(cs.opacity);
  }
  // textes animés lettre par lettre : lisible quand la dernière lettre l'est
  const lettres = [...box.querySelectorAll('span')].filter(s => s.style.opacity !== '');
  if (lettres.length) o *= Math.min(...lettres.map(s => parseFloat(s.style.opacity)));
  let r = box.getBoundingClientRect();
  if (box.tagName === 'svg') {          // formules : on mesure seulement les glyphes visibles
    const ps = [...box.querySelectorAll('path')].filter(p => p.style.display !== 'none' && parseFloat(p.style.opacity || 1) > .5);
    if (!ps.length) return [id, 0, 0, 0, 0, 0];
    const rs = ps.map(p => p.getBoundingClientRect());
    r = {left: Math.min(...rs.map(q => q.left)), top: Math.min(...rs.map(q => q.top)), right: Math.max(...rs.map(q => q.right)), bottom: Math.max(...rs.map(q => q.bottom))};
  }
  return [id, vis ? o : 0, r.left, r.top, r.right, r.bottom];
})"""


async def main():
    from playwright.async_api import async_playwright
    srv, url = rendre.serveur()
    async with async_playwright() as p:
        nav, page, erreurs = await rendre.ouvrir(p, url)
        duree = await page.evaluate("window.__duration")
        n = int(round(duree * FPS))
        lisible = {k: [] for k in ELEMENTS}
        hors_zone = {k: [] for k in ELEMENTS}
        coupe = {k: [] for k in ELEMENTS}
        for i in range(n):
            t = i / FPS
            await page.evaluate("t => window.__render(t)", t)
            for id_, o, x0, y0, x1, y1 in await page.evaluate(JS, list(ELEMENTS)):
                if o < 0.9:
                    continue
                lisible[id_].append(t)
                if x0 < 0 or x1 > 1080 or y0 < 0 or y1 > 1920:
                    coupe[id_].append(t)
                if x0 < ZONE["gauche"] or x1 > ZONE["droite"] or y0 < ZONE["haut"] or y1 > ZONE["bas"]:
                    hors_zone[id_].append((t, round(x0), round(y0), round(x1), round(y1)))
        dernier = await page.evaluate(JS, list(ELEMENTS))
        await nav.close()
    srv.shutdown()

    print(f"Durée : {duree:.2f} s ({n} images)\n")
    print(f"{'Texte':<30} {'lisible de':>10} {'à':>7} {'durée':>7}   zones TikTok   coupé")
    ok = True
    for k, nom in ELEMENTS.items():
        ts = lisible[k]
        if not ts:
            if k in ("eqTag", "eqNote"):
                print(f"{nom:<30} (absent de ce défi)")
            else:
                print(f"{nom:<30} JAMAIS LISIBLE"); ok = False
            continue
        d = len(ts) / FPS
        hz = f"{len(hors_zone[k])} img" if hors_zone[k] else "ok"
        cp = f"{len(coupe[k])} img" if coupe[k] else "ok"
        print(f"{nom:<30} {ts[0]:>9.2f}s {ts[-1]:>6.2f}s {d:>6.2f}s   {hz:<13}  {cp}")
        if d < 0.4 or coupe[k]:
            ok = False
    print("\nDernière image : " + ", ".join(ELEMENTS[i] for i, o, *_ in dernier if o >= 0.9))
    for k, v in hors_zone.items():
        if v:
            print(f"  {ELEMENTS[k]} hors zone sûre : {v[0]} … {v[-1]}")
    print("\nRÉSULTAT :", "OK" if ok else "À CORRIGER")


if __name__ == "__main__":
    asyncio.run(main())
