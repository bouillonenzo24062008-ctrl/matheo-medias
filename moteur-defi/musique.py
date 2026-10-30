#!/usr/bin/env python3
"""
Musique de la pub « Le défi » (8 s), composée et fabriquée par calcul (aucun échantillon externe,
aucun droit d'auteur : utilisable commercialement sur TikTok, Instagram et Facebook).

120 BPM, ré mineur, calée sur l'animation (instants lus dans config.json > timeline) :
  0 – 1 s      « Tu saurais résoudre ça ? » : impact dès la première image, pulsation grave tendue
  1 – 3 s      la résolution : un accord et une note d'arpège plus aiguë à chaque étape, montée
  3 s          la réponse : accord de cloches lumineux (le « déclic »)
  3 – 4 s      roulement et montée vers la marque
  4 – 7,5 s    Mathéo Plus : grand impact, rythmique complète sous le slogan et l'appel à l'action
  7,5 – 8 s    accord final sec qui s'éteint juste avant la dernière image

Usage :  python musique.py   ->  out/musique.wav
"""
from pathlib import Path
import json
import wave

import numpy as np
from scipy import signal

SR = 48000
ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
TL = CFG["timeline"]
DUREE = CFG["duration"]
RNG = np.random.default_rng(2027)
N = int((DUREE + 3) * SR)
MIX = {k: np.zeros((N, 2)) for k in ("drums", "bass", "pad", "arp", "fx", "bell")}


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tt(n):
    return np.arange(n) / SR


def lp(x, fc, order=2):
    b, a = signal.butter(order, min(fc, SR / 2 - 200), fs=SR)
    return signal.lfilter(b, a, x, axis=0)


def hp(x, fc, order=2):
    b, a = signal.butter(order, fc, btype="high", fs=SR)
    return signal.lfilter(b, a, x, axis=0)


def bp(x, f0, f1, order=2):
    b, a = signal.butter(order, [f0, f1], btype="band", fs=SR)
    return signal.lfilter(b, a, x, axis=0)


def lp_sweep(x, f0, f1, blk=512):
    out, zi, n = np.zeros_like(x), None, len(x)
    for k in range(0, n, blk):
        fc = f0 * (f1 / f0) ** (k / max(1, n - 1))
        b, a = signal.butter(2, min(fc, SR / 2 - 200), fs=SR)
        if zi is None:
            zi = np.zeros(max(len(a), len(b)) - 1)
        out[k:k + blk], zi = signal.lfilter(b, a, x[k:k + blk], zi=zi)
    return out


def saw(f, n, phase=0.0):
    return 2 * ((f * tt(n) + phase) % 1.0) - 1


def stereo(x, pan=0.0):
    return np.vstack([x * np.sqrt(0.5 - pan / 2), x * np.sqrt(0.5 + pan / 2)]).T


def add(bus, t, x, gain_db=0.0):
    if x.ndim == 1:
        x = stereo(x)
    i = int(round(t * SR))
    if i >= N or i < 0:
        return
    x = x[: N - i] * 10 ** (gain_db / 20)
    MIX[bus][i:i + len(x)] += x


def reverb(x, dur=2.4, decay=3.0, hp_f=200):
    n = int(dur * SR)
    t = tt(n)
    irs = []
    for _ in range(2):
        ir = RNG.standard_normal(n) * np.exp(-t * decay)
        ir = lp(ir, 7000)
        irs.append(ir / np.sqrt((ir ** 2).sum()) * 0.5)
    wet = np.vstack([signal.fftconvolve(x[:, 0], irs[0])[: len(x)], signal.fftconvolve(x[:, 1], irs[1])[: len(x)]]).T
    return hp(wet, hp_f)


def delay(x, d=0.375, fb=0.35, mix=0.35):
    k = int(d * SR)
    out = x.copy()
    tap = x.copy()
    for i in range(1, 6):
        tap = np.roll(tap, k, axis=0) * fb
        tap[:k] = 0
        tap = tap[:, ::-1]
        out += tap * mix / fb
    return out


