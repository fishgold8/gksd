"""Чистая логика без зависимостей от Maya (тестируется вне Maya)."""

import array
import math
import random
import sys
import wave


# --- Моргание ---------------------------------------------------------------

def plan_blinks(start, end, fps, min_interval, max_interval, duration, seed=None):
    """Кадры начала морганий в диапазоне [start, end].

    Интервал между морганиями случайный в [min_interval, max_interval] секунд.
    Моргание целиком (duration кадров) помещается в диапазон.
    """
    if fps <= 0 or duration < 1 or end - start < duration:
        return []
    lo, hi = sorted((float(min_interval), float(max_interval)))
    lo = max(lo, (duration + 1) / float(fps))
    hi = max(hi, lo)
    rng = random.Random(seed)
    frames = []
    t = start + rng.uniform(lo * 0.5, hi) * fps
    while True:
        frame = int(round(t))
        if frame + duration > end:
            break
        frames.append(frame)
        t += rng.uniform(lo, hi) * fps
    return frames


# --- Звук -------------------------------------------------------------------

def _decode_samples(raw, sampwidth):
    """Сырые байты PCM -> список целых сэмплов и максимальная амплитуда."""
    if sampwidth == 1:
        return [b - 128 for b in raw], 128.0
    if sampwidth == 2:
        data = array.array("h")
        data.frombytes(raw)
        if sys.byteorder == "big":
            data.byteswap()
        return data, 32768.0
    if sampwidth == 3:
        out = []
        for i in range(0, len(raw) - 2, 3):
            v = raw[i] | (raw[i + 1] << 8) | (raw[i + 2] << 16)
            if v & 0x800000:
                v -= 0x1000000
            out.append(v)
        return out, 8388608.0
    if sampwidth == 4:
        data = array.array("i")
        data.frombytes(raw)
        if sys.byteorder == "big":
            data.byteswap()
        return data, 2147483648.0
    raise ValueError("Неподдерживаемая разрядность WAV: %d байт" % sampwidth)


def read_wav_envelope(path, fps):
    """Громкость (RMS, 0..1 от полной шкалы) на каждый кадр анимации."""
    with wave.open(path, "rb") as wav:
        channels = wav.getnchannels()
        sampwidth = wav.getsampwidth()
        rate = wav.getframerate()
        raw = wav.readframes(wav.getnframes())
    samples, full_scale = _decode_samples(raw, sampwidth)
    if channels > 1:
        samples = [
            sum(samples[i:i + channels]) / float(channels)
            for i in range(0, len(samples) - channels + 1, channels)
        ]
    per_frame = rate / float(fps)
    count = int(math.ceil(len(samples) / per_frame)) if samples else 0
    envelope = []
    for f in range(count):
        a = int(f * per_frame)
        b = min(len(samples), int((f + 1) * per_frame))
        if b <= a:
            envelope.append(0.0)
            continue
        acc = 0.0
        for s in samples[a:b]:
            acc += s * s
        envelope.append(math.sqrt(acc / (b - a)) / full_scale)
    return envelope


def normalize(values, percentile=0.95):
    """Масштабирует так, чтобы заданный перцентиль стал 1.0 (с обрезкой)."""
    if not values:
        return []
    ordered = sorted(values)
    ref = ordered[min(len(ordered) - 1, int(len(ordered) * percentile))]
    if ref <= 0:
        ref = ordered[-1]
    if ref <= 0:
        return [0.0] * len(values)
    return [min(1.0, v / ref) for v in values]


def smooth(values, radius):
    """Скользящее среднее с радиусом radius кадров."""
    if radius <= 0 or not values:
        return list(values)
    n = len(values)
    out = []
    for i in range(n):
        a, b = max(0, i - radius), min(n, i + radius + 1)
        out.append(sum(values[a:b]) / float(b - a))
    return out


