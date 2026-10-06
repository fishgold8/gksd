"""Тело: контролы AdvancedSkeleton, сброс позы, ключи, зеркало, FK/IK."""

from maya import cmds

from . import config, logic
from .utils import keyable_attrs, undoable, warn

IK_RESET_ATTRS = ("swivel", "roll", "rock")


# --- Контролы ---------------------------------------------------------------

def all_controls(ns):
    """Все контролы рига: из ControlSet, иначе — кривые под Main."""
    ctrl_set = ns + config.CONTROL_SET
    ctrls = []
    if cmds.objExists(ctrl_set):
        ctrls = cmds.sets(ctrl_set, q=True) or []
    else:
        main = ns + config.MAIN_CTRL
        if cmds.objExists(main):
            ctrls = [main]
            for shape in cmds.listRelatives(main, allDescendents=True, type="nurbsCurve", fullPath=True) or []:
                parent = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
                if not cmds.getAttr(shape + ".intermediateObject"):
                    ctrls.append(parent)
    ctrls = [c for c in cmds.ls(ctrls, type="transform") if keyable_attrs(c)]
    face = ns + config.FACE_CTRL
    if cmds.objExists(face) and face not in ctrls:
        from .face import face_subcontrols
        ctrls.extend(c for c in face_subcontrols(ns) if c not in ctrls)
    return sorted(set(ctrls))


def target_controls(ns, selected_only):
    if selected_only:
        sel = cmds.ls(selection=True, type="transform") or []
        if not sel:
            raise RuntimeError("Ничего не выделено.")
        return sel
    return all_controls(ns)


def select_all(ns):
    cmds.select(all_controls(ns), replace=True)


@undoable
def key_controls(ns, selected_only=False):
    ctrls = target_controls(ns, selected_only)
    cmds.setKeyframe(ctrls)
    return len(ctrls)


@undoable
def reset_pose(ns, selected_only=False):
    """Все каналы контролов -> значения по умолчанию."""
    count = 0
    for ctrl in target_controls(ns, selected_only):
        for attr in keyable_attrs(ctrl):
            if attr == config.FKIK_ATTR or attr.startswith("follow"):
                continue  # режим FK/IK и follow — это настройки, а не поза
            default = cmds.attributeQuery(attr, node=ctrl, listDefault=True)
            if default is None:
                continue
            try:
                cmds.setAttr(ctrl + "." + attr, default[0])
                count += 1
            except RuntimeError:
                pass
    return count


# --- Зеркало ----------------------------------------------------------------

def _read(ctrl):
    return {a: cmds.getAttr(ctrl + "." + a) for a in keyable_attrs(ctrl)}


def _write(ctrl, values, flips):
    available = set(keyable_attrs(ctrl))
    for attr, value in values.items():
        if attr not in available:
            continue
        if attr in flips:
            value = -value
        try:
            cmds.setAttr(ctrl + "." + attr, value)
        except RuntimeError:
            pass


@undoable
def mirror_selected(ns=None):
    """Переносит позу выделенных контролов на противоположную сторону."""
    sel = cmds.ls(selection=True, type="transform") or []
    if not sel:
        raise RuntimeError("Выделите контролы одной стороны.")
    done = 0
    for ctrl in sel:
        other = logic.opposite_name(ctrl, config.SIDE_TOKENS)
        if not other or not cmds.objExists(other):
            continue
        _write(other, _read(ctrl), logic.flip_attrs(ctrl, config.MIRROR_RULES_SIDE))
        done += 1
    return done


@undoable
def flip_pose(ns, selected_only=False):
    """Отражает позу: левая и правая стороны меняются, центр отражается."""
    ctrls = target_controls(ns, selected_only)
    snapshot = {c: _read(c) for c in ctrls}
    for ctrl in ctrls:
        other = logic.opposite_name(ctrl, config.SIDE_TOKENS)
        if other:
            if not cmds.objExists(other):
                continue
            values = snapshot[ctrl]
            _write(other, values, logic.flip_attrs(ctrl, config.MIRROR_RULES_SIDE))
        elif logic.split_namespace(ctrl)[1].endswith(config.CENTER_TOKEN):
            _write(ctrl, snapshot[ctrl], logic.flip_attrs(ctrl, config.MIRROR_RULES_CENTER))
    return len(ctrls)


