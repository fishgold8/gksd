"""Автоморгание: переключение eyes на «закрытые» на несколько кадров."""

from maya import cmds

from . import config, logic
from .face import face_ctrl
from .utils import fps, keyed_frames, set_stepped_key, undoable


@undoable
def add_blinks(ns, closed_value, start, end, min_interval=config.BLINK_MIN_INTERVAL,
               max_interval=config.BLINK_MAX_INTERVAL, duration=config.BLINK_DURATION,
               seed=None, respect_keys=True):
    """Расставляет моргания. Возвращает список кадров, где они появились.

    respect_keys: не ставить моргание поверх уже существующих ключей eyes
    (чтобы не ломать смену эмоций).
    """
    plug = face_ctrl(ns) + "." + config.EYES_ATTR
    added = []
    for frame in logic.plan_blinks(start, end, fps(), min_interval, max_interval, duration, seed):
        reopen = frame + duration
        if respect_keys and keyed_frames(plug, frame - 1, reopen + 1):
            continue
        open_value = cmds.getAttr(plug, time=frame)
        if abs(open_value - closed_value) < 0.5:
            continue  # глаза уже закрыты по анимации
        set_stepped_key(plug, frame, closed_value)
        set_stepped_key(plug, reopen, open_value)
        added.append(frame)
    return added


@undoable
def remove_blinks(ns, closed_value, start, end):
    """Удаляет пары ключей «закрыто/открыто», похожие на моргания."""
    plug = face_ctrl(ns) + "." + config.EYES_ATTR
    removed = 0
    frames = sorted(keyed_frames(plug, start, end))
    for i, frame in enumerate(frames[:-1]):
        value = cmds.keyframe(plug, q=True, time=(frame, frame), valueChange=True)[0]
        nxt = frames[i + 1]
        if abs(value - closed_value) >= 0.5 or nxt - frame > 8:
            continue
        before = cmds.getAttr(plug, time=frame - 1)
        after = cmds.keyframe(plug, q=True, time=(nxt, nxt), valueChange=True)[0]
        if abs(before - after) < 0.5:
            cmds.cutKey(plug, time=(frame, frame))
            cmds.cutKey(plug, time=(nxt, nxt))
            removed += 1
    return removed
