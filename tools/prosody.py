#!/usr/bin/env python3
"""
prosody.py - make a narrator clip sound like it means its questions.

Many TTS voices read "Masz pięć minut?" with the same falling tone as a statement.
Polish yes/no questions rise at the end, so for every sentence that ends with "?"
this bends the pitch of its last ~0.4 s upwards (PSOLA in Praat via parselmouth:
the voice itself is untouched, only the melody changes). Sentences are found at
the pauses between them, the same way make_reel.py finds them.

Usage (in code)
  from prosody import lift_questions
  y = lift_questions(x, sr, "Wolna strona? Klient pójdzie do konkurencji!")
"""

import re

import numpy as np

RISE_ST = 5.5          # how far the end of a question goes up, in semitones
RISE_LEN = 0.38        # over how many seconds before the end of the sentence


def sentences(text):
    return [s.strip() for s in re.findall(r"[^.!?]+[.!?]*", text) if s.strip()]


def segments(x, sr, count):
    """`count` sentences at the `count - 1` longest pauses (same rule as make_reel)."""
    hop = int(0.01 * sr)
    frames = len(x) // hop
    rms = np.sqrt(np.mean(x[: frames * hop].reshape(frames, hop) ** 2, axis=1))
    quiet = rms < max(rms.max() * 0.04, 1e-4)
    pauses, i = [], 0
    while i < frames:
        if quiet[i]:
            j = i
            while j < frames and quiet[j]:
                j += 1
            if i > 0 and j < frames and j - i >= 6:
                pauses.append((j - i, i, j))
            i = j
        else:
            i += 1
    cut = sorted(sorted(pauses, reverse=True)[: max(0, count - 1)], key=lambda p: p[1])
    if len(cut) != count - 1:
        return None
    edges = [0] + [c[1] * hop / sr for c in cut] + [len(x) / sr]
    return list(zip(edges[:-1], edges[1:]))


def end_moves(x, sr, text):
    """Pitch movement (semitones) over the last ~0.1 s of every sentence, None when
    it cannot be measured. A spoken yes/no question ends clearly up (> +2)."""
    sents = sentences(text)
    segs = segments(x, sr, len(sents))
    if not segs:
        return [None] * len(sents)
    import parselmouth
    p = parselmouth.Sound(x.astype(np.float64), sampling_frequency=sr).to_pitch(
        time_step=0.01, pitch_floor=70, pitch_ceiling=450)
    f, t = p.selected_array["frequency"], p.xs()
    out = []
    for a, b in segs:
        v = f[(f > 0) & (t >= a) & (t <= b)]
        out.append(round(float(12 * np.log2(np.median(v[-10:]) / np.median(v[-40:-10]))), 1)
                   if len(v) >= 20 else None)
    return out


def flat_questions(x, sr, text):
    """Indexes of the questions that do not go up at the end."""
    moves = end_moves(x, sr, text)
    return [i for i, (s, m) in enumerate(zip(sentences(text), moves)) if s.endswith("?") and m is not None and m < 2.0]


def lift_questions(x, sr, text, rise=RISE_ST, only=None):
    """Lift the end of every question (or only the sentence indexes in `only`)."""
    sents = sentences(text)
    if not any(s.endswith("?") for s in sents):
        return x
    segs = segments(x, sr, len(sents))
    if not segs:
        return x
    import parselmouth
    from parselmouth.praat import call
    snd = parselmouth.Sound(x.astype(np.float64), sampling_frequency=sr)
    manip = call(snd, "To Manipulation", 0.01, 70, 450)
    tier = call(manip, "Extract pitch tier")
    pitch = snd.to_pitch(time_step=0.01, pitch_floor=70, pitch_ceiling=450)
    f0, ts = pitch.selected_array["frequency"], pitch.xs()
    n = call(tier, "Get number of points")
    points = [(call(tier, "Get time from index", i), call(tier, "Get value at index", i)) for i in range(1, n + 1)]
    windows = []
    for i, (s, (a, b)) in enumerate(zip(sents, segs)):
        if not s.endswith("?") or (only is not None and i not in only):
            continue
        voiced = ts[(f0 > 0) & (ts >= a) & (ts <= b)]
        if len(voiced) < 10:
            continue
        end = voiced[-1]
        windows.append((end - RISE_LEN, end))
    if not windows:
        return x

    # Inside each window the original (falling) melody is replaced by a stylised
    # question tune that starts where the voice already is: a small dip, then up.
    def value(t, v):
        for w0, w1 in windows:
            if w0 <= t <= w1 + 0.06:
                before = [pv for pt, pv in points if w0 - 0.12 <= pt <= w0]
                base = float(np.median(before)) if before else v
                k = min(1.0, (t - w0) / (w1 - w0))
                st = -0.8 * np.sin(np.pi * min(1.0, k / 0.35)) if k < 0.35 else \
                    rise * (0.5 - 0.5 * np.cos(np.pi * (k - 0.35) / 0.65))
                wobble = (v / base) ** 0.25 if base > 0 else 1.0     # keep a little of the original life
                return base * 2 ** (st / 12) * wobble
        return v

    call(tier, "Remove points between", 0, len(x) / sr)
    for t, v in points:
        call(tier, "Add point", t, value(t, v))
    call([tier, manip], "Replace pitch tier")
    out = call(manip, "Get resynthesis (overlap-add)")
    y = out.values[0].astype(np.float32)
    return y[: len(x)] if len(y) >= len(x) else np.pad(y, (0, len(x) - len(y)))
