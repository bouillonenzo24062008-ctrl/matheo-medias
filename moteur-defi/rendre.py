#!/usr/bin/env python3
"""
Rend la pub « Le défi » (8 s) en MP4 (1080 x 1920, 30 i/s, H.264).

Le montage est décrit dans config.json et animé par index.html.
Ce script ouvre index.html dans un navigateur invisible (Chromium via Playwright),
calcule chaque image une par une, puis les envoie à ffmpeg pour fabriquer le MP4.

Usages :
  python rendre.py                         -> out/matheo-plus-defi.mp4 (image seule, sans son)
                                              + out/matheo-plus-defi-son.mp4 (musique de musique.py,
                                              effets sonores, et voix off si config.json > voice en contient)
  python rendre.py --audio-seulement       -> refait seulement le son sur la vidéo déjà rendue (quelques secondes)
  python rendre.py --musique son.mp3       -> ajoute une musique (baissée automatiquement sous la voix)
  python rendre.py --musique son.mp3 --volume-musique 0.6 --debut-musique 12.5
  python rendre.py --sans-effets           -> sans les effets sonores
  python rendre.py --sans-musique          -> sans la musique composée (pour mettre un son TikTok)
  python rendre.py --sans-voix             -> sans la voix off
  python rendre.py --apercu                -> out/apercu.png (planche de 16 images)
  python rendre.py --images 0,1.3,8.9       -> out/images/t_00.00.png ... (contrôle rapide)
  python rendre.py --navigateur            -> aperçu animé dans ton navigateur

Pré-requis :  ffmpeg  +  pip install numpy scipy playwright pillow  +  python -m playwright install chromium
"""
import argparse, asyncio, functools, http.server, json, subprocess, sys, threading, time, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
W, H, FPS = CFG["output"]["width"], CFG["output"]["height"], CFG["output"]["fps"]
OUT = ROOT / "out"


def serveur():
    """Petit serveur web local (le navigateur ne peut pas lire config.json sans lui)."""
    class Silencieux(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0),
                                          functools.partial(Silencieux, directory=str(ROOT)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/index.html"


async def ouvrir(p, url):
    navigateur = await p.chromium.launch()
    page = await navigateur.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
    erreurs = []
    page.on("pageerror", lambda e: erreurs.append(str(e)))
    page.on("console", lambda m: erreurs.append(m.text) if m.type == "error" else None)
    await page.goto(url + "?rendu=1", wait_until="networkidle")
    try:
        await page.wait_for_function("window.__ready === true", timeout=30000)
    except Exception:
        sys.exit("La page ne s'est pas chargée. Erreurs : " + " | ".join(erreurs or ["aucune"]) +
                 "\nVérifie config.json (virgules, guillemets).")
    return navigateur, page, erreurs


async def image(page, t):
    await page.evaluate("t => window.__render(t)", t)
    return await page.screenshot(clip={"x": 0, "y": 0, "width": W, "height": H}, type="png")


async def rendre_video(url, sortie):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        nav, page, erreurs = await ouvrir(p, url)
        duree = await page.evaluate("window.__duration")
        n = int(round(duree * FPS))
        print(f"Durée {duree:.2f} s  ->  {n} images")
        ff = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "png", "-i", "-",
             "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high", "-level", "4.2",
             "-pix_fmt", "yuv420p", "-bsf:v", "h264_metadata=sample_aspect_ratio=1/1",
             "-r", str(FPS), "-movflags", "+faststart", str(sortie)], stdin=subprocess.PIPE)
        t0 = time.time()
        for i in range(n):
            ff.stdin.write(await image(page, i / FPS))
            if i % FPS == 0 or i == n - 1:
                ecoule = time.time() - t0
                reste = ecoule / (i + 1) * (n - i - 1)
                print(f"\r  image {i + 1}/{n}   ~{reste:4.0f} s restantes ", end="", flush=True)
        ff.stdin.close()
        ff.wait()
        print()
        await nav.close()
        if erreurs:
            print("Avertissements de la page :", *erreurs, sep="\n  ")
        return duree