# --- FK / IK ----------------------------------------------------------------

def limb_joints(ns, switch, limb):
    plug_base = ns + switch
    names = []
    for attr in ("startJoint", "middleJoint", "endJoint"):
        value = None
        if cmds.attributeQuery(attr, node=plug_base, exists=True):
            value = cmds.getAttr(plug_base + "." + attr)
        names.append(value)
    if not all(names):
        names = list(config.LIMB_JOINTS[limb])
    return names


def is_ik(ns, switch):
    return cmds.getAttr(ns + switch + "." + config.FKIK_ATTR) > (config.FKIK_IK_VALUE / 2.0)


def _limb_ctrls(ns, switch):
    side, limb = config.FKIK_SWITCHES[switch]
    joints = limb_joints(ns, switch, limb)
    fk = [ns + "FK%s_%s" % (j, side) for j in joints]
    ik = [ns + "IK%s_%s" % (limb, side), ns + "Pole%s_%s" % (limb, side)]
    ik += [ns + "%s_%s" % (n, side) for n in config.LIMB_EXTRA_IK_CTRLS[limb]]
    return [c for c in fk + ik if cmds.objExists(c)]


def _key_limb(ns, switch, frame):
    cmds.setKeyframe(_limb_ctrls(ns, switch) + [ns + switch], time=frame)


@undoable
def switch_fkik(ns, switch, to_ik=None, key=True):
    """Переключает конечность FK<->IK, подгоняя позу, чтобы не было скачка.

    to_ik=None — переключить в противоположный режим.
    """
    side, limb = config.FKIK_SWITCHES[switch]
    if not cmds.objExists(ns + switch):
        raise RuntimeError("Нет переключателя %s%s" % (ns, switch))
    if to_ik is None:
        to_ik = not is_ik(ns, switch)
    frame = cmds.currentTime(q=True)
    if key:
        # фиксируем текущую позу на предыдущем кадре, чтобы переключение было ступенькой
        _key_limb(ns, switch, frame - 1)

    joints = limb_joints(ns, switch, limb)
    bind = [ns + "%s_%s" % (j, side) for j in joints]
    missing = [b for b in bind if not cmds.objExists(b)]
    if missing:
        raise RuntimeError("Не найдены суставы: %s" % ", ".join(missing))

    if to_ik:
        ik_ctrl = ns + "IK%s_%s" % (limb, side)
        pole = ns + "Pole%s_%s" % (limb, side)
        for attr in IK_RESET_ATTRS:
            if cmds.attributeQuery(attr, node=ik_ctrl, exists=True):
                cmds.setAttr(ik_ctrl + "." + attr, 0)
        for extra in config.LIMB_EXTRA_IK_CTRLS[limb]:
            name = ns + "%s_%s" % (extra, side)
            if cmds.objExists(name):
                for attr in keyable_attrs(name):
                    default = cmds.attributeQuery(attr, node=name, listDefault=True)
                    if default is not None:
                        cmds.setAttr(name + "." + attr, default[0])
        align = ns + "AlignIKTo%s_%s" % (joints[2], side)
        target = align if cmds.objExists(align) else bind[2]
        if target != align:
            warn("нет %s, IK ставится по суставу (ориентация может отличаться)" % align)
        cmds.matchTransform(ik_ctrl, target, position=True, rotation=True)
        if cmds.objExists(pole):
            pts = [cmds.xform(b, q=True, worldSpace=True, translation=True) for b in bind]
            pos = logic.pole_vector_position(pts[0], pts[1], pts[2], config.POLE_DISTANCE)
            cmds.xform(pole, worldSpace=True, translation=pos)
        cmds.setAttr(ns + switch + "." + config.FKIK_ATTR, config.FKIK_IK_VALUE)
    else:
        for j, b in zip(joints, bind):
            fk = ns + "FK%s_%s" % (j, side)
            if cmds.objExists(fk):
                cmds.matchTransform(fk, b, rotation=True)
        cmds.setAttr(ns + switch + "." + config.FKIK_ATTR, config.FKIK_FK_VALUE)

    if key:
        _key_limb(ns, switch, frame)
    return to_ik
