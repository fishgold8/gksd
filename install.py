"""Установка AnimAuto: перетащите этот файл во вьюпорт Maya.

Создаётся .mod-файл (Maya будет находить аддон при каждом запуске)
и кнопка AnimAuto на текущей полке.
"""

import os
import sys

from maya import cmds, mel

MODULE_NAME = "AnimAuto"
SHELF_COMMAND = "import animauto.ui\nanimauto.ui.show()"


def install():
    root = os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")
    scripts = root + "/scripts"
    modules_dir = os.path.join(cmds.internalVar(userAppDir=True), "modules")
    os.makedirs(modules_dir, exist_ok=True)
    with open(os.path.join(modules_dir, MODULE_NAME + ".mod"), "w") as fh:
        fh.write("+ %s 1.0 %s\n" % (MODULE_NAME, root))

    # в текущей сессии путь добавляем сразу, без перезапуска
    if scripts not in sys.path:
        sys.path.insert(0, scripts)

    shelf_top = mel.eval("$tmp = $gShelfTopLevel")
    shelf = cmds.tabLayout(shelf_top, q=True, selectTab=True)
    for btn in cmds.shelfLayout(shelf, q=True, childArray=True) or []:
        if cmds.shelfButton(btn, q=True, exists=True) and \
                cmds.shelfButton(btn, q=True, label=True) == MODULE_NAME:
            cmds.deleteUI(btn)
    cmds.shelfButton(parent=shelf, label=MODULE_NAME, imageOverlayLabel="Anim",
                     image="pythonFamily.png", annotation="AnimAuto — анимация Бати",
                     command=SHELF_COMMAND, sourceType="python")
    cmds.confirmDialog(title=MODULE_NAME, button=["OK"],
                       message="AnimAuto установлен.\nКнопка «Anim» добавлена на полку «%s»." % shelf)

    import animauto.ui
    animauto.ui.show()


def onMayaDroppedPythonFile(*_):
    install()