async def rendre_images(url, temps, dossier):
    from playwright.async_api import async_playwright
    dossier.mkdir(parents=True, exist_ok=True)
    chemins = []
    async with async_playwright() as p:
        nav, page, _ = await ouvrir(p, url)
        duree = await page.evaluate("window.__duration")
        for t in temps:
            t = min(max(0.0, t), duree - 1 / FPS)
            c = dossier / f"t_{t:05.2f}.png"
            c.write_bytes(await image(page, t))
            chemins.append((t, c))
        await nav.close()
    return chemins, duree


def planche(chemins, sortie, colonnes=8):
    from PIL import Image, ImageDraw, ImageFont
    lw, lh = 270, 480
    lignes = (len(chemins) + colonnes - 1) // colonnes
    feuille = Image.new("RGB", (colonnes * (lw + 12) + 12, lignes * (lh + 52) + 12), (6, 10, 29))
    d = ImageDraw.Draw(feuille)
    try:
        police = ImageFont.truetype(str(ROOT / "assets/fonts/InterDisplay-SemiBold.otf"), 26)
    except Exception:
        police = ImageFont.load_default()
    for k, (t, c) in enumerate(chemins):
        x, y = 12 + (k % colonnes) * (lw + 12), 12 + (k // colonnes) * (lh + 52)
        feuille.paste(Image.open(c).convert("RGB").resize((lw, lh), Image.LANCZOS), (x, y))
        d.text((x + 4, y + lh + 10), f"{t:5.1f} s", fill=(201, 212, 245), font=police)
    feuille.save(sortie)


def duree_parole(fichier: Path, vitesse: float = 1.0) -> float:
    """Durée de la voix une fois le silence de début et de fin retiré (pour les sous-titres)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(fichier), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                       capture_output=True, check=True).stdout
    import array
    x = array.array("h", r)
    pas = 160
    nrj = [max(abs(v) for v in x[i:i + pas]) for i in range(0, len(x) - pas, pas)]
    seuil = max(nrj) * 0.02
    actifs = [i for i, v in enumerate(nrj) if v > seuil]
    return (actifs[-1] - actifs[0] + 1) * pas / 16000 / vitesse if actifs else 0.0


def ecrire_srt(lignes, sortie: Path):
    def tc(t):
        ms = int(round(t * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    blocs = []
    for k, l in enumerate(lignes, 1):
        fin = l["at"] + duree_parole(ROOT / l["file"], l.get("speed", 1.0)) + 0.15
        blocs.append(f"{k}\n{tc(l['at'])} --> {tc(fin)}\n{l.get('text', '')}\n")
    sortie.write_text("\n".join(blocs), encoding="utf-8")


def niveau_voix(fichier: Path, cible: float) -> float:
    """Écart (dB) entre le volume perçu d'une phrase et la cible, borné à ±12 dB."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(fichier), "-af", "loudnorm=print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    try:
        mesure = float(json.loads(r[r.rindex("{"):r.rindex("}") + 1])["input_i"])
    except Exception:
        return 0.0
    return max(-12.0, min(12.0, cible - mesure))


def mixer_audio(video, sortie, duree, voix, musique=None, vol_musique=None, debut_musique=0.0, sfx=None, fondu=1.5):
    """Assemble le son : effets (sfx), voix off placées à leur instant, musique éventuelle
    (baissée automatiquement quand la voix parle). Avec une voix : normalisé à -14 LUFS
    (niveau TikTok/Reels). Effets seuls : laissés à leur niveau (crête à -1,5 dB)."""
    entrees, filtres, bus = ["-i", str(video)], [], []
    fin = f"apad=whole_dur={duree:.3f},atrim=0:{duree:.3f}"
    lignes = voix.get("lines", []) if voix else []
    n = 1
    for k, l in enumerate(lignes):
        f = ROOT / l["file"]
        if not f.exists():
            sys.exit(f"Fichier voix introuvable : {f}")
        entrees += ["-i", str(f)]
        vitesse = l.get("speed", 1.0)
        tempo = f"atempo={vitesse}," if vitesse != 1.0 else ""
        # chaque phrase est ramenée au même niveau (ElevenLabs varie d'une génération à l'autre)
        gain = l.get("gain", niveau_voix(f, voix.get("niveau", -16.0)) if voix.get("niveler", True) else 0.0)
        filtres.append(f"[{n}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
                       f"silenceremove=start_periods=1:start_threshold=-45dB,asetpts=N/SR/TB,{tempo}"
                       f"volume={gain:.2f}dB,adelay={int(round(l['at'] * 1000))}:all=1[v{k}]")
        n += 1
    # La voix sert aussi de « déclencheur » pour baisser la musique et les effets quand elle parle
    duck_m = bool(musique and lignes)
    duck_s = bool(sfx and lignes and voix.get("duckSfx", True))
    if lignes:
        filtres.append("".join(f"[v{k}]" for k in range(len(lignes))) +
                       f"amix=inputs={len(lignes)}:normalize=0:duration=longest,highpass=f=70,"
                       f"volume={voix.get('volume', 1.0)},aresample=48000:async=1:first_pts=0,{fin}[voix]")
        cles = (["vm"] if duck_m else []) + (["vs"] if duck_s else [])
        if cles:
            filtres.append(f"[voix]asplit={1 + len(cles)}[va]" + "".join(f"[{c}]" for c in cles))
            bus.append("va")
        else:
            bus.append("voix")
    if musique:
        entrees += ["-i", str(musique)]
        vm = vol_musique if vol_musique is not None else (0.35 if lignes else 0.8)
        filtres.append(f"[{n}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=start={debut_musique},"
                       f"asetpts=PTS-STARTPTS,{fin},afade=t=in:st=0:d=0.3,"
                       f"afade=t=out:st={max(0, duree - fondu):.3f}:d={fondu},volume={vm}[mus]")
        n += 1
        if duck_m:
            filtres.append("[mus][vm]sidechaincompress=threshold=0.03:ratio=5:attack=15:release=350[musb]")
            bus.append("musb")
        else:
            bus.append("mus")
    if sfx:
        entrees += ["-i", str(sfx)]
        filtres.append(f"[{n}:a]aformat=sample_rates=48000:channel_layouts=stereo,"
                       f"volume={CFG.get('sfxVolume', 1.0)},{fin}[sfx]")
        if duck_s:
            # baisse douce (environ -6 dB) des effets sous la voix, remontée rapide pour garder les impacts
            filtres.append("[sfx][vs]sidechaincompress=threshold=0.02:ratio=2:knee=4:attack=10:release=160[sfxd]")
            bus.append("sfxd")
        else:
            bus.append("sfx")
    if not bus:
        return False
    filtres.append("".join(f"[{x}]" for x in bus) + (f"amix=inputs={len(bus)}:normalize=0:duration=first[mix]"
                                                     if len(bus) > 1 else "anull[mix]"))
    graphe = ";".join(filtres)
    if lignes or musique:
        # 1er passage : mesure du volume ; 2e passage : normalisation précise
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-y", *entrees, "-filter_complex",
                            graphe + ";[mix]loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json[o]",
                            "-map", "[o]", "-f", "null", "-"], capture_output=True, text=True)
        txt = r.stderr
        mesure = json.loads(txt[txt.rindex("{"):txt.rindex("}") + 1])
        norm = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={mesure['input_i']}:measured_TP={mesure['input_tp']}:"
                f"measured_LRA={mesure['input_lra']}:measured_thresh={mesure['input_thresh']}:"
                f"offset={mesure['target_offset']}:linear=true,aresample=48000,apad")
    else:
        norm = "alimiter=limit=0.84:level=false,aresample=48000,apad"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *entrees, "-filter_complex", graphe + f";[mix]{norm}[o]",
                    "-map", "0:v", "-map", "[o]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-t", f"{duree:.3f}", "-movflags", "+faststart", str(sortie)], check=True)
    return True