# ------------------------------------------------------------------ instruments
def kick(size=1.0):
    n = int(0.6 * SR)
    t = tt(n)
    f = 44 + 120 * np.exp(-t * 30)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (6.5 / size))
    x += hp(RNG.standard_normal(n), 1800) * np.exp(-t * 320) * 0.35
    return np.tanh(x * 1.4) * 0.9


def clap():
    n = int(0.5 * SR)
    t = tt(n)
    env = np.zeros(n)
    for o in (0.0, 0.011, 0.023):
        k = int(o * SR)
        env[k:] += np.exp(-(t[: n - k]) * (55 if o < 0.02 else 16))
    x = bp(RNG.standard_normal(n), 900, 5200) * env * 0.6
    x += np.sin(2 * np.pi * 185 * t) * np.exp(-t * 30) * 0.25
    st = stereo(x)
    return st + reverb(st, 1.2, 5.0, 400) * 0.6


def hat(open_=False):
    n = int((0.3 if open_ else 0.08) * SR)
    t = tt(n)
    x = hp(RNG.standard_normal(n), 7500) * np.exp(-t * (11 if open_ else 65)) * 0.5
    return x


def snare():
    n = int(0.35 * SR)
    t = tt(n)
    x = bp(RNG.standard_normal(n), 1200, 7000) * np.exp(-t * 22) * 0.55 + np.sin(2 * np.pi * 200 * t) * np.exp(-t * 35) * 0.35
    return x


def bass_note(m, dur, cut=700, pump=True):
    n = int(dur * SR)
    t = tt(n)
    f = hz(m)
    x = saw(f, n) * 0.6 + saw(f * 1.004, n, 0.3) * 0.4 + np.sin(2 * np.pi * f / 2 * t) * 0.7
    env = np.minimum(1, t / 0.004) * (0.55 + 0.45 * np.exp(-t * 9)) * np.clip((dur - t) / 0.03, 0, 1)
    x = lp(x * env, cut)
    return x


def pad_chord(notes, dur, cut=1900, att=0.35, rel=0.9, bright=1.0):
    n = int((dur + rel) * SR)
    t = tt(n)
    L, R = np.zeros(n), np.zeros(n)
    for m in notes:
        f = hz(m)
        for det, side in ((-0.007, 0), (0.0, 2), (0.007, 1)):
            v = saw(f * (1 + det), n, RNG.uniform())
            if side in (0, 2):
                L += v
            if side in (1, 2):
                R += v
    env = np.minimum(1, t / att) * np.clip((dur + rel - t) / rel, 0, 1) ** 1.5
    st = np.vstack([L * env, R * env]).T / (len(notes) * 2.5)
    return lp(st, cut * bright)


def pluck(m, cut=3200):
    n = int(0.45 * SR)
    t = tt(n)
    f = hz(m)
    x = saw(f, n) * 0.7 + (2 * ((f * t) % 1 < 0.5) - 1) * 0.3
    x = lp_sweep(x * np.exp(-t * 9), cut, 500)
    return x


def bell(m, dur=1.6):
    n = int(dur * SR)
    t = tt(n)
    f = hz(m)
    x = (np.sin(2 * np.pi * f * t) + 0.45 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 3)
         + 0.25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 6)) * np.exp(-t * 2.4) * np.minimum(1, t / 0.002)
    return x * 0.35


def riser(dur):
    n = int(dur * SR)
    t = tt(n)
    noise = RNG.standard_normal(n)
    x = lp_sweep(hp(noise, 300), 400, 12000) * (t / dur) ** 2.2 * 0.5
    f = 110 * 8 ** (t / dur)
    x += np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / dur) ** 2 * 0.18
    return stereo(x, 0) + stereo(np.roll(x, 300), 0) * 0.3


