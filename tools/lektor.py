#!/usr/bin/env python3
"""
lektor.py - Polish voice-over for the Reels, free and local.

Model: Chatterbox Multilingual (Resemble AI, MIT licence) - expressive speech with
an emotion knob ("exaggeration"), cloning the PageHub voice from
assets/voice/lektor.wav (voice 6 of Supertonic 3, OpenRAIL-M, chosen by Jakub).
Needs torch and the model from Hugging Face (about 3 GB), so it runs in GitHub
Actions (.github/workflows/lektor.yml), not in the Monday cloud session.

For every kN.json of a week with meta.reel_voice {"cover", "list", "sell"} it writes
weeks/<data>/kN/voice-<part>.wav (24 kHz mono) and kN/voice.json (texts, settings,
lengths). make_reel.py mixes them in and times the screens to the voice. A clip is
generated again only when its text or the settings change.

Usage
  python tools/lektor.py weeks/2026-11-02
  python tools/lektor.py weeks/2026-11-02 --force
  python tools/lektor.py --probki out/probki        # the same lines in a few settings, to compare
"""

import argparse
import hashlib
import json
import pathlib
import re
import sys
import unicodedata
import wave

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
REF = ROOT / "assets" / "voice" / "lektor.wav"
PARTS = ("cover", "list", "sell")
SETTINGS = {"exaggeration": 0.7, "cfg_weight": 0.4, "temperature": 0.8}
CHARS_PER_SEC = 16.5          # rough speaking rate, to catch a clip that lost or repeated words

_model = None


def model():
    global _model
    if _model is None:
        import torch
        original = torch.load

        def cpu_load(*a, **k):                       # checkpoints were saved on GPU
            k.setdefault("map_location", "cpu")
            return original(*a, **k)

        torch.load = cpu_load
        torch.set_num_threads(max(1, torch.get_num_threads()))
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        _model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    return _model


def spoken(text):
    """What the narrator gets: plain sentences, no markup."""
    text = unicodedata.normalize("NFC", text).replace("*", "")
    text = re.sub(r"\s+[-–—]\s+", ", ", text)
    return " ".join(text.split())


def trim(x, sr):
    env = np.convolve(np.abs(x), np.ones(int(sr * 0.01)) / int(sr * 0.01), "same")
    loud = np.where(env > env.max() * 0.03)[0]
    if not len(loud):
        return x
    a, b = max(0, loud[0] - int(0.03 * sr)), min(len(x), loud[-1] + int(0.12 * sr))
    y = x[a:b].copy()
    f = int(0.01 * sr)
    y[:f] *= np.linspace(0, 1, f)
    y[-f:] *= np.linspace(1, 0, f)
    return y


def say(text, settings=SETTINGS, ref=REF, seed=0, tries=3):
    """One clip, checked: a clip much shorter or longer than the text is regenerated."""
    import torch
    m = model()
    text = spoken(text)
    expected = len(text) / CHARS_PER_SEC
    best = None
    for k in range(tries):
        torch.manual_seed(seed + k)
        kw = dict(language_id="pl", exaggeration=settings["exaggeration"],
                  cfg_weight=settings["cfg_weight"], temperature=settings["temperature"])
        if ref:
            kw["audio_prompt_path"] = str(ref)
        wav = m.generate(text, **kw)
        x = trim(wav.squeeze(0).cpu().numpy().astype(np.float32), m.sr)
        dur = len(x) / m.sr
        ratio = dur / expected
        print(f"  [{k + 1}] {dur:.1f} s (oczekiwane ~{expected:.1f} s)  {text[:60]}", flush=True)
        if best is None or abs(np.log(ratio)) < abs(np.log(best[1])):
            best = (x, ratio)
        if 0.6 < ratio < 1.6:
            break
    return best[0], m.sr


def write(path, x, sr):
    path.parent.mkdir(parents=True, exist_ok=True)
    y = x / max(np.abs(x).max(), 1e-6) * 0.9
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((y * 32767).astype("<i2").tobytes())


def sha(text, settings):
    return hashlib.sha1(json.dumps([spoken(text), settings, REF.stat().st_size], sort_keys=True)
                        .encode()).hexdigest()[:12]


def week(folder, force=False, settings=SETTINGS):
    done = 0
    for spec_path in sorted(pathlib.Path(folder).glob("k*.json")):
        meta = json.loads(spec_path.read_text(encoding="utf-8")).get("meta", {})
        voice = meta.get("reel_voice")
        if not voice:
            continue
        out = spec_path.with_suffix("")
        info_path = out / "voice.json"
        info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else {"parts": {}}
        for part in PARTS:
            text = voice.get(part)
            if not text:
                continue
            h = sha(text, settings)
            wav = out / f"voice-{part}.wav"
            if not force and wav.exists() and info["parts"].get(part, {}).get("sha") == h:
                continue
            print(f"{spec_path.parent.name}/{spec_path.stem} {part}", flush=True)
            x, sr = say(text, settings, seed=int(h[:6], 16))
            write(wav, x, sr)
            info["parts"][part] = {"text": spoken(text), "sha": h, "seconds": round(len(x) / sr, 2)}
            done += 1
        info["model"] = "Chatterbox Multilingual (MIT), głos: assets/voice/lektor.wav"
        info["settings"] = settings
        info_path.parent.mkdir(parents=True, exist_ok=True)
        info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"lektor: {done} nowych nagrań")


def probki(out_dir):
    out = pathlib.Path(out_dir)
    k1 = json.loads((ROOT / "weeks" / "2026-11-02" / "k1.json").read_text(encoding="utf-8"))["meta"]["reel_voice"]
    script = " ".join(k1[p] for p in PARTS)
    test = "Tracisz klientów? Szybko to sprawdzisz. Masz pięć minut? To zrób to teraz!"
    variants = [
        ("A-spokojny", {"exaggeration": 0.5, "cfg_weight": 0.5, "temperature": 0.8}, REF),
        ("B-zywy", SETTINGS, REF),
        ("C-bardzo-emocjonalny", {"exaggeration": 1.0, "cfg_weight": 0.3, "temperature": 0.8}, REF),
        ("D-zywy-glos-wbudowany", SETTINGS, None),
    ]
    for name, settings, ref in variants:
        print(name, flush=True)
        parts = [say(t, settings, ref=ref, seed=11) for t in (script, test)]
        sr = parts[0][1]
        gap = np.zeros(int(0.8 * sr), dtype=np.float32)
        write(out / f"{name}.wav", np.concatenate([parts[0][0], gap, parts[1][0]]), sr)


def main():
    ap = argparse.ArgumentParser(description="Polski lektor do rolek (Chatterbox Multilingual).")
    ap.add_argument("week", nargs="?")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--probki")
    a = ap.parse_args()
    if a.probki:
        probki(a.probki)
    if a.week:
        week(a.week, a.force)
    if not a.probki and not a.week:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