def main():
    ap = argparse.ArgumentParser(description="Rendu de la pub Mathéo")
    ap.add_argument("--sortie", default=str(OUT / "matheo-plus-defi.mp4"), help="fichier MP4 produit (image seule)")
    ap.add_argument("--musique", help="fichier audio à ajouter (mp3, wav, m4a…)")
    ap.add_argument("--volume-musique", type=float, default=None, help="0.35 par défaut sous la voix")
    ap.add_argument("--debut-musique", type=float, default=0.0, help="démarrer la musique à cette seconde")
    ap.add_argument("--apercu", action="store_true", help="planche d'images out/apercu.png")
    ap.add_argument("--images", help="liste de temps en secondes, ex. 3.2,10,24.5")
    ap.add_argument("--navigateur", action="store_true", help="aperçu animé dans le navigateur")
    ap.add_argument("--audio-seulement", action="store_true", help="refait le son sans recalculer l'image")
    ap.add_argument("--sans-voix", action="store_true", help="ignore les voix de config.json")
    ap.add_argument("--sans-effets", action="store_true", help="ignore les effets sonores de config.json")
    ap.add_argument("--sans-musique", action="store_true", help="sans la musique composée par musique.py")
    a = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    srv, url = serveur()

    if a.navigateur:
        print("Aperçu :", url, "\n(Ctrl+C pour arrêter)")
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return

    if a.images or a.apercu:
        if a.images:
            temps = [float(x) for x in a.images.split(",")]
        else:
            tl = CFG["timeline"]; et = [t for _, t in tl["etapes"]]; tg, tm = et[-1], tl["marque"]
            milieu = [round(t + 0.32, 2) for t in et[1:-1]][:7]          # chaque étape, une fois sa transition finie
            temps = [0.0, 0.6] + milieu + [round(tg + 0.3, 2), round(tg + 0.7, 2), round(tm + 0.6, 2),
                     round(tm + 1.3, 2), round(tl["final"] + 0.3, 2), round(tl["cta"] + 0.5, 2), round(CFG["duration"] - 0.05, 2)]
            temps = temps[:16]
        chemins, _ = asyncio.run(rendre_images(url, temps, OUT / "images"))
        if a.apercu:
            planche(chemins, OUT / "apercu.png")
            print("Aperçu :", OUT / "apercu.png")
        else:
            print("Images :", *[str(c) for _, c in chemins], sep="\n  ")
        return

    sortie = Path(a.sortie)
    if a.audio_seulement:
        if not sortie.exists():
            sys.exit(f"{sortie} n'existe pas encore : lance d'abord  python rendre.py")
        duree = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                      str(sortie)], capture_output=True, text=True).stdout)
    else:
        duree = asyncio.run(rendre_video(url, sortie))
        print("Vidéo (image seule) :", sortie)
    voix = None if a.sans_voix else CFG.get("voice")
    sfx = None
    if CFG.get("sfx") and not a.sans_effets:
        import sons
        sfx = sons.fabriquer(CFG["sfx"], duree, OUT / "sfx.wav")
    avec_son = sortie.with_name(sortie.stem + "-son.mp4")
    musique, vol = (Path(a.musique) if a.musique else None), a.volume_musique
    if musique is None and CFG.get("music") and not a.sans_musique:
        musique = ROOT / CFG["music"]["file"]
        subprocess.run([sys.executable, str(ROOT / "musique.py")], check=True, capture_output=True)
        if vol is None:
            vol = CFG["music"].get("volume", 0.8)
    # la musique composée finit déjà nettement sur l'accord final : pas de long fondu
    fondu = 1.5 if a.musique else 0.05
    if mixer_audio(sortie, avec_son, duree, voix, musique, vol, a.debut_musique, sfx, fondu):
        print("Vidéo avec son :", avec_son)
        if voix and voix.get("lines"):
            ecrire_srt(voix["lines"], avec_son.with_suffix(".srt"))
            print("Sous-titres :", avec_son.with_suffix(".srt"))


if __name__ == "__main__":
    main()
