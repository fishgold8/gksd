"""Лицо: переключение глаз/рта/Expressions на Face_ctrl и пресеты эмоций."""

import json
import os
import re

from maya import cmds

from . import config
from .utils import node, set_stepped_key, undoable

FACE_ATTRS = (config.EYES_ATTR, config.MOUTH_ATTR, config.EXPRESSIONS_ATTR)
_OPTVAR_FOLDER = "animauto_texfolder_"


# --- Библиотека текстур ----------------------------------------------------

def _sequence_from_path(path):
    """'.../eye_01.png' -> (папка, префикс, расширение)."""
    folder, filename = os.path.split(path)
    m = re.match(r"^(.*?)(\d+)(\.\w+)$", filename)
    if not m:
        return None
    return folder, m.group(1), m.group(3)


def texture_path_for(kind):
    """Путь из file-ноды с последовательностью глаз ('eyes') или рта ('mouth')."""
    hint = config.EYES_TEXTURE_HINT if kind == "eyes" else config.MOUTH_TEXTURE_HINT
    for f in cmds.ls(type="file") or []:
        path = cmds.getAttr(f + ".fileTextureName") or ""
        if hint in path.replace("\\", "/").lower():
            return path
    return None


def set_folder_override(kind, folder):
    cmds.optionVar(stringValue=(_OPTVAR_FOLDER + kind, folder or ""))


def get_folder_override(kind):
    key = _OPTVAR_FOLDER + kind
    return cmds.optionVar(q=key) if cmds.optionVar(exists=key) else ""


def _candidate_folders(folder):
    """Папка из сцены, а если её нет — такая же папка внутри проекта."""
    yield folder
    root = cmds.workspace(q=True, rootDirectory=True)
    tail = os.path.basename(folder.rstrip("/\\"))
    for sub in ("sourceimages", "sourceimages/tex", ""):
        yield os.path.join(root, sub, tail)


def texture_library(kind):
    """[(значение атрибута, путь к картинке)] для глаз или рта, по возрастанию."""
    path = texture_path_for(kind)
    offset = config.EYES_INDEX_OFFSET if kind == "eyes" else config.MOUTH_INDEX_OFFSET
    seq = _sequence_from_path(path) if path else None
    prefix, ext = (seq[1], seq[2]) if seq else (("eye_" if kind == "eyes" else "mouth_"), ".png")
    folders = []
    override = get_folder_override(kind)
    if override:
        folders.append(override)
    if seq:
        folders.extend(_candidate_folders(seq[0]))
    pattern = re.compile(r"^%s(\d+)%s$" % (re.escape(prefix), re.escape(ext)), re.IGNORECASE)
    for folder in folders:
        if not os.path.isdir(folder):
            continue
        items = []
        for name in os.listdir(folder):
            m = pattern.match(name)
            if m:
                items.append((int(m.group(1)) - offset, os.path.join(folder, name)))
        if items:
            return sorted(items)
    return []


# --- Значения и ключи -----------------------------------------------------

def face_ctrl(ns):
    return node(ns, config.FACE_CTRL)


def attr_range(ns, attr):
    ctrl = face_ctrl(ns)
    lo = hi = None
    if cmds.attributeQuery(attr, node=ctrl, minExists=True):
        lo = cmds.attributeQuery(attr, node=ctrl, minimum=True)[0]
    if cmds.attributeQuery(attr, node=ctrl, maxExists=True):
        hi = cmds.attributeQuery(attr, node=ctrl, maximum=True)[0]
    return lo, hi


def get_face(ns, frame=None):
    ctrl = face_ctrl(ns)
    kwargs = {} if frame is None else {"time": frame}
    return {a: cmds.getAttr(ctrl + "." + a, **kwargs) for a in FACE_ATTRS}


@undoable
def set_face(ns, values, key=True, frame=None):
    """values: {'eyes': 3, 'Mouth': 2, 'Expressions': 0}; лишние ключи игнорируются."""
    ctrl = face_ctrl(ns)
    if frame is None:
        frame = cmds.currentTime(q=True)
    for attr in FACE_ATTRS:
        if attr not in values or values[attr] is None:
            continue
        plug = ctrl + "." + attr
        value = values[attr]
        if key:
            # Expressions управляет blendShape — его оставляем плавным
            if attr == config.EXPRESSIONS_ATTR:
                cmds.setKeyframe(plug, time=frame, value=value)
            else:
                set_stepped_key(plug, frame, value)
        else:
            cmds.setAttr(plug, value)


def face_subcontrols(ns):
    """Face_ctrl и все кривые-контролы под ним (смещения глаз, рта)."""
    ctrl = face_ctrl(ns)
    out = [ctrl]
    for child in cmds.listRelatives(ctrl, allDescendents=True, type="transform", fullPath=True) or []:
        if cmds.listRelatives(child, shapes=True, type="nurbsCurve"):
            out.append(cmds.ls(child)[0])
    return out


# --- Пресеты эмоций --------------------------------------------------------

def presets_path():
    return os.path.join(cmds.internalVar(userPrefDir=True), config.PRESETS_FILENAME)


def load_presets():
    path = presets_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_presets(presets):
    with open(presets_path(), "w", encoding="utf-8") as fh:
        json.dump(presets, fh, ensure_ascii=False, indent=2, sort_keys=True)


def save_current_as_preset(ns, name):
    presets = load_presets()
    presets[name] = get_face(ns)
    save_presets(presets)
    return presets


def delete_preset(name):
    presets = load_presets()
    presets.pop(name, None)
    save_presets(presets)
    return presets