def sub_boom(dur=2.2):
    n = int(dur * SR)
    t = tt(n)
    f = 30 + 40 * np.exp(-t * 4)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6) * 0.9


def reverse_swell(dur=0.9):
    n = int(dur * SR)
    x = lp(RNG.standard_normal(n), 5000) * np.exp(-tt(n) * 4)
    x = x[::-1] * 0.35
    st = stereo(x)
    return st + reverb(st, 1.0, 4, 300) * 0.5


# ------------------------------------------------------------------ partition
B, S16 = 0.5, 0.125
ETAPES = [t for _, t in TL["etapes"]]
TG, TM = ETAPES[-1], TL["marque"]
TF, FIN = TL["final"], TL["fin"]
kicks = []


def K(t, size=1.0, gain=-5):
    add("drums", t, kick(size), gain)
    kicks.append(t)


# « TU SAURAIS RÉSOUDRE ÇA ? » : impact dès la première image, pulsation grave tendue
K(0.0, 1.6, -1)
add("bass", 0.0, sub_boom(1.4), -5)
for i in range(int(ETAPES[1] / S16)):
    t0 = i * S16
    add("bass", t0, bass_note(26 if i % 4 else 38, S16 * 0.85, 180 + 300 * t0), -11)
add("pad", 0.0, pad_chord([50, 53, 56], ETAPES[1], 800, att=0.25, rel=0.05), -18)   # accord tendu (diminué)
for i, t0 in enumerate(np.arange(0.25, ETAPES[1] - 0.01, S16)):
    add("drums", t0, hat(), -26 + i * 0.8)
K(0.5, 0.7, -12)

# LA RÉSOLUTION : un accord par étape, l'arpège monte d'un cran à chaque étape
accords = [(38, [50, 57, 62, 65]), (34, [46, 53, 58, 62]), (41, [53, 57, 60, 65]), (36, [48, 55, 60, 64])]
notes = [[62, 65, 69, 74], [65, 70, 74, 77], [69, 72, 77, 81], [72, 76, 79, 84]]
for n, t0 in enumerate(ETAPES[1:-1]):
    t1 = ETAPES[n + 2]
    root, padn = accords[n % 4]
    lvl = n / 3
    K(t0, 0.9, -7)
    add("pad", t0, pad_chord(padn, t1 - t0, 1300 + 900 * lvl, att=0.02, rel=0.15), -13 + 2 * lvl)
    add("bass", t0, bass_note(root, t1 - t0 - 0.02, 500 + 300 * lvl), -9)
    pas = 0.1                                    # les étapes s'accélèrent : 4 notes par étape de 0,4 s
    for j, t in enumerate(np.arange(t0, t1 - 0.01, pas)):
        add("arp", t, pluck(notes[n][j % 4] + (12 if j >= 4 else 0), 2000 + 1600 * lvl), -20 + 3 * lvl)
    for t in np.arange(t0 + 0.2, t1 - 0.01, 0.2):
        add("drums", t, hat(), -19 + 3 * lvl)
    if TL.get("roulement") is not None and n + 1 == TL["roulement"]:   # la solution barrée : roulement qui retient la réponse
        for i, t in enumerate(np.arange(t0 + 0.4, t1 - 0.01, 0.1)):
            add("drums", t, snare(), -20 + i * 1.2)

# LA RÉPONSE : accord de cloches lumineux, puis montée vers la marque
K(TG, 1.1, -4)
add("bass", TG, sub_boom(1.0), -10)
add("pad", TG, pad_chord([53, 57, 60, 65, 69], TM - TG - 0.05, 2400, att=0.01, rel=0.2), -11)
for k, m in enumerate((77, 81, 84, 89)):
    add("bell", TG + k * 0.035, bell(m, 1.8), -12)
roll = list(np.arange(TG + 0.5, TG + 0.75, S16)) + list(np.arange(TG + 0.75, TM - 0.04, S16 / 2))
for i, t0 in enumerate(roll):
    add("drums", t0, snare(), -12 + i * 0.9)
