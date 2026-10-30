#!/usr/bin/env python3
"""
Effets sonores de la pub, fabriqués par calcul (aucun fichier externe, donc aucun droit d'auteur).

Types disponibles (dans config.json > "sfx") :
  whoosh   souffle qui passe (transitions)          options : dur (s), up (true/false)
  riser    montée de tension qui finit sur "at"      options : dur (s)
  impact   coup grave + traîne lumineuse             options : size (0.5 à 1.5)
  shimmer  scintillement aigu (apparition lumineuse) options : dur (s)
  tick     petit "tic" pour l'apparition d'un texte
  tap      clic doux (toucher sur l'écran)
  click    le « déclic » : claquement net et sec
  glitch   petite saturation numérique

Chaque ligne : {"type": "impact", "at": 11.6, "gain": -3, ...}  (gain en dB, 0 = normal)
Pour "riser", "at" est le moment où la montée se termine (là où tombe l'impact).

Usage direct (pour écouter) :  python sons.py   ->  out/sfx.wav
"""
import json, wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 48000
RNG = np.random.default_rng(7)


def _env(n, a=0.01, r=0.2, shape=2.0):
    t = np.linspace(0, 1, n)
    att = np.clip(t / max(a, 1e-4), 0, 1)
    rel = np.clip((1 - t) / max(r, 1e-4), 0, 1) ** shape
    return att * rel


def _bandsweep(noise, f0, f1, q=1.2):
    """Bruit filtré par une bande dont le centre glisse de f0 à f1 (traitement par blocs)."""
    n, out, blk = len(noise), np.zeros_like(noise), 1024
    zi = None
    for k in range(0, n, blk):
        frac = k / max(1, n - 1)
        fc = f0 * (f1 / f0) ** frac
        bw = fc / q
        lo, hi = max(30, fc - bw / 2), min(SR / 2 - 100, fc + bw / 2)
        b, a = signal.butter(2, [lo, hi], btype="band", fs=SR)
        if zi is None or len(zi) != max(len(a), len(b)) - 1:
            zi = signal.lfilter_zi(b, a) * 0
        out[k:k + blk], zi = signal.lfilter(b, a, noise[k:k + blk], zi=zi)
    return out


def _reverb(x, dur=1.6, wet=0.25):
    n = int(dur * SR)
    t = np.arange(n) / SR
    ir_l = RNG.standard_normal(n) * np.exp(-t * 4.0)
    ir_r = RNG.standard_normal(n) * np.exp(-t * 4.0)
    b, a = signal.butter(1, 6000, fs=SR)
    ir_l, ir_r = signal.lfilter(b, a, ir_l), signal.lfilter(b, a, ir_r)
    ir_l /= np.abs(ir_l).sum() ** 0.5 * 4
    ir_r /= np.abs(ir_r).sum() ** 0.5 * 4
    l = np.pad(signal.fftconvolve(x[:, 0], ir_l), (0, 1))[: len(x) + n]
    r = np.pad(signal.fftconvolve(x[:, 1], ir_r), (0, 1))[: len(x) + n]
    dry = np.vstack([np.pad(x[:, 0], (0, n)), np.pad(x[:, 1], (0, n))]).T
    return dry * (1 - wet) + np.vstack([l, r]).T * wet


def whoosh(dur=0.6, up=True):
    n = int(dur * SR)
    noise = RNG.standard_normal(n)
    f0, f1 = (350, 4200) if up else (4200, 350)
    x = _bandsweep(noise, f0, f1, q=1.4) * _env(n, a=0.55, r=0.45, shape=1.6)
    pan = np.linspace(-0.6, 0.6, n)
    st = np.vstack([x * np.sqrt(0.5 - pan / 2), x * np.sqrt(0.5 + pan / 2)]).T
    return _reverb(st, 0.8, 0.2) * 0.9


def riser(dur=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = _bandsweep(RNG.standard_normal(n), 250, 7000, q=1.0)
    f = 90 * (8 ** (t / dur))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35 + np.sin(2 * np.pi * np.cumsum(f * 1.5) / SR) * 0.15
    env = (t / dur) ** 2.2
    x = (noise * 0.8 + tone) * env
    x[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))
    st = np.vstack([x, np.roll(x, 90)]).T
    return st * 0.8


