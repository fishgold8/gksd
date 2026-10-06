"""Автолипсинк по громкости WAV: уровни громкости -> формы рта (Mouth)."""

import os

from maya import cmds

from . import config, logic
from .face import face_ctrl
from .utils import fps, set_stepped_key, undoable


def scene_sounds():
    """[(узел sound, путь к файлу, offset в кадрах)]."""
    out = []
    for snd in cmds.ls(type="audio") or []:
        out.append((snd, cmds.getAttr(snd + ".filename"), cmds.getAttr(snd + ".offset")))
    return out


def import_sound(path, offset=0):
    snd = cmds.sound(file=path, offset=offset)
    slider = cmds.lsUI(type="timeControl")
    if slider:
        cmds.timeControl(slider[0], e=True, sound=snd, displaySound=True)
    return snd


@undoable
def apply_lipsync(ns, wav_path, mouth_values, offset=0, thresholds=config.LIPSYNC_THRESHOLDS,
                  min_hold=config.LIPSYNC_MIN_HOLD, smooth_radius=config.LIPSYNC_SMOOTH,
                  clear_existing=True, jaw=None):
    """Ставит ключи Mouth по звуку.

    mouth_values: значения Mouth по уровням громкости, от тишины к самому
        громкому, например [1, 4, 5, 2]. Уровней = len(thresholds) + 1;
        если значений меньше, громкие уровни используют последнее.
    jaw: None или (атрибут, максимальное значение) — дополнительно открывать
        челюсть пропорционально громкости, например ('FKJaw_M.rz', 15).
    Возвращает (первый кадр, последний кадр, число ключей).
    """
    if not os.path.isfile(wav_path):
        raise RuntimeError("Файл не найден: %s" % wav_path)
    if not mouth_values:
        raise RuntimeError("Не выбраны формы рта.")
    envelope = logic.read_wav_envelope(wav_path, fps())
    if not envelope:
        raise RuntimeError("В файле нет звука.")
    points, env = logic.lipsync_keys(envelope, thresholds, min_hold, smooth_radius)

    plug = face_ctrl(ns) + "." + config.MOUTH_ATTR
    start = int(round(offset))
    end = start + len(envelope)
    if clear_existing:
        cmds.cutKey(plug, time=(start, end), clear=True)
    for i, level in points:
        value = mouth_values[min(level, len(mouth_values) - 1)]
        set_stepped_key(plug, start + i, value)
    # после фразы рот возвращается в «тишину»
    set_stepped_key(plug, end, mouth_values[0])

    if jaw:
        jaw_plug, jaw_max = jaw
        if not cmds.objExists(jaw_plug):
            jaw_plug = ns + jaw_plug
        if clear_existing:
            cmds.cutKey(jaw_plug, time=(start, end), clear=True)
        rest = cmds.getAttr(jaw_plug, time=start - 1)
        for i, v in enumerate(env):
            if i % 2 == 0:  # ключ через кадр — достаточно и не перегружает кривую
                cmds.setKeyframe(jaw_plug, time=start + i, value=rest + v * jaw_max)
        cmds.setKeyframe(jaw_plug, time=end, value=rest)
    return start, end, len(points) + 1