def classify_levels(values, thresholds):
    """Громкость -> уровень: 0 (тишина) .. len(thresholds)."""
    th = sorted(thresholds)
    return [sum(1 for t in th if v >= t) for v in values]


def enforce_min_hold(levels, min_hold):
    """Убирает мелькание: отрезки короче min_hold поглощаются соседями."""
    if min_hold <= 1 or not levels:
        return list(levels)
    runs = []  # [уровень, длина]
    for lv in levels:
        if runs and runs[-1][0] == lv:
            runs[-1][1] += 1
        else:
            runs.append([lv, 1])
    changed = True
    while changed and len(runs) > 1:
        changed = False
        for i, (lv, length) in enumerate(runs):
            if length >= min_hold:
                continue
            # отдаём кадры соседу с более высоким уровнем: рот не «проглатывает» слоги
            if i == 0:
                j = 1
            elif i == len(runs) - 1:
                j = i - 1
            else:
                j = i - 1 if runs[i - 1][0] >= runs[i + 1][0] else i + 1
            runs[j][1] += length
            del runs[i]
            merged = []
            for r in runs:
                if merged and merged[-1][0] == r[0]:
                    merged[-1][1] += r[1]
                else:
                    merged.append(r)
            runs = merged
            changed = True
            break
    out = []
    for lv, length in runs:
        out.extend([lv] * length)
    return out


def change_points(levels):
    """[(индекс кадра, уровень)] только там, где уровень меняется."""
    points = []
    prev = None
    for i, lv in enumerate(levels):
        if lv != prev:
            points.append((i, lv))
            prev = lv
    return points


def lipsync_keys(envelope, thresholds, min_hold=2, smooth_radius=1):
    """Полный конвейер: громкость по кадрам -> [(кадр, уровень)]."""
    env = smooth(normalize(envelope), smooth_radius)
    levels = enforce_min_hold(classify_levels(env, thresholds), min_hold)
    return change_points(levels), env


# --- Имена и зеркало --------------------------------------------------------

def split_namespace(name):
    if ":" in name:
        ns, base = name.rsplit(":", 1)
        return ns + ":", base
    return "", name


def opposite_name(name, side_tokens):
    """FKHip_L -> FKHip_R (с сохранением namespace). None, если стороны нет."""
    ns, base = split_namespace(name)
    for src, dst in side_tokens:
        if base.endswith(src):
            return ns + base[: -len(src)] + dst
    return None


def flip_attrs(name, rules):
    """Каналы, которые нужно инвертировать для контрола по таблице правил."""
    _, base = split_namespace(name)
    for prefix, attrs in rules:
        if base.startswith(prefix):
            return set(attrs)
    return set()


# --- Геометрия --------------------------------------------------------------

def pole_vector_position(start, mid, end, distance_factor=0.5):
    """Позиция pole vector по трём точкам конечности (мировые координаты)."""
    sx, sy, sz = start
    mx, my, mz = mid
    ex, ey, ez = end
    chain = (ex - sx, ey - sy, ez - sz)
    chain_len2 = sum(c * c for c in chain)
    to_mid = (mx - sx, my - sy, mz - sz)
    limb_len = math.sqrt(sum(c * c for c in to_mid)) + math.sqrt(
        (ex - mx) ** 2 + (ey - my) ** 2 + (ez - mz) ** 2)
    if chain_len2 < 1e-12:
        return mid
    t = sum(a * b for a, b in zip(to_mid, chain)) / chain_len2
    proj = (sx + chain[0] * t, sy + chain[1] * t, sz + chain[2] * t)
    out = (mx - proj[0], my - proj[1], mz - proj[2])
    out_len = math.sqrt(sum(c * c for c in out))
    if out_len < 1e-6:
        # конечность прямая — направление неоднозначно, оставляем pole у сустава
        return mid
    k = limb_len * distance_factor / out_len
    return (mx + out[0] * k, my + out[1] * k, mz + out[2] * k)
