"""Окно AnimAuto: вкладки Лицо / Моргание / Липсинк / Тело."""

import os
import traceback

from maya import cmds
from maya import OpenMayaUI as omui

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance
except ImportError:  # Maya 2024 и старше
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance

from . import blink, body, config, face, lipsync, utils

WINDOW_NAME = "AnimAutoWindow"
THUMB = 72
_window = None


def maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)


def _report(func):
    """Ошибки показываем в строке состояния Maya, а не роняем окно."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — показываем любую ошибку пользователю
            traceback.print_exc()
            cmds.warning("AnimAuto: %s" % exc)
    return wrapper


class ThumbGrid(QtWidgets.QWidget):
    """Сетка кнопок-превью для выбора текстуры глаз или рта."""

    picked = QtCore.Signal(int)

    def __init__(self, columns=5, parent=None):
        super().__init__(parent)
        self.columns = columns
        self.layout_ = QtWidgets.QGridLayout(self)
        self.layout_.setSpacing(4)
        self.group = QtWidgets.QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = {}

    def populate(self, items):
        for btn in self.buttons.values():
            self.group.removeButton(btn)
            btn.deleteLater()
        self.buttons = {}
        if not items:
            label = QtWidgets.QLabel("Текстуры не найдены. Укажите папку кнопкой «Папка…».")
            label.setWordWrap(True)
            self.layout_.addWidget(label, 0, 0)
            self.buttons[None] = label
            return
        for n, (value, path) in enumerate(items):
            btn = QtWidgets.QToolButton()
            btn.setCheckable(True)
            btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            pix = QtGui.QPixmap(path)
            if not pix.isNull():
                # картинки 512x512 с рисунком в центре — показываем центральную часть
                side = int(min(pix.width(), pix.height()) * 0.6)
                rect = QtCore.QRect((pix.width() - side) // 2, (pix.height() - side) // 2, side, side)
                btn.setIcon(QtGui.QIcon(pix.copy(rect)))
                btn.setIconSize(QtCore.QSize(THUMB, THUMB))
            btn.setText(str(value))
            btn.setToolTip(os.path.basename(path))
            btn.clicked.connect(lambda _=False, v=value: self.picked.emit(v))
            self.group.addButton(btn)
            self.layout_.addWidget(btn, n // self.columns, n % self.columns)
            self.buttons[value] = btn

    def values(self):
        return [v for v in self.buttons if v is not None]

    def mark(self, value):
        btn = self.buttons.get(int(round(value))) if value is not None else None
        if isinstance(btn, QtWidgets.QToolButton):
            btn.setChecked(True)


def _value_combo(values, current=None):
    combo = QtWidgets.QComboBox()
    for v in values:
        combo.addItem(str(v), v)
    if current is not None:
        idx = combo.findData(current)
        if idx >= 0:
            combo.setCurrentIndex(idx)
    return combo


class AnimAutoWindow(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent or maya_main_window())
        self.setObjectName(WINDOW_NAME)
        self.setWindowTitle("AnimAuto — анимация Бати")
        self.setWindowFlags(QtCore.Qt.Window)
        self.resize(520, 720)

        root = QtWidgets.QVBoxLayout(self)
        ns_row = QtWidgets.QHBoxLayout()
        ns_row.addWidget(QtWidgets.QLabel("Риг (namespace):"))
        self.ns_combo = QtWidgets.QComboBox()
        self.ns_combo.setEditable(True)
        ns_row.addWidget(self.ns_combo, 1)
        refresh = QtWidgets.QPushButton("Обновить")
        refresh.clicked.connect(self.refresh)
        ns_row.addWidget(refresh)
        root.addLayout(ns_row)

        self.autokey = QtWidgets.QCheckBox("Ставить ключ при изменении")
        self.autokey.setChecked(True)
        root.addWidget(self.autokey)

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self._scroll(self._build_face()), "Лицо")
        tabs.addTab(self._build_blink(), "Моргание")
        tabs.addTab(self._build_lipsync(), "Липсинк")
        tabs.addTab(self._build_body(), "Тело")
        root.addWidget(tabs, 1)
        self.refresh()

    # --- общее -----------------------------------------------------------

    @staticmethod
    def _scroll(widget):
        area = QtWidgets.QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(widget)
        return area

    def ns(self):
        text = self.ns_combo.currentText().strip()
        if text in ("", "(без namespace)"):
            return ""
        return text if text.endswith(":") else text + ":"

    @_report
    def refresh(self):
        current = self.ns_combo.currentText()
        found = utils.find_rig_namespaces()
        self.ns_combo.clear()
        for ns in found:
            self.ns_combo.addItem(ns or "(без namespace)")
        sel_ns = utils.namespace_from_selection()
        if sel_ns and sel_ns in found:
            self.ns_combo.setCurrentIndex(found.index(sel_ns))
        elif current:
            idx = self.ns_combo.findText(current)
            if idx >= 0:
                self.ns_combo.setCurrentIndex(idx)
        self.eye_grid.populate(face.texture_library("eyes"))
        self.mouth_grid.populate(face.texture_library("mouth"))
        self._refresh_value_combos()
        self._refresh_presets()
        self._refresh_sounds()
        if found:
            self._sync_face()

    def _sync_face(self):
        try:
            values = face.get_face(self.ns())
        except RuntimeError:
            return
        self.eye_grid.mark(values[config.EYES_ATTR])
        self.mouth_grid.mark(values[config.MOUTH_ATTR])
        self.expr_slider.blockSignals(True)
        self.expr_slider.setValue(int(round(values[config.EXPRESSIONS_ATTR])))
        self.expr_slider.blockSignals(False)
        self.expr_label.setText(str(int(round(values[config.EXPRESSIONS_ATTR]))))

    # --- Лицо ------------------------------------------------------------

    def _build_face(self):
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)

        for kind, title in (("eyes", "Глаза"), ("mouth", "Рот")):
            box = QtWidgets.QGroupBox(title)
            bl = QtWidgets.QVBoxLayout(box)
            grid = ThumbGrid()
            attr = config.EYES_ATTR if kind == "eyes" else config.MOUTH_ATTR
            grid.picked.connect(lambda v, a=attr: self._set_face({a: v}))
            bl.addWidget(grid)
            folder_btn = QtWidgets.QPushButton("Папка…")
            folder_btn.clicked.connect(lambda _=False, k=kind: self._pick_folder(k))
            bl.addWidget(folder_btn, 0, QtCore.Qt.AlignRight)
            lay.addWidget(box)
            setattr(self, "eye_grid" if kind == "eyes" else "mouth_grid", grid)

        box = QtWidgets.QGroupBox("Expressions (blendShape головы)")
        el = QtWidgets.QHBoxLayout(box)
        self.expr_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.expr_slider.setRange(0, 21)
        self.expr_label = QtWidgets.QLabel("0")
        self.expr_slider.valueChanged.connect(lambda v: self.expr_label.setText(str(v)))
        self.expr_slider.sliderReleased.connect(
            lambda: self._set_face({config.EXPRESSIONS_ATTR: self.expr_slider.value()}))
        el.addWidget(self.expr_slider, 1)
        el.addWidget(self.expr_label)
        lay.addWidget(box)

        box = QtWidgets.QGroupBox("Пресеты эмоций (глаза + рот + Expressions)")
        pl = QtWidgets.QVBoxLayout(box)
        self.preset_list = QtWidgets.QListWidget()
        self.preset_list.itemDoubleClicked.connect(lambda _: self._apply_preset())
        pl.addWidget(self.preset_list)
        row = QtWidgets.QHBoxLayout()
        for text, slot in (("Применить", self._apply_preset),
                           ("Сохранить текущее…", self._save_preset),
                           ("Удалить", self._delete_preset)):
            b = QtWidgets.QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        pl.addLayout(row)
        lay.addWidget(box)
        lay.addStretch(1)
        return w

    @_report
    def _set_face(self, values):
        face.set_face(self.ns(), values, key=self.autokey.isChecked())
        self._sync_face()

    @_report
    def _pick_folder(self, kind):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Папка с текстурами")
        if folder:
            face.set_folder_override(kind, folder)
            self.refresh()

    def _refresh_presets(self):
        self.preset_list.clear()
        for name, values in sorted(face.load_presets().items()):
            item = QtWidgets.QListWidgetItem(
                "%s   (глаза %s, рот %s, expr %s)" % (
                    name, values.get(config.EYES_ATTR), values.get(config.MOUTH_ATTR),
                    values.get(config.EXPRESSIONS_ATTR)))
            item.setData(QtCore.Qt.UserRole, name)
            self.preset_list.addItem(item)

    def _selected_preset(self):
        item = self.preset_list.currentItem()
        return item.data(QtCore.Qt.UserRole) if item else None

    @_report
    def _apply_preset(self):
        name = self._selected_preset()
        if name:
            self._set_face(face.load_presets()[name])

    @_report
    def _save_preset(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "Пресет", "Название эмоции:")
        if ok and name.strip():
            face.save_current_as_preset(self.ns(), name.strip())
            self._refresh_presets()

    @_report
    def _delete_preset(self):
        name = self._selected_preset()
        if name:
            face.delete_preset(name)
            self._refresh_presets()

    def _refresh_value_combos(self):
        eyes = self.eye_grid.values() or list(range(1, 11))
        mouths = self.mouth_grid.values() or list(range(1, 11))
        for combo, values in ((self.blink_closed, eyes),) + tuple((c, mouths) for c in self.lip_levels):
            current = combo.currentData()
            combo.clear()
            for v in values:
                combo.addItem(str(v), v)
            idx = combo.findData(current)
            if idx < 0 and combo in self.lip_levels:
                # по умолчанию уровни громкости разносятся по разным ртам
                idx = min(self.lip_levels.index(combo), combo.count() - 1)
            if idx >= 0:
                combo.setCurrentIndex(idx)

    # --- Моргание --------------------------------------------------------

    def _build_blink(self):
        w = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(w)
        self.blink_closed = QtWidgets.QComboBox()
        form.addRow("Закрытые глаза (eyes):", self.blink_closed)

        self.blink_min = QtWidgets.QDoubleSpinBox()
        self.blink_min.setRange(0.3, 30)
        self.blink_min.setValue(config.BLINK_MIN_INTERVAL)
        self.blink_max = QtWidgets.QDoubleSpinBox()
        self.blink_max.setRange(0.3, 30)
        self.blink_max.setValue(config.BLINK_MAX_INTERVAL)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.blink_min)
        row.addWidget(QtWidgets.QLabel("—"))
        row.addWidget(self.blink_max)
        row.addWidget(QtWidgets.QLabel("сек"))
        form.addRow("Интервал:", row)

        self.blink_dur = QtWidgets.QSpinBox()
        self.blink_dur.setRange(1, 24)
        self.blink_dur.setValue(config.BLINK_DURATION)
        form.addRow("Длительность (кадров):", self.blink_dur)

        self.blink_seed = QtWidgets.QSpinBox()
        self.blink_seed.setRange(0, 99999)
        form.addRow("Seed (0 = случайно):", self.blink_seed)

        self.blink_respect = QtWidgets.QCheckBox("Не трогать места, где уже есть ключи глаз")
        self.blink_respect.setChecked(True)
        form.addRow(self.blink_respect)
        form.addRow(QtWidgets.QLabel("Диапазон — текущий playback range."))

        row = QtWidgets.QHBoxLayout()
        add = QtWidgets.QPushButton("Расставить моргания")
        add.clicked.connect(self._add_blinks)
        rem = QtWidgets.QPushButton("Удалить моргания")
        rem.clicked.connect(self._remove_blinks)
        row.addWidget(add)
        row.addWidget(rem)
        form.addRow(row)
        return w

    @_report
    def _add_blinks(self):
        start, end = utils.playback_range()
        seed = self.blink_seed.value() or None
        frames = blink.add_blinks(
            self.ns(), self.blink_closed.currentData(), start, end,
            self.blink_min.value(), self.blink_max.value(), self.blink_dur.value(),
            seed, self.blink_respect.isChecked())
        utils.info("моргания на кадрах: %s" % (frames or "нет"))

    @_report
    def _remove_blinks(self):
        start, end = utils.playback_range()
        n = blink.remove_blinks(self.ns(), self.blink_closed.currentData(), start, end)
        utils.info("удалено морганий: %d" % n)

    # --- Липсинк ---------------------------------------------------------

    def _build_lipsync(self):
        w = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(w)

        self.sound_combo = QtWidgets.QComboBox()
        self.sound_combo.currentIndexChanged.connect(self._sound_picked)
        form.addRow("Звук из сцены:", self.sound_combo)

        row = QtWidgets.QHBoxLayout()
        self.wav_edit = QtWidgets.QLineEdit()
        browse = QtWidgets.QPushButton("…")
        browse.clicked.connect(self._browse_wav)
        row.addWidget(self.wav_edit, 1)
        row.addWidget(browse)
        form.addRow("WAV-файл:", row)

        self.wav_offset = QtWidgets.QSpinBox()
        self.wav_offset.setRange(-100000, 100000)
        form.addRow("Начало (кадр):", self.wav_offset)

        labels = ("Тишина", "Тихо", "Средне", "Громко")
        self.lip_levels = []
        for label in labels:
            combo = QtWidgets.QComboBox()
            self.lip_levels.append(combo)
            form.addRow("Рот — %s:" % label, combo)

        self.lip_sens = QtWidgets.QDoubleSpinBox()
        self.lip_sens.setRange(0.2, 3.0)
        self.lip_sens.setSingleStep(0.1)
        self.lip_sens.setValue(1.0)
        self.lip_sens.setToolTip("Больше — рот открывается от более тихого звука")
        form.addRow("Чувствительность:", self.lip_sens)

        self.lip_hold = QtWidgets.QSpinBox()
        self.lip_hold.setRange(1, 12)
        self.lip_hold.setValue(config.LIPSYNC_MIN_HOLD)
        form.addRow("Мин. кадров на форму:", self.lip_hold)

        self.lip_clear = QtWidgets.QCheckBox("Удалить старые ключи рта в этом диапазоне")
        self.lip_clear.setChecked(True)
        form.addRow(self.lip_clear)

        self.lip_jaw = QtWidgets.QCheckBox("Открывать челюсть (%s.%s)" % (config.JAW_CTRL, config.JAW_ATTR))
        self.lip_jaw_max = QtWidgets.QDoubleSpinBox()
        self.lip_jaw_max.setRange(-90, 90)
        self.lip_jaw_max.setValue(config.JAW_MAX_VALUE)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.lip_jaw)
        row.addWidget(QtWidgets.QLabel("макс:"))
        row.addWidget(self.lip_jaw_max)
        form.addRow(row)

        row = QtWidgets.QHBoxLayout()
        imp = QtWidgets.QPushButton("Добавить звук в сцену")
        imp.clicked.connect(self._import_sound)
        go = QtWidgets.QPushButton("Сделать липсинк")
        go.clicked.connect(self._apply_lipsync)
        row.addWidget(imp)
        row.addWidget(go)
        form.addRow(row)
        return w

    def _refresh_sounds(self):
        self.sound_combo.blockSignals(True)
        self.sound_combo.clear()
        self.sound_combo.addItem("— выбрать файл вручную —", None)
        for snd, path, offset in lipsync.scene_sounds():
            self.sound_combo.addItem("%s  (%s)" % (snd, os.path.basename(path)), (path, offset))
        self.sound_combo.blockSignals(False)
        if self.sound_combo.count() > 1 and not self.wav_edit.text():
            self.sound_combo.setCurrentIndex(1)
            self._sound_picked(1)

    def _sound_picked(self, index):
        data = self.sound_combo.itemData(index)
        if data:
            self.wav_edit.setText(data[0])
            self.wav_offset.setValue(int(round(data[1])))

    def _browse_wav(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Звук", "", "WAV (*.wav)")
        if path:
            self.wav_edit.setText(path)

    @_report
    def _import_sound(self):
        path = self.wav_edit.text().strip()
        if path:
            lipsync.import_sound(path, self.wav_offset.value())
            self._refresh_sounds()

    @_report
    def _apply_lipsync(self):
        k = self.lip_sens.value()
        thresholds = tuple(min(0.99, t / k) for t in config.LIPSYNC_THRESHOLDS)
        jaw = ((config.JAW_CTRL + "." + config.JAW_ATTR), self.lip_jaw_max.value()) \
            if self.lip_jaw.isChecked() else None
        start, end, n = lipsync.apply_lipsync(
            self.ns(), self.wav_edit.text().strip(),
            [c.currentData() for c in self.lip_levels],
            offset=self.wav_offset.value(), thresholds=thresholds,
            min_hold=self.lip_hold.value(), clear_existing=self.lip_clear.isChecked(), jaw=jaw)
        utils.info("липсинк: кадры %d–%d, ключей рта: %d" % (start, end, n))

    # --- Тело ------------------------------------------------------------

    def _build_body(self):
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)

        self.body_selected = QtWidgets.QCheckBox("Только выделенные контролы")
        lay.addWidget(self.body_selected)

        box = QtWidgets.QGroupBox("Поза и ключи")
        grid = QtWidgets.QGridLayout(box)
        buttons = (
            ("Выделить все контролы", lambda: body.select_all(self.ns())),
            ("Ключ на контролы", lambda: body.key_controls(self.ns(), self.body_selected.isChecked())),
            ("Сбросить позу", lambda: body.reset_pose(self.ns(), self.body_selected.isChecked())),
            ("Зеркалить выделенное →", lambda: body.mirror_selected(self.ns())),
            ("Отразить позу (L↔R)", lambda: body.flip_pose(self.ns(), self.body_selected.isChecked())),
        )
        for n, (text, fn) in enumerate(buttons):
            b = QtWidgets.QPushButton(text)
            b.clicked.connect(_report(fn))
            grid.addWidget(b, n // 2, n % 2)
        lay.addWidget(box)

        box = QtWidgets.QGroupBox("FK / IK с подгонкой позы (без скачка)")
        grid = QtWidgets.QGridLayout(box)
        self.fkik_key = QtWidgets.QCheckBox("Ставить ключи на кадре переключения")
        self.fkik_key.setChecked(True)
        grid.addWidget(self.fkik_key, 0, 0, 1, 3)
        titles = {"FKIKArm_L": "Рука L", "FKIKArm_R": "Рука R",
                  "FKIKLeg_L": "Нога L", "FKIKLeg_R": "Нога R"}
        for row, switch in enumerate(config.FKIK_SWITCHES, start=1):
            grid.addWidget(QtWidgets.QLabel(titles.get(switch, switch)), row, 0)
            for col, (text, to_ik) in enumerate((("→ FK", False), ("→ IK", True)), start=1):
                b = QtWidgets.QPushButton(text)
                b.clicked.connect(_report(
                    lambda _=False, s=switch, t=to_ik: body.switch_fkik(
                        self.ns(), s, t, self.fkik_key.isChecked())))
                grid.addWidget(b, row, col)
        lay.addWidget(box)
        lay.addStretch(1)
        return w


def show():
    global _window
    if _window is not None:
        try:
            _window.close()
            _window.deleteLater()
        except RuntimeError:
            pass
    _window = AnimAutoWindow()
    _window.show()
    return _window