def impact(size=1.0):
    dur = 1.6 + 0.6 * size
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 34 + 40 * np.exp(-t * 9)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (2.6 / size))
    thump = np.sin(2 * np.pi * 110 * t) * np.exp(-t * 22) * 0.6
    tr = RNG.standard_normal(n) * np.exp(-t * 60)
    b, a = signal.butter(2, 2500, fs=SR)
    tr = signal.lfilter(b, a, tr) * 0.9
    air = _bandsweep(RNG.standard_normal(n), 6000, 2500, q=0.8) * np.exp(-t * 2.2) * 0.25
    x = sub * 1.0 + thump + tr + air
    st = np.vstack([x, x]).T
    return _reverb(st, 2.2, 0.3) * (0.75 + 0.25 * size)


def shimmer(dur=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for f in (2093, 2637, 3136, 4186, 5274):
        x += np.sin(2 * np.pi * f * t + RNG.uniform(0, 6.28)) * (0.5 + 0.5 * np.sin(2 * np.pi * RNG.uniform(5, 11) * t))
    x *= _env(n, a=0.12, r=0.85, shape=2.2) * 0.12
    st = np.vstack([x, np.roll(x, 240)]).T
    return _reverb(st, 1.8, 0.45)


def tick():
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 1650 * t) * np.exp(-t * 70) * 0.35 + RNG.standard_normal(n) * np.exp(-t * 400) * 0.08
    return _reverb(np.vstack([x, x]).T, 0.5, 0.15)


def tap():
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    noise = RNG.standard_normal(n) * np.exp(-t * 300)
    b, a = signal.butter(2, [900, 4000], btype="band", fs=SR)
    x = signal.lfilter(b, a, noise) * 0.5 + np.sin(2 * np.pi * 700 * t) * np.exp(-t * 120) * 0.15
    return np.vstack([x, x]).T


def click():
    """Le « déclic » : claquement net et sec, avec une petite résonance."""
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    snap = RNG.standard_normal(n) * np.exp(-t * 900)
    b, a = signal.butter(2, 2500, btype="high", fs=SR)
    snap = signal.lfilter(b, a, snap) * 0.9
    tone = np.sin(2 * np.pi * 2350 * t) * np.exp(-t * 60) * 0.35 + np.sin(2 * np.pi * 1180 * t) * np.exp(-t * 35) * 0.25
    thump = np.sin(2 * np.pi * 95 * t) * np.exp(-t * 40) * 0.5
    x = snap + tone + thump
    return _reverb(np.vstack([x, x]).T, 0.9, 0.18)


def glitch():
    """Petite saturation numérique (on « bloque »)."""
    n = int(0.22 * SR)
    x = np.zeros(n)
    for k in range(6):
        i0 = int(RNG.uniform(0, 0.18) * SR)
        L = int(RNG.uniform(0.006, 0.03) * SR)
        f = RNG.choice([180, 420, 880, 1760, 3300])
        seg = np.sign(np.sin(2 * np.pi * f * np.arange(L) / SR)) * 0.35 + RNG.standard_normal(L) * 0.2
        x[i0:i0 + L] += seg[: len(x[i0:i0 + L])]
    x = np.round(x * 6) / 6
    st = np.vstack([x, np.roll(x, 90)]).T
    return st * 0.8


SONS = {"whoosh": whoosh, "riser": riser, "impact": impact, "shimmer": shimmer, "tick": tick, "tap": tap,
        "click": click, "glitch": glitch}


def fabriquer(evenements, duree, sortie: Path):
    """Assemble tous les effets sur une piste de `duree` secondes et l'écrit en WAV 48 kHz stéréo."""
    piste = np.zeros((int(duree * SR) + SR * 3, 2))
    for e in evenements:
        opts = {k: v for k, v in e.items() if k not in ("type", "at", "gain")}
        son = SONS[e["type"]](**opts)
        debut = e["at"] - (opts.get("dur", 1.6) if e["type"] == "riser" else 0)
        if e["type"] == "whoosh":
            debut -= opts.get("dur", 0.6) * 0.55          # le souffle culmine sur "at"
        i = int(round(max(0, debut) * SR))
        son = son[: len(piste) - i] * 10 ** (e.get("gain", 0) / 20)
        piste[i:i + len(son)] += son
    piste = piste[: int(duree * SR)]
    fin = int(0.1 * SR)
    piste[-fin:] *= np.linspace(1, 0, fin)[:, None]
    crete = np.abs(piste).max() or 1
    piste = piste / crete * 10 ** (-1.5 / 20)
    with wave.open(str(sortie), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((piste * 32767).astype("<i2").tobytes())
    return sortie


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    cfg = json.loads((root / "config.json").read_text(encoding="utf-8"))
    d = cfg["duration"]
    (root / "out").mkdir(exist_ok=True)
    print(fabriquer(cfg.get("sfx", []), d, root / "out" / "sfx.wav"))
