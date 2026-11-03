#!/usr/bin/env python3
"""
lektor.py - Polish voice-over for the Reels, free and local.

Model: Chatterbox Multilingual (Resemble AI, MIT licence) - expressive speech with
an emotion knob ("exaggeration"), cloning the PageHub voice from
assets/voice/lektor.wav (voice 6 of Supertonic 3, OpenRAIL-M, chosen by Jakub).
Needs torch and the model from Hugging Face (about 3 GB), so it runs in GitHub
Actions (.github/workflows/lektor.yml), not in the Monday cloud session.

The narrator reads exactly the words of the Reel's three screens (tools/reel_text.py:
cover title and subtitle, list heading and points, closing line and button), only
with numbers spelled out. For every kN.json of a week it writes
weeks/<data>/kN/voice-<part>.wav (24 kHz mono) and kN/voice.json (the screen text,
what was said, lengths, what the check heard). make_reel.py mixes them in, times the
screens to the voice and ignores a clip whose text no longer matches the screen.
A clip is generated again only when its text or the settings change.

Nobody listens to these before they go out, so every take is checked:
  - Whisper (small, via sherpa-onnx) writes down what it hears and it is compared
    with the screen text word by word, so a mumbled, swallowed or changed word loses,
  - every question must go up at the end (tools/prosody.py),
  - the length must fit the text.
Up to TAKES takes per line, the best one wins; a question that still ends flat gets
its end lifted with PSOLA. A line that still sounds wrong is marked "uwaga" in voice.json.

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
SETTINGS = {"exaggeration": 0.7, "cfg_weight": 0.4, "temperature": 0.8}
CHARS_PER_SEC = 16.5          # rough speaking rate, to catch a clip that lost or repeated words
TAKES = 4
GOOD_WER, MAX_WER = 0.05, 0.25
ASR_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-small.tar.bz2"
ASR_DIR = pathlib.Path.home() / ".cache" / "pagehub-asr" / "sherpa-onnx-whisper-small"

sys.path.insert(0, str(ROOT / "tools"))
from prosody import flat_questions, lift_questions  # noqa: E402
from reel_text import PARTS, speakable, voice_script  # noqa: E402

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


_asr = None


def recognizer():
    """Whisper small (MIT) through sherpa-onnx, downloaded once into ~/.cache."""
    global _asr
    if _asr is None:
        import sherpa_onnx
        if not ASR_DIR.exists():
            import subprocess
            ASR_DIR.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(f"curl -sL {ASR_URL} | tar xj -C {ASR_DIR.parent}", shell=True, check=True)
        _asr = sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=str(ASR_DIR / "small-encoder.int8.onnx"), decoder=str(ASR_DIR / "small-decoder.int8.onnx"),
            tokens=str(ASR_DIR / "small-tokens.txt"), language="pl", task="transcribe", num_threads=4)
    return _asr


def heard(x, sr):
    s = recognizer().create_stream()
    s.accept_waveform(sr, x.astype(np.float32).tolist())
    recognizer().decode_stream(s)
    return s.result.text.strip()


def plain(text):
    """Lowercase letters only, numbers as words, for comparing script and transcript."""
    from num2words import num2words
    text = re.sub(r"\d+", lambda m: " " + num2words(int(m.group(0)), lang="pl") + " ", text.lower())
    return " ".join(re.sub(r"[^\w\s]|_", " ", text).split())


def wer(ref, hyp):
    """Share of words heard wrong (Whisper small makes a few mistakes of its own, so
    this ranks takes against each other rather than judging one alone)."""
    return _edits(plain(ref).split(), plain(hyp).split())


def cer(ref, hyp):
    return _edits(plain(ref), plain(hyp))


def _edits(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] / max(len(a), 1)


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


def say(text, settings=SETTINGS, ref=REF, seed=0, tries=TAKES):
    """The best of up to `tries` takes: words heard right, questions going up, sane length."""
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
        ratio = len(x) / m.sr / expected
        said = heard(x, m.sr)
        w, c = wer(text, said), cer(text, said)
        flat = flat_questions(x, m.sr, text)
        score = w + 0.5 * c + 0.04 * len(flat) + 0.3 * max(0.0, abs(np.log(ratio)) - np.log(1.5))
        print(f"  [{k + 1}] {len(x) / m.sr:.1f} s  źle słów {w:.0%}  płaskie pytania {len(flat)}  | {said}", flush=True)
        if best is None or score < best["score"]:
            best = {"x": x, "score": score, "wer": w, "flat": flat, "heard": said, "take": k + 1}
        if w <= GOOD_WER and not flat and 0.6 < ratio < 1.6:
            break
    x = best["x"]
    if best["flat"]:
        x = lift_questions(x, m.sr, text, only=best["flat"])
    report = {"take": best["take"], "heard": best["heard"], "wer": round(best["wer"], 3),
              "lifted_questions": len(best["flat"])}
    return x, m.sr, report


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
    done, bad = 0, []
    for spec_path in sorted(pathlib.Path(folder).glob("k*.json")):
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        if spec.get("meta", {}).get("skip") or spec.get("meta", {}).get("reel") is False:
            continue
        keyword = spec.get("meta", {}).get("cta_keyword", "")
        out = spec_path.with_suffix("")
        info_path = out / "voice.json"
        info = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else {"parts": {}}
        for part, script in zip(PARTS, voice_script(spec)):
            text = script["text"]
            if not text:
                continue
            h = sha(text, settings)
            wav = out / f"voice-{part}.wav"
            if not force and wav.exists() and info["parts"].get(part, {}).get("sha") == h:
                continue
            print(f"{spec_path.parent.name}/{spec_path.stem} {part}", flush=True)
            said = speakable(text, keyword)
            x, sr, report = say(said, settings, seed=int(h[:6], 16))
            if report["wer"] > MAX_WER:
                bad.append(f"{spec_path.stem} {part}: {report['heard']}")
                report["uwaga"] = "niewyraźne, przepisz prościej"
            write(wav, x, sr)
            info["parts"][part] = {"text": text, "spoken": spoken(said), "sha": h,
                                   "seconds": round(len(x) / sr, 2), **report}
            done += 1
        info["model"] = "Chatterbox Multilingual (MIT), głos: assets/voice/lektor.wav"
        info["settings"] = settings
        info_path.parent.mkdir(parents=True, exist_ok=True)
        info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"lektor: {done} nowych nagrań")
    if bad:
        print("UWAGA, te zdania wychodzą niewyraźnie, przepisz je prościej:\n  " + "\n  ".join(bad))


def probki(out_dir):
    out = pathlib.Path(out_dir)
    k1 = json.loads((ROOT / "weeks" / "2026-11-02" / "k1.json").read_text(encoding="utf-8"))
    script = speakable(" ".join(s["text"] for s in voice_script(k1)), k1["meta"].get("cta_keyword", ""))
    test = "Tracisz klientów? Szybko to sprawdzisz. Masz pięć minut? To zrób to teraz!"
    variants = [
        ("A-spokojny", {"exaggeration": 0.5, "cfg_weight": 0.5, "temperature": 0.8}, REF),
        ("B-zywy", SETTINGS, REF),
        ("C-bardzo-emocjonalny", {"exaggeration": 1.0, "cfg_weight": 0.3, "temperature": 0.8}, REF),
    ]
    for name, settings, ref in variants:
        print(name, flush=True)
        parts = [say(t, settings, ref=ref, seed=11, tries=1) for t in (script, test)]
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
