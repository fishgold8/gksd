"""Общие помощники для работы с Maya."""

import functools

from maya import cmds, mel

from . import config


def undoable(func):
    """Всё, что делает функция, отменяется одним Ctrl+Z."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        cmds.undoInfo(openChunk=True, chunkName="AnimAuto: " + func.__name__)
        try:
            return func(*args, **kwargs)
        finally:
            cmds.undoInfo(closeChunk=True)
    return wrapper


def fps():
    return float(mel.eval("currentTimeUnitToFPS"))


def playback_range():
    return (int(cmds.playbackOptions(q=True, minTime=True)),
            int(cmds.playbackOptions(q=True, maxTime=True)))


def current_frame():
    return cmds.currentTime(q=True)


def find_rig_namespaces():
    """Namespace'ы, в которых есть Face_ctrl или Main ('' — без namespace)."""
    found = set()
    for base in (config.FACE_CTRL, config.MAIN_CTRL):
        for node in cmds.ls(base, "*:" + base, "*:*:" + base, type="transform") or []:
            found.add(node.rsplit(":", 1)[0] + ":" if ":" in node else "")
    return sorted(found)


def namespace_from_selection():
    sel = cmds.ls(selection=True) or []
    if sel and ":" in sel[0]:
        return sel[0].rsplit(":", 1)[0] + ":"
    return None


def node(ns, name):
    full = ns + name
    if not cmds.objExists(full):
        raise RuntimeError("В сцене нет узла %s. Проверьте namespace рига." % full)
    return full


def set_stepped_key(attr, frame, value):
    """Ключ со ступенчатой интерполяцией (для переключения текстур)."""
    cmds.setKeyframe(attr, time=frame, value=value)
    cmds.keyTangent(attr, time=(frame, frame), outTangentType="step")


def keyed_frames(attr, start=None, end=None):
    kwargs = {"query": True, "timeChange": True}
    if start is not None and end is not None:
        kwargs["time"] = (start, end)
    return cmds.keyframe(attr, **kwargs) or []


def keyable_attrs(ctrl):
    attrs = cmds.listAttr(ctrl, keyable=True, unlocked=True, scalar=True) or []
    out = []
    for a in attrs:
        plug = ctrl + "." + a
        try:
            if cmds.getAttr(plug, settable=True):
                out.append(a)
        except (RuntimeError, ValueError):
            pass
    return out


def warn(msg):
    cmds.warning("AnimAuto: " + msg)


def info(msg):
    print("AnimAuto: " + msg)
