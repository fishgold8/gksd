"""Имена узлов рига и настройки по умолчанию.

Всё, что зависит от конкретного рига, собрано здесь. Если риг переименуют
или появится другой персонаж, правьте только этот файл.
"""

# --- Лицо -------------------------------------------------------------------
FACE_CTRL = "Face_ctrl"
EYES_ATTR = "eyes"
MOUTH_ATTR = "Mouth"
EXPRESSIONS_ATTR = "Expressions"

# Как найти file-ноды с последовательностями текстур (по куску пути).
EYES_TEXTURE_HINT = "/eyes/"
MOUTH_TEXTURE_HINT = "/mouth/"

# Значение атрибута N показывает картинку с номером N + OFFSET
# (eye_01.png при eyes = 1). Если превью не совпадают с тем, что во вьюпорте,
# поменяйте сдвиг.
EYES_INDEX_OFFSET = 0
MOUTH_INDEX_OFFSET = 0

# --- Тело (AdvancedSkeleton) ------------------------------------------------
MAIN_CTRL = "Main"
CONTROL_SET = "ControlSet"

# FKIK-переключатели: имя -> (сторона, тип конечности)
FKIK_SWITCHES = {
    "FKIKArm_L": ("L", "Arm"),
    "FKIKArm_R": ("R", "Arm"),
    "FKIKLeg_L": ("L", "Leg"),
    "FKIKLeg_R": ("R", "Leg"),
}
FKIK_ATTR = "FKIKBlend"
FKIK_FK_VALUE = 0.0
FKIK_IK_VALUE = 10.0

# Запасные имена суставов, если на переключателе нет строк startJoint/...
LIMB_JOINTS = {
    "Arm": ("Shoulder", "Elbow", "Wrist"),
    "Leg": ("Hip", "Knee", "Ankle"),
}
# Дополнительные IK-контролы конечности, которые сбрасываются при FK -> IK.
LIMB_EXTRA_IK_CTRLS = {
    "Arm": (),
    "Leg": ("IKToes", "RollHeel", "RollToes", "RollToesEnd"),
}
# Насколько далеко от локтя/колена ставить pole vector (в длинах конечности).
POLE_DISTANCE = 0.5

# --- Зеркалирование ---------------------------------------------------------
# Правила по префиксу имени контрола: какие каналы инвертировать при переносе
# позы на другую сторону. Проверяются по порядку, срабатывает первое
# совпадение. В AdvancedSkeleton FK-суставы зеркальные по поведению, поэтому
# FK копируется как есть, а IK-контролы в мировой ориентации инвертируют
# tx, ry, rz.
MIRROR_RULES_SIDE = [
    ("IK", ("tx", "ry", "rz")),
    ("Pole", ("tx", "ry", "rz")),
    ("Roll", ()),
    ("FK", ()),
]
MIRROR_RULES_CENTER = [
    # Центральные контролы (_M) при отражении позы относительно YZ.
    ("RootX", ("tx", "ry", "rz")),
    ("IK", ("tx", "ry", "rz")),
    ("HipSwinger", ("ry", "rz")),
    ("FK", ("rx", "ry")),
]
SIDE_TOKENS = (("_L", "_R"), ("_R", "_L"))
CENTER_TOKEN = "_M"

# --- Моргание ---------------------------------------------------------------
BLINK_MIN_INTERVAL = 2.0   # секунды
BLINK_MAX_INTERVAL = 5.0
BLINK_DURATION = 3         # кадров с закрытыми глазами

# --- Липсинк ----------------------------------------------------------------
LIPSYNC_THRESHOLDS = (0.12, 0.35, 0.7)  # границы уровней громкости 0..1
LIPSYNC_MIN_HOLD = 2                    # минимум кадров на одну форму рта
LIPSYNC_SMOOTH = 1                      # радиус сглаживания в кадрах
JAW_CTRL = "FKJaw_M"
JAW_ATTR = "rz"
JAW_MAX_VALUE = 15.0

PRESETS_FILENAME = "animauto_face_presets.json"