add("fx", TM - 0.5, reverse_swell(0.5), -6)
add("fx", TG + 0.25, riser(TM - TG - 0.25), -9)
add("fx", ETAPES[2], riser(TG - ETAPES[2]), -13)

# MATHÉO PLUS : grand impact, rythmique complète sous le slogan et l'appel à l'action
K(TM, 1.6, -1)
add("bass", TM, sub_boom(2.2), -5)
add("pad", TM, pad_chord([38, 50, 57, 62, 64, 65, 69, 74], TF - TM, 2600, att=0.02, rel=0.3), -8)
add("pad", TF, pad_chord([46, 53, 58, 62, 65, 70], FIN - TF - 0.05, 2600, att=0.02, rel=0.25), -9)
for t0, m in ((TM, 74), (TM + 0.5, 81), (TM + 1.0, 77), (TF, 86)):
    add("bell", t0, bell(m, 1.6), -13)
t0, j = TM + 0.5, 0
while t0 < FIN - 1e-6:
    root = 38 if t0 < TF else 34
    if abs(((t0 - TM) / B) - round((t0 - TM) / B)) < 1e-6:
        K(t0, 0.95, -6)
        if round((t0 - TM) / B) % 2 == 1:
            add("drums", t0, clap(), -10)
    else:
        add("drums", t0, hat(), -16)
    add("bass", t0, bass_note(root + (12 if j % 4 == 3 else 0), 0.22, 900), -8)
    t0 += 0.25
    j += 1
for t0 in np.arange(TM, FIN - 0.01, S16):
    i = int(round((t0 - TM) / S16))
    seq = [62, 65, 69, 74, 69, 65, 74, 77] if t0 < TF else [58, 62, 65, 70, 65, 62, 70, 74]
    add("arp", t0, pluck(seq[i % 8] + 12, 3000), -20)
# accord final sec : tout tombe ensemble, puis s'éteint avant la dernière image
K(FIN, 1.3, -2)
add("bass", FIN, bass_note(26, 0.4, 400), -6)
add("pad", FIN, pad_chord([50, 57, 62, 65, 69, 74], 0.12, 3000, att=0.005, rel=0.3), -7)
add("bell", FIN, bell(86, 0.5), -11)
add("drums", FIN, clap(), -10)

# ------------------------------------------------------------------ mixage
t_all = tt(N)
pump = np.ones(N)
for k in kicks:
    i = int(k * SR)
    seg = t_all[: N - i]
    pump[i:] = np.minimum(pump[i:], 1 - 0.5 * np.exp(-seg / 0.11))
pump = pump[:, None]
mix = MIX["drums"] * 1.0
mix += MIX["bass"] * pump
mix += (MIX["pad"] + reverb(MIX["pad"], 2.6, 2.2) * 0.8) * pump
arp = delay(MIX["arp"], 0.375, 0.32, 0.4)
mix += (arp + reverb(arp, 2.0, 3.0, 400) * 0.5) * pump
mix += MIX["bell"] + reverb(MIX["bell"], 3.0, 1.8, 500) * 0.9
mix += MIX["fx"]
mix = hp(mix, 28)
mix = mix[: int(DUREE * SR)]
fin = int((DUREE - FIN - 0.25) * SR)
mix[-fin:] *= (np.linspace(1, 0, fin) ** 1.5)[:, None]   # fin nette : l'accord final s'éteint juste avant la dernière image
mix = np.tanh(mix / (np.abs(mix).max() + 1e-9) * 1.6) / np.tanh(1.6)
mix *= 10 ** (-1.0 / 20) / np.abs(mix).max()


def ecrire(chemin, x):
    with wave.open(str(chemin), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


if __name__ == "__main__":
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    ecrire(out / "musique.wav", mix)
    print(out / "musique.wav")
