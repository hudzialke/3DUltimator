import json
import argparse
from pathlib import Path
import sys
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from PySide6.QtCore import QEvent, QPointF, Qt, QAbstractTableModel, QModelIndex, QTimer, QSettings
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from vispy import scene
from vispy.app import use_app

import pyqtgraph as pg

from package_library import PackageLibrary, SavedPackage
from packing import LayoutIssue, PackItem, PackedBox, pack_single_bin, validate_layout
from manual_layout import inside, snap_drag_delta
from i18n import apply_translations, configure_qt_language, language, set_language, tr
from version import __version__

use_app("pyside6")


@dataclass
class PackageType:
    count: int
    dx: int
    dy: int
    dz: int
    stackable: bool
    rot_x: bool
    rot_y: bool
    rot_z: bool


@dataclass
class PlacedBox:
    position: Tuple[float, float, float]
    size: Tuple[float, float, float]
    color: Tuple[float, float, float, float]
    package_index: int
    overflow: bool = False


@dataclass
class UndoState:
    packages: List[PackageType]
    boxes: List[PlacedBox]


def _yn(flag: bool) -> str:
    return tr("Tak" if flag else "Nie")


def package_to_saved(pkg: PackageType) -> SavedPackage:
    return SavedPackage(
        dx=pkg.dx,
        dy=pkg.dy,
        dz=pkg.dz,
        count=pkg.count,
        stackable=pkg.stackable,
        rot_x=pkg.rot_x,
        rot_y=pkg.rot_y,
        rot_z=pkg.rot_z,
    )


def saved_to_package(saved: SavedPackage) -> PackageType:
    return PackageType(
        count=saved.count,
        dx=saved.dx,
        dy=saved.dy,
        dz=saved.dz,
        stackable=saved.stackable,
        rot_x=saved.rot_x,
        rot_y=saved.rot_y,
        rot_z=saved.rot_z,
    )


class PackageDialog(QDialog):
    """Formularz dodawania / edycji typu paczki."""

    def __init__(
        self,
        parent=None,
        package: PackageType | None = None,
        *,
        library: PackageLibrary | None = None,
        mark_favorite: bool | None = None,
    ):
        super().__init__(parent)
        editing = package is not None
        self.setWindowTitle("Edytuj typ paczki" if editing else "Dodaj typ paczki")
        self.setModal(True)
        self.setMinimumWidth(360)
        self._library = library

        root = QVBoxLayout(self)

        form = QFormLayout()
        self.spin_count = QSpinBox()
        self.spin_count.setRange(1, 9999)
        self.spin_count.setValue(package.count if package else 1)
        self.spin_count.setSuffix(" szt.")
        form.addRow("Ilość sztuk:", self.spin_count)
        root.addLayout(form)

        dims = QGroupBox("Wymiary paczki [cm]")
        dims_form = QFormLayout(dims)
        self.spin_dx = QSpinBox()
        self.spin_dy = QSpinBox()
        self.spin_dz = QSpinBox()
        for spin, val in (
            (self.spin_dx, package.dx if package else 50),
            (self.spin_dy, package.dy if package else 50),
            (self.spin_dz, package.dz if package else 50),
        ):
            spin.setRange(1, 2000)
            spin.setSuffix(" cm")
            spin.setValue(val)
        dims_form.addRow("X (długość):", self.spin_dx)
        dims_form.addRow("Y (szerokość):", self.spin_dy)
        dims_form.addRow("Z (wysokość):", self.spin_dz)
        root.addWidget(dims)

        opts = QGroupBox("Opcje układania")
        opts_layout = QVBoxLayout(opts)
        self.chk_stackable = QCheckBox("Piętrowalna (można stawiać coś na wierzchu)")
        self.chk_stackable.setChecked(package.stackable if package else True)
        opts_layout.addWidget(self.chk_stackable)

        opts_layout.addWidget(QLabel("Dozwolone obroty o 90°:"))
        self.chk_rot_x = QCheckBox("Wokół osi X (zamiana Y ↔ Z)")
        self.chk_rot_y = QCheckBox("Wokół osi Y (zamiana X ↔ Z)")
        self.chk_rot_z = QCheckBox("Wokół osi Z (zamiana X ↔ Y)")
        self.chk_rot_x.setChecked(package.rot_x if package else True)
        self.chk_rot_y.setChecked(package.rot_y if package else True)
        self.chk_rot_z.setChecked(package.rot_z if package else True)
        opts_layout.addWidget(self.chk_rot_x)
        opts_layout.addWidget(self.chk_rot_y)
        opts_layout.addWidget(self.chk_rot_z)
        root.addWidget(opts)

        fav_default = False
        if mark_favorite is not None:
            fav_default = mark_favorite
        elif package is not None and library is not None:
            fav_default = library.is_favorite(package_to_saved(package))
        self.chk_favorite = QCheckBox("★ Ulubiona (zapisz na liście ulubionych)")
        self.chk_favorite.setChecked(fav_default)
        root.addWidget(self.chk_favorite)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Zapisz")
        buttons.button(QDialogButtonBox.Cancel).setText("Anuluj")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        apply_translations(self)

    def result_package(self) -> PackageType:
        return PackageType(
            count=self.spin_count.value(),
            dx=self.spin_dx.value(),
            dy=self.spin_dy.value(),
            dz=self.spin_dz.value(),
            stackable=self.chk_stackable.isChecked(),
            rot_x=self.chk_rot_x.isChecked(),
            rot_y=self.chk_rot_y.isChecked(),
            rot_z=self.chk_rot_z.isChecked(),
        )

    def want_favorite(self) -> bool:
        return self.chk_favorite.isChecked()


class PackageLibraryDialog(QDialog):
    """Lista historii lub ulubionych — przywrócenie do puli typów paczek."""

    def __init__(
        self,
        parent,
        library: PackageLibrary,
        *,
        mode: str,
    ):
        super().__init__(parent)
        self.library = library
        self.mode = mode  # "history" | "favorites"
        self.selected: SavedPackage | None = None

        if mode == "favorites":
            self.setWindowTitle("Ulubione paczki ★")
            empty_msg = "Brak ulubionych. Oznacz paczkę gwiazdką przy dodawaniu/edycji."
        else:
            self.setWindowTitle("Historia paczek")
            empty_msg = "Historia jest pusta. Dodane typy paczek pojawią się tutaj."

        self.setModal(True)
        self.resize(560, 420)
        root = QVBoxLayout(self)

        tip = QLabel(
            "Zaznacz wpis i kliknij „Dodaj do puli”, albo dwukrotnie kliknij wiersz.\n"
            "Historia i ulubione są zapamiętane po zamknięciu programu."
        )
        tip.setWordWrap(True)
        tip.setStyleSheet("color: #555;")
        root.addWidget(tip)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._accept_current)
        root.addWidget(self.list_widget, 1)

        self.empty_label = QLabel(empty_msg)
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet("color: #888; padding: 8px;")
        root.addWidget(self.empty_label)

        row = QHBoxLayout()
        self.btn_favorite = QPushButton("★ Ulubiona")
        self.btn_favorite.clicked.connect(self._toggle_favorite)
        self.btn_remove = QPushButton("Usuń z listy")
        self.btn_remove.clicked.connect(self._remove_current)
        self.btn_add = QPushButton("Dodaj do puli")
        self.btn_add.clicked.connect(self._accept_current)
        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(self.reject)
        row.addWidget(self.btn_favorite)
        row.addWidget(self.btn_remove)
        row.addStretch(1)
        row.addWidget(self.btn_add)
        row.addWidget(btn_close)
        root.addLayout(row)

        self._reload()
        apply_translations(self)

    def _items(self) -> list[SavedPackage]:
        return self.library.favorites if self.mode == "favorites" else self.library.history

    def _reload(self) -> None:
        self.list_widget.clear()
        items = self._items()
        self.empty_label.setVisible(len(items) == 0)
        self.list_widget.setVisible(len(items) > 0)
        for saved in items:
            star = "★ " if self.library.is_favorite(saved) else ""
            text = f"{star}{saved.label()}"
            if saved.last_used:
                text += tr("\n    ostatnio: {last_used}", last_used=saved.last_used)
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, saved)
            self.list_widget.addItem(item)
        self.btn_favorite.setVisible(self.mode == "history")
        self.btn_favorite.setText(tr("★ Dodaj do ulubionych" if self.mode == "history" else "★ Ulubiona"))

    def _current_saved(self) -> SavedPackage | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _current_index(self) -> int:
        return self.list_widget.currentRow()

    def _toggle_favorite(self) -> None:
        saved = self._current_saved()
        if saved is None:
            return
        if self.library.is_favorite(saved):
            self.library.set_favorite(saved, False)
        else:
            self.library.set_favorite(saved, True)
        self._reload()

    def _remove_current(self) -> None:
        idx = self._current_index()
        if idx < 0:
            return
        if self.mode == "favorites":
            self.library.remove_favorite(idx)
        else:
            self.library.remove_from_history(idx)
        self._reload()

    def _accept_current(self) -> None:
        saved = self._current_saved()
        if saved is None:
            QMessageBox.information(self, tr("Wybór"), tr("Zaznacz paczkę na liście."))
            return
        self.selected = saved
        self.accept()


class PackageTableModel(QAbstractTableModel):
    """Tylko podgląd listy — dodawanie/edycja przez PackageDialog."""

    headers = [
        "Ilość",
        "X [cm]",
        "Y [cm]",
        "Z [cm]",
        "Piętrowalna",
        "Rot X",
        "Rot Y",
        "Rot Z",
    ]

    def __init__(self, packages: List[PackageType] | None = None):
        super().__init__()
        self.packages: List[PackageType] = packages or []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.packages)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        pkg = self.packages[index.row()]
        col = index.column()
        if col == 0:
            return pkg.count
        if col == 1:
            return pkg.dx
        if col == 2:
            return pkg.dy
        if col == 3:
            return pkg.dz
        if col == 4:
            return _yn(pkg.stackable)
        if col == 5:
            return _yn(pkg.rot_x)
        if col == 6:
            return _yn(pkg.rot_y)
        if col == 7:
            return _yn(pkg.rot_z)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal and 0 <= section < len(self.headers):
            return tr(self.headers[section])
        return None

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def addPackageType(self, pkg: PackageType):
        self.beginInsertRows(QModelIndex(), len(self.packages), len(self.packages))
        self.packages.append(pkg)
        self.endInsertRows()

    def updatePackageType(self, row: int, pkg: PackageType):
        if row < 0 or row >= len(self.packages):
            return
        self.packages[row] = pkg
        left = self.index(row, 0)
        right = self.index(row, self.columnCount() - 1)
        self.dataChanged.emit(left, right)


class MainWindow(QMainWindow):
    def __init__(self, *, settings=None, library=None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings(
            QSettings.IniFormat, QSettings.UserScope, "3DUltimator", "settings")
        set_language(self.settings.value("language", "pl"))
        configure_qt_language()
        self.setWindowTitle("3D Ultimator")
        self.resize(1500, 900)

        pg.setConfigOptions(antialias=True)

        self.container_x = 485
        self.container_y = 220
        self.container_z = 245

        self.package_colors: list[tuple[int, int, int]] = [
            (220, 70, 70),
            (60, 170, 80),
            (60, 100, 220),
            (230, 180, 40),
            (180, 60, 180),
            (40, 180, 180),
            (160, 80, 40),
            (80, 140, 40),
            (80, 80, 160),
            (180, 160, 40),
            (140, 60, 140),
            (40, 140, 140),
            (160, 160, 160),
            (120, 120, 120),
            (230, 120, 40),
            (40, 120, 230),
        ]

        self.package_model = PackageTableModel(
            [PackageType(40, 30, 60, 30, True, True, True, True)]
        )
        self.package_library = library if library is not None else PackageLibrary()

        self.placed_boxes: List[PlacedBox] = []
        self.undo_stack: List[UndoState] = []
        self.selected_indices: set[int] = set()
        self.layout_issues: list[LayoutIssue] = []
        self._invalid_indices: set[int] = set()
        self._top_view_texts: list[pg.TextItem] = []
        self._top_view_issue_markers: list[pg.TextItem] = []
        self._drag_active = False
        self._drag_started = False
        self._drag_selection: list[int] = []
        self._drag_start_widget: QPointF | None = None
        self._drag_start_xy: tuple[float, float] | None = None
        self._drag_start_positions: dict[int, Tuple[float, float, float]] = {}
        self._drag_original_snapshot: UndoState | None = None
        self._drag_pending = None
        self._drag_timer = QTimer(self)
        self._drag_timer.setSingleShot(True)
        self._drag_timer.setInterval(16)
        self._drag_timer.timeout.connect(self._apply_pending_drag)
        self._top_box_items = {}
        self._side_box_items = {}
        self._box_visuals_3d = {}

        self.top_view_boxes: List[pg.PlotCurveItem] = []
        self.top_view_container: pg.PlotCurveItem | None = None
        self.side_view_boxes: List[pg.PlotCurveItem] = []
        self.side_view_container: pg.PlotCurveItem | None = None

        central = QWidget()
        self.setCentralWidget(central)
        self._create_menu()

        root = QHBoxLayout(central)

        # --- Left controls ---
        controls = QVBoxLayout()
        root.addLayout(controls, 1)

        controls.addWidget(QLabel("Wymiary przestrzeni ładunkowej [cm]:"))

        self.spin_x = QSpinBox()
        self.spin_y = QSpinBox()
        self.spin_z = QSpinBox()
        for spin in (self.spin_x, self.spin_y, self.spin_z):
            spin.setRange(1, 2000)
        self.spin_x.setValue(self.container_x)
        self.spin_y.setValue(self.container_y)
        self.spin_z.setValue(self.container_z)

        controls.addWidget(QLabel("X (długość)"))
        controls.addWidget(self.spin_x)
        controls.addWidget(QLabel("Y (szerokość)"))
        controls.addWidget(self.spin_y)
        controls.addWidget(QLabel("Z (wysokość)"))
        controls.addWidget(self.spin_z)

        controls.addWidget(QLabel("Typy paczek (lista — edycja w osobnym oknie):"))
        self.table = QTableView()
        self.table.setModel(self.package_model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_package_type)
        delete_type = QAction("Usuń typ paczki", self.table)
        delete_type.setShortcut("Delete")
        delete_type.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        delete_type.triggered.connect(self.remove_selected_package_type)
        self.table.addAction(delete_type)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
        controls.addWidget(self.table, 1)

        btns = QHBoxLayout()
        btn_add = QPushButton("Dodaj typ paczki…")
        btn_add.clicked.connect(self.add_package_type)
        btn_edit = QPushButton("Edytuj…")
        btn_edit.clicked.connect(self.edit_package_type)
        btn_del = QPushButton("Usuń")
        btn_del.clicked.connect(self.remove_selected_package_type)
        btns.addWidget(btn_add)
        btns.addWidget(btn_edit)
        btns.addWidget(btn_del)
        controls.addLayout(btns)

        lib_btns = QHBoxLayout()
        btn_history = QPushButton("Historia…")
        btn_history.setToolTip("Paczki używane wcześniej — przywróć do puli")
        btn_history.clicked.connect(self.open_history)
        btn_fav = QPushButton("★ Ulubione…")
        btn_fav.setToolTip("Zapisane ulubione typy paczek")
        btn_fav.clicked.connect(self.open_favorites)
        lib_btns.addWidget(btn_history)
        lib_btns.addWidget(btn_fav)
        controls.addLayout(lib_btns)

        self.chk_show_overflow = QCheckBox("Pokazuj paczki, które się nie zmieściły")
        self.chk_show_overflow.setChecked(True)
        self.chk_show_overflow.stateChanged.connect(self.redraw_boxes)
        controls.addWidget(self.chk_show_overflow)

        btn_compute = QPushButton("Oblicz ułożenie paczek")
        btn_compute.setToolTip("Przelicza cały układ od zera (auto).")
        btn_compute.clicked.connect(self.compute_packing)
        controls.addWidget(btn_compute)

        btn_spawn = QPushButton("Wstaw nowe bez układu")
        btn_spawn.setToolTip(
            "Dodaje brakujące sztuki z listy typów obok busy (overflow),\n"
            "bez ruszania już ułożonych paczek. Potem przeciągnij je myszą."
        )
        btn_spawn.clicked.connect(self.spawn_missing_packages)
        controls.addWidget(btn_spawn)

        self.btn_rotate_z = QPushButton("Obróć zaznaczone o 90° (Z)")
        self.btn_rotate_z.setEnabled(False)
        self.btn_rotate_z.setToolTip(
            "Obraca tylko zaznaczone paczki (X↔Y) w miejscu — inne nie zmieniają położenia."
        )
        self.btn_rotate_z.clicked.connect(self.rotate_selected_z)
        controls.addWidget(self.btn_rotate_z)

        hint = QLabel(
            "Zaznaczanie: klik w rzut z góry (Ctrl+klik = wiele). "
            "Przeciąganie: przyciąganie z odstępem 1 cm; Alt = bez przyciągania. "
            "Esc = anuluj ruch. R = obrót Z. Delete na liście = usuń typ. "
            "„Wstaw nowe bez układu” dorzuca paczki obok busy do ręcznego ustawienia."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #555; font-size: 11px;")
        controls.addWidget(hint)

        self.verdict_label = QLabel("Werdykt: brak obliczenia")
        self.verdict_label.setWordWrap(True)
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.verdict_label.setFont(font)
        self.verdict_label.setStyleSheet(
            "padding: 8px; border-radius: 4px; background: #f0f0f0; color: #333;"
        )
        controls.addWidget(self.verdict_label)

        self.stats_label = QLabel("")
        self.stats_label.setWordWrap(True)
        controls.addWidget(self.stats_label)

        self.issues_label = QLabel("")
        self.issues_label.setWordWrap(True)
        self.issues_label.setStyleSheet(
            "padding: 6px; border-radius: 4px; background: #fff3cd; color: #7a4b00;"
        )
        self.issues_label.hide()
        controls.addWidget(self.issues_label)

        controls.addStretch(1)

        # --- Right: 3D + 2D ---
        right_split = QSplitter(Qt.Vertical)
        root.addWidget(right_split, 3)

        self.canvas3d = scene.SceneCanvas(
            keys="interactive",
            bgcolor="#f4f6f8",
            size=(800, 500),
        )
        self.view3d = self.canvas3d.central_widget.add_view()
        self.view3d.camera = scene.cameras.TurntableCamera(
            up="+z",
            fov=45,
            elevation=25,
            azimuth=35,
            distance=None,
        )
        self.view3d.camera.interactive = True
        self._visuals_3d: list = []
        right_split.addWidget(self.canvas3d.native)

        views_2d = QWidget()
        views_layout = QHBoxLayout(views_2d)
        views_layout.setContentsMargins(0, 0, 0, 0)

        self.top_view = pg.PlotWidget(title="Rzut z góry (X/Y) — klik: zaznacz")
        self.top_view.setAspectLocked(True)
        self.top_view.showGrid(x=True, y=True, alpha=0.3)
        self.top_view.viewport().installEventFilter(self)
        views_layout.addWidget(self.top_view)

        self.side_view = pg.PlotWidget(title="Rzut z boku (X/Z)")
        self.side_view.setAspectLocked(True)
        self.side_view.showGrid(x=True, y=True, alpha=0.3)
        views_layout.addWidget(self.side_view)

        right_split.addWidget(views_2d)
        right_split.setStretchFactor(0, 3)
        right_split.setStretchFactor(1, 2)

        self._update_top_view_ranges()
        self._update_side_view_ranges()
        self._redraw_top_view_container()
        self._redraw_side_view_container()
        self._validate_current_layout()
        self._redraw_3d()
        undo_action = QAction("Cofnij", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        self.addAction(undo_action)

        rotate_action = QAction("Obróć Z", self)
        rotate_action.setShortcut("R")
        rotate_action.triggered.connect(self.rotate_selected_z)
        self.addAction(rotate_action)
        cancel_drag = QAction("Anuluj przesuwanie", self)
        cancel_drag.setShortcut("Esc")
        cancel_drag.triggered.connect(lambda: self._finish_drag(False))
        self.addAction(cancel_drag)
        self._retranslate_ui()

    def _create_menu(self):
        bar = self.menuBar()
        language_widget = QWidget(bar)
        language_layout = QHBoxLayout(language_widget)
        language_layout.setContentsMargins(8, 0, 8, 0)
        self.language_label = QLabel("Język:")
        self.language_combo = QComboBox()
        self.language_combo.addItem("Polski", "pl")
        self.language_combo.addItem("English", "en")
        self.language_combo.setCurrentIndex(self.language_combo.findData(language()))
        self.language_label.setBuddy(self.language_combo)
        language_layout.addWidget(self.language_label)
        language_layout.addWidget(self.language_combo)
        bar.setCornerWidget(language_widget, Qt.TopRightCorner)
        self.language_combo.currentIndexChanged.connect(self._change_language)
        file_menu = bar.addMenu("Plik")
        act_save = QAction("Zapisz konfigurację…", self)
        act_save.triggered.connect(self.save_config)
        file_menu.addAction(act_save)
        act_load = QAction("Wczytaj konfigurację…", self)
        act_load.triggered.connect(self.load_config)
        file_menu.addAction(act_load)
        help_menu = bar.addMenu("Pomoc")
        about_action = QAction("O programie…", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_about(self):
        QMessageBox.about(self, tr("O programie"), tr(
            "Autor projektu: {author}.\nProgram został w całości wykonany przez agentów AI.\n\n"
            "Wersja: {version}\nRepozytorium: https://github.com/hudzialke/3DUltimator",
            author="hudzialke", version=__version__))

    def _change_language(self, _index):
        self._finish_drag(False)
        set_language(self.language_combo.currentData())
        configure_qt_language()
        self.settings.setValue("language", language())
        self.settings.sync()
        self._retranslate_ui()

    def _retranslate_ui(self):
        apply_translations(self)
        self.top_view.setTitle(tr("Rzut z góry (X/Y) — klik: zaznacz"))
        self.side_view.setTitle(tr("Rzut z boku (X/Z)"))
        self.package_model.headerDataChanged.emit(Qt.Horizontal, 0, self.package_model.columnCount() - 1)
        if self.package_model.rowCount():
            self.package_model.dataChanged.emit(
                self.package_model.index(0, 0),
                self.package_model.index(self.package_model.rowCount() - 1, self.package_model.columnCount() - 1))
        self._update_verdict()
        if not self.placed_boxes and self.package_model.packages:
            self.verdict_label.setText(tr("Werdykt: brak obliczenia"))
        self.statusBar().clearMessage()

    def _remember_package(self, pkg: PackageType, favorite: bool | None = None) -> None:
        saved = package_to_saved(pkg)
        self.package_library.remember(saved)
        if favorite is not None:
            self.package_library.set_favorite(saved, favorite)

    def add_package_type(self):
        dlg = PackageDialog(self, library=self.package_library)
        if dlg.exec() != QDialog.Accepted:
            return
        pkg = dlg.result_package()
        self.undo_stack.append(self._snapshot())
        self.package_model.addPackageType(pkg)
        self._remember_package(pkg, favorite=dlg.want_favorite())

    def edit_package_type(self, *_args):
        row = self.table.currentIndex().row()
        if row < 0 or row >= len(self.package_model.packages):
            QMessageBox.information(
                self, tr("Edycja"), tr("Zaznacz typ paczki na liście, potem kliknij Edytuj.")
            )
            return
        current = self.package_model.packages[row]
        dlg = PackageDialog(self, package=current, library=self.package_library)
        if dlg.exec() != QDialog.Accepted:
            return
        pkg = dlg.result_package()
        self.undo_stack.append(self._snapshot())
        self.package_model.updatePackageType(row, pkg)
        self._remember_package(pkg, favorite=dlg.want_favorite())

    def open_history(self):
        self._open_package_library("history")

    def open_favorites(self):
        self._open_package_library("favorites")

    def _open_package_library(self, mode: str):
        dlg = PackageLibraryDialog(self, self.package_library, mode=mode)
        if dlg.exec() != QDialog.Accepted or dlg.selected is None:
            return
        pkg = saved_to_package(dlg.selected)
        self.undo_stack.append(self._snapshot())
        self.package_model.addPackageType(pkg)
        self.package_library.remember(package_to_saved(pkg))

    def remove_selected_package_type(self):
        row = self.table.currentIndex().row()
        if row < 0 or row >= len(self.package_model.packages):
            return
        self._finish_drag(False)
        self.undo_stack.append(self._snapshot())
        self.package_model.beginRemoveRows(QModelIndex(), row, row)
        del self.package_model.packages[row]
        self.package_model.endRemoveRows()
        self.placed_boxes = [b for b in self.placed_boxes if b.package_index != row]
        for box in self.placed_boxes:
            if box.package_index > row:
                box.package_index -= 1
            box.color = self._color_for_package(box.package_index, box.overflow)
        self.selected_indices.clear()
        self._sync_rotate_button()
        self._update_verdict()
        self.redraw_boxes()

    def draw_container(self):
        self.container_x = self.spin_x.value()
        self.container_y = self.spin_y.value()
        self.container_z = self.spin_z.value()
        self._update_top_view_ranges()
        self._redraw_top_view_container()
        self._update_side_view_ranges()
        self._redraw_side_view_container()

    def compute_packing(self):
        self.draw_container()
        self.undo_stack.append(self._snapshot())
        self.selected_indices.clear()
        self._sync_rotate_button()

        items: List[PackItem] = []
        for idx, pkg in enumerate(self.package_model.packages):
            for _ in range(pkg.count):
                items.append(
                    PackItem(
                        package_index=idx,
                        dx=pkg.dx,
                        dy=pkg.dy,
                        dz=pkg.dz,
                        stackable=pkg.stackable,
                        rot_x=pkg.rot_x,
                        rot_y=pkg.rot_y,
                        rot_z=pkg.rot_z,
                    )
                )

        packed: List[PackedBox] = pack_single_bin(
            (self.container_x, self.container_y, self.container_z),
            items,
        )

        self.placed_boxes = [
            PlacedBox(
                position=b.position,
                size=b.size,
                color=self._color_for_package(b.package_index, overflow=b.overflow),
                package_index=b.package_index,
                overflow=b.overflow,
            )
            for b in packed
        ]
        self._update_verdict()
        self._validate_current_layout()
        self.redraw_boxes()

    def spawn_missing_packages(self):
        """Dodaje brakujące sztuki z listy typów jako overflow — bez auto-układu."""
        self.draw_container()
        self.chk_show_overflow.setChecked(True)

        existing_counts: dict[int, int] = {}
        for box in self.placed_boxes:
            existing_counts[box.package_index] = existing_counts.get(box.package_index, 0) + 1

        # Start pozycji overflow: obok busy, poniżej już leżących overflow
        overflow_x = float(self.container_x + 50)
        overflow_y = 0.0
        for box in self.placed_boxes:
            if box.overflow:
                overflow_y = max(overflow_y, box.position[1] + box.size[1] + 20)

        added = 0
        new_boxes: list[PlacedBox] = []
        for idx, pkg in enumerate(self.package_model.packages):
            have = existing_counts.get(idx, 0)
            need = max(0, pkg.count - have)
            for _ in range(need):
                dx, dy, dz = float(pkg.dx), float(pkg.dy), float(pkg.dz)
                new_boxes.append(
                    PlacedBox(
                        position=(overflow_x, overflow_y, 0.0),
                        size=(dx, dy, dz),
                        color=self._color_for_package(idx, overflow=True),
                        package_index=idx,
                        overflow=True,
                    )
                )
                overflow_y += dy + 20
                added += 1

        if added == 0:
            QMessageBox.information(
                self,
                tr("Wstawianie"),
                tr("Brak nowych sztuk do wstawienia.\n"
                "Zwiększ „Ilość” w typie paczki albo dodaj nowy typ."),
            )
            return

        self.undo_stack.append(self._snapshot())
        self.placed_boxes.extend(new_boxes)
        self._update_verdict()
        self._validate_current_layout()
        self.redraw_boxes()
        QMessageBox.information(
            self,
            tr("Wstawianie"),
            tr("Dodano {added} paczek obok przestrzeni ładunkowej.\n"
               "Przeciągnij je myszą w rzucie z góry we właściwe miejsce.", added=added),
        )

    def _update_verdict(self):
        self._validate_current_layout()
        total = len(self.placed_boxes)
        overflow = sum(1 for b in self.placed_boxes if b.overflow)
        fitted = total - overflow
        vol_box = self.container_x * self.container_y * self.container_z
        used = sum(
            b.size[0] * b.size[1] * b.size[2]
            for b in self.placed_boxes
            if not b.overflow
        )
        fill_pct = (100.0 * used / vol_box) if vol_box else 0.0

        if total == 0:
            self.verdict_label.setText(tr("Werdykt: brak paczek"))
            self.verdict_label.setStyleSheet(
                "padding: 8px; border-radius: 4px; background: #f0f0f0; color: #333;"
            )
            self.stats_label.setText("")
            return

        if self.layout_issues:
            self.verdict_label.setText(tr("Werdykt: POPRAW UŁOŻENIE — kolizja lub brak podparcia"))
            self.verdict_label.setStyleSheet(
                "padding: 8px; border-radius: 4px; background: #fff3cd; color: #7a4b00;"
            )
        elif overflow == 0:
            self.verdict_label.setText(tr("Werdykt: MIEŚCI SIĘ — wszystkie {fitted} paczek", fitted=fitted))
            self.verdict_label.setStyleSheet(
                "padding: 8px; border-radius: 4px; background: #d4edda; color: #155724;"
            )
        else:
            self.verdict_label.setText(
                tr("Werdykt: NIE ZNALEZIONO PEŁNEGO UKŁADU — poza: {overflow} / {total}", overflow=overflow, total=total)
            )
            self.verdict_label.setStyleSheet(
                "padding: 8px; border-radius: 4px; background: #f8d7da; color: #721c24;"
            )

        self.stats_label.setText(
            tr("W środku: {fitted}  |  Overflow: {overflow}\n"
               "Objętość użyta: {used:.0f} / {vol_box:.0f} cm3  ({fill_pct:.1f}%)",
               fitted=fitted, overflow=overflow, used=used, vol_box=vol_box, fill_pct=fill_pct)
        )

    def redraw_boxes(self, _checked=False, *, update_ranges=True):
        self._validate_current_layout()
        self.redraw_top_view(update_ranges=update_ranges)
        self.redraw_side_view(update_ranges=update_ranges)
        self._redraw_3d(update_ranges=update_ranges)

    def _sync_rotate_button(self):
        self.btn_rotate_z.setEnabled(bool(self.selected_indices))

    def _scene_pos_from_widget_event(self, event) -> QPointF:
        point = event.position().toPoint() if hasattr(event, "position") else event.pos()
        return self.top_view.mapToScene(point)

    def _map_scene_to_view_xy(self, scene_pos: QPointF) -> tuple[float, float]:
        mouse_point = self.top_view.plotItem.vb.mapSceneToView(scene_pos)
        return float(mouse_point.x()), float(mouse_point.y())

    def _snapshot(self):
        return UndoState(
            [PackageType(**vars(p)) for p in self.package_model.packages],
            [PlacedBox(**vars(b)) for b in self.placed_boxes],
        )

    def _container(self):
        return self.container_x, self.container_y, self.container_z

    def _issue_summary(self) -> str:
        if not self.layout_issues:
            return ""
        parts: list[str] = []
        seen: set[tuple[int, str, int | None]] = set()
        for issue in self.layout_issues:
            key = (issue.index, issue.kind, issue.other_index)
            if key in seen:
                continue
            seen.add(key)
            parts.append(tr("Paczka {number}: {detail}.", number=issue.index + 1, detail=issue.detail))
        return tr("Uwaga: ") + " ".join(parts[:6])

    def _validate_current_layout(self):
        index_map: list[int] = []
        boxes: list[tuple] = []
        for i, box in enumerate(self.placed_boxes):
            if box.overflow:
                continue
            index_map.append(i)
            boxes.append((box.position, box.size))

        raw_issues = validate_layout(
            boxes,
            (float(self.container_x), float(self.container_y), float(self.container_z)),
            stackable=[self.package_model.packages[self.placed_boxes[i].package_index].stackable
                       for i in index_map],
        )
        remapped: list[LayoutIssue] = []
        for issue in raw_issues:
            real_index = index_map[issue.index]
            other = (
                index_map[issue.other_index]
                if issue.other_index is not None
                else None
            )
            detail = issue.detail
            if issue.kind == "collision" and other is not None:
                detail = tr("koliduje z paczką {number}", number=other + 1)
            remapped.append(
                LayoutIssue(
                    index=real_index,
                    kind=issue.kind,
                    detail=detail,
                    other_index=other,
                )
            )
        self.layout_issues = remapped
        self._invalid_indices = {issue.index for issue in self.layout_issues}
        summary = self._issue_summary()
        if summary:
            self.issues_label.setText(summary)
            self.issues_label.show()
        else:
            self.issues_label.hide()

    def _adopt_overflow_packages(self, indices: list[int]) -> None:
        """Overflow po ręcznym przesunięciu wraca do normalnej puli."""
        for i in indices:
            if 0 <= i < len(self.placed_boxes) and self.placed_boxes[i].overflow:
                box = self.placed_boxes[i]
                box.overflow = False
                box.color = self._color_for_package(box.package_index, overflow=False)

    def _apply_pending_drag(self):
        if self._drag_pending is None or not self._drag_active:
            return
        dx, dy, free = self._drag_pending
        self._drag_pending = None
        if not free:
            vb = self.top_view.plotItem.vb
            pixel_x, pixel_y = vb.viewPixelSize()
            tolerance = min(5.0, 8.0 * min(abs(pixel_x), abs(pixel_y)))
            dx, dy = snap_drag_delta(
                self.placed_boxes, self._drag_selection, self._drag_start_positions,
                (dx, dy), self._container(), tolerance,
            )
        for i in self._drag_selection:
            box = self.placed_boxes[i]
            x, y, z = self._drag_start_positions[i]
            box.position = (x + dx, y + dy, z)
            if self._drag_original_snapshot.boxes[i].overflow:
                box.overflow = not inside(box, self._container())
            box.color = self._color_for_package(box.package_index, box.overflow)
        self._validate_current_layout()
        # Update existing graphics in place. Do not rebuild OpenGL meshes or
        # change the view transform under the mouse during a drag.
        for i in self._drag_selection:
            box = self.placed_boxes[i]
            x, y, z = box.position
            dx, dy, dz = box.size
            curves, label = self._top_box_items.get(i, ([], None))
            for curve in curves:
                curve.setData([x, x + dx, x + dx, x, x], [y, y, y + dy, y + dy, y])
                curve.setPen(pg.mkPen((210, 40, 40) if i in self._invalid_indices else (255, 200, 0), width=2))
            if label is not None:
                label.setPos(x + dx / 2.0, y + dy / 2.0)
            curve = self._side_box_items.get(i)
            if curve is not None:
                curve.setData([x, x + dx, x + dx, x, x], [z, z, z + dz, z + dz, z])
            visual = self._box_visuals_3d.get(i)
            if visual is not None:
                visual.transform.translate = (x + dx / 2.0, y + dy / 2.0, z + dz / 2.0)
        self.canvas3d.update()

    def _finish_drag(self, commit=True):
        if not self._drag_active:
            return
        self._drag_timer.stop()
        if commit:
            self._apply_pending_drag()
        snapshot = self._drag_original_snapshot
        changed = self._drag_started and snapshot is not None
        if changed:
            self._validate_current_layout()
            if not commit or self.layout_issues:
                self.placed_boxes = [PlacedBox(**vars(b)) for b in snapshot.boxes]
                if commit:
                    self.statusBar().showMessage(
                        tr("Ruch cofnięty: kolizja, brak podparcia lub paczka poza samochodem."), 5000)
            elif self.placed_boxes != snapshot.boxes:
                self.undo_stack.append(snapshot)
        self._drag_active = False
        self._drag_started = False
        self._drag_pending = None
        self._drag_selection = []
        self._drag_start_widget = None
        self._drag_start_xy = None
        self._drag_start_positions = {}
        self._drag_original_snapshot = None
        if changed:
            self._update_verdict()
            self.redraw_boxes(update_ranges=False)

    def eventFilter(self, watched, event):
        if watched is self.top_view.viewport():
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self.top_view.setFocus()
                scene_pos = self._scene_pos_from_widget_event(event)
                x, y = self._map_scene_to_view_xy(scene_pos)
                hit = self._hit_test_top(x, y)
                ctrl = bool(event.modifiers() & Qt.ControlModifier)
                if hit is None:
                    if not ctrl:
                        self.selected_indices.clear()
                elif ctrl:
                    if hit in self.selected_indices:
                        self.selected_indices.remove(hit)
                    else:
                        self.selected_indices.add(hit)
                elif hit not in self.selected_indices:
                    self.selected_indices = {hit}
                self._sync_rotate_button()
                self.redraw_boxes(update_ranges=False)
                if hit is not None and hit in self.selected_indices:
                    self._drag_active = True
                    self._drag_started = False
                    self._drag_selection = sorted(self.selected_indices)
                    self._drag_start_widget = QPointF(event.position())
                    self._drag_start_xy = (x, y)
                    self._drag_start_positions = {
                        i: self.placed_boxes[i].position for i in self._drag_selection}
                    self._drag_original_snapshot = self._snapshot()
                return True
            if event.type() == QEvent.MouseMove and self._drag_active:
                if not self._drag_started:
                    distance = event.position() - self._drag_start_widget
                    if distance.manhattanLength() < QApplication.startDragDistance():
                        return True
                    self._drag_started = True
                x, y = self._map_scene_to_view_xy(self._scene_pos_from_widget_event(event))
                sx, sy = self._drag_start_xy
                self._drag_pending = (x - sx, y - sy, bool(event.modifiers() & Qt.AltModifier))
                if not self._drag_timer.isActive():
                    self._drag_timer.start()
                return True
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                self._finish_drag()
                return True
        return super().eventFilter(watched, event)

    def _hit_test_top(self, x: float, y: float) -> int | None:
        """Zwraca indeks paczki pod (x,y); przy nakładaniu wybiera najwyższą (max z+dz)."""
        best: int | None = None
        best_top = -1.0
        show_overflow = self.chk_show_overflow.isChecked()
        for i, box in enumerate(self.placed_boxes):
            if box.overflow and not show_overflow:
                continue
            px, py, pz = box.position
            dx, dy, dz = box.size
            if px <= x <= px + dx and py <= y <= py + dy:
                # Overflow rysujemy „obok” — traktuj je jak wysoko klikalne.
                top = (pz + dz) if not box.overflow else 1e9
                if top >= best_top:
                    best_top = top
                    best = i
        return best

    def rotate_selected_z(self):
        if self._drag_active:
            return
        if not self.selected_indices:
            QMessageBox.information(
                self,
                tr("Obrót Z"),
                tr("Zaznacz paczki w rzucie z góry (klik / Ctrl+klik), potem naciśnij R."),
            )
            return

        indices = sorted(i for i in self.selected_indices if 0 <= i < len(self.placed_boxes))
        if not indices:
            QMessageBox.information(self, tr("Obrót Z"), tr("Brak zaznaczonych paczek."))
            return

        if any(not self.package_model.packages[self.placed_boxes[i].package_index].rot_z
               for i in indices):
            self.statusBar().showMessage(tr("Obrót Z jest wyłączony dla zaznaczonej paczki."), 5000)
            return
        snapshot = self._snapshot()
        for i in indices:
            box = self.placed_boxes[i]
            dx, dy, dz = box.size
            x, y, z = box.position
            box.size = (dy, dx, dz)
            box.position = (x + (dx - dy) / 2, y + (dy - dx) / 2, z)
            if not box.overflow:
                box.position = (max(0, min(box.position[0], self.container_x - dy)),
                                max(0, min(box.position[1], self.container_y - dx)), z)
            if box.overflow and inside(box, self._container()):
                self._adopt_overflow_packages([i])
        self._validate_current_layout()
        if self.layout_issues:
            self.placed_boxes = snapshot.boxes
            self.statusBar().showMessage(tr("Obrót cofnięty: kolizja, brak podparcia lub brak miejsca."), 5000)
        elif self.placed_boxes != snapshot.boxes:
            self.undo_stack.append(snapshot)
        self._update_verdict()
        self.redraw_boxes(update_ranges=False)

    def _color_for_package(
        self, pkg_index: int, overflow: bool
    ) -> tuple[float, float, float, float]:
        if overflow:
            return (0.55, 0.55, 0.55, 0.75)
        r, g, b = self.package_colors[pkg_index % len(self.package_colors)]
        return (r / 255.0, g / 255.0, b / 255.0, 0.85)

    def _update_top_view_ranges(self):
        max_x = self.container_x
        max_y = self.container_y
        if self.chk_show_overflow.isChecked():
            for b in self.placed_boxes:
                if b.overflow:
                    max_x = max(max_x, b.position[0] + b.size[0] + 20)
                    max_y = max(max_y, b.position[1] + b.size[1] + 20)
        self.top_view.setXRange(0, max(max_x, 100))
        self.top_view.setYRange(0, max(max_y, 100))

    def _redraw_top_view_container(self):
        if self.top_view_container is not None:
            self.top_view.removeItem(self.top_view_container)
        xs = [0, self.container_x, self.container_x, 0, 0]
        ys = [0, 0, self.container_y, self.container_y, 0]
        self.top_view_container = pg.PlotCurveItem(
            xs, ys, pen=pg.mkPen((50, 150, 255), width=2)
        )
        self.top_view.addItem(self.top_view_container)

    def redraw_top_view(self, *, update_ranges=True):
        self._top_box_items.clear()
        for item in self.top_view_boxes:
            self.top_view.removeItem(item)
        self.top_view_boxes.clear()
        for item in self._top_view_texts:
            self.top_view.removeItem(item)
        self._top_view_texts.clear()
        for item in self._top_view_issue_markers:
            self.top_view.removeItem(item)
        self._top_view_issue_markers.clear()
        if update_ranges:
            self._update_top_view_ranges()
        self._redraw_top_view_container()

        show_overflow = self.chk_show_overflow.isChecked()
        for i, box in enumerate(self.placed_boxes):
            if box.overflow and not show_overflow:
                continue
            x, y, _ = box.position
            dx, dy, _ = box.size
            xs = [x, x + dx, x + dx, x, x]
            ys = [y, y, y + dy, y + dy, y]
            selected = i in self.selected_indices
            invalid = i in self._invalid_indices and not box.overflow
            if box.overflow and not selected and not invalid:
                color = (150, 150, 150)
                width = 1.5
            elif invalid:
                color = (210, 40, 40)
                width = 3.0
            elif selected:
                color = (20, 20, 20)
                width = 3.5
            else:
                r, g, b, _a = box.color
                color = (int(r * 255), int(g * 255), int(b * 255))
                width = 1.5
            curve = pg.PlotCurveItem(xs, ys, pen=pg.mkPen(color, width=width))
            self.top_view.addItem(curve)
            self.top_view_boxes.append(curve)
            curves = [curve]
            if selected:
                # żółta obwódka zaznaczenia
                hi = pg.PlotCurveItem(
                    xs, ys, pen=pg.mkPen((255, 200, 0), width=2.0)
                )
                self.top_view.addItem(hi)
                self.top_view_boxes.append(hi)
                curves.append(hi)

            label = pg.TextItem(
                text=f"{int(box.size[0])} × {int(box.size[1])} × {int(box.size[2])}",
                color=(235, 235, 235) if not box.overflow else (200, 200, 200),
                anchor=(0.5, 0.5),
            )
            label.setPos(x + dx / 2.0, y + dy / 2.0)
            self.top_view.addItem(label)
            self._top_view_texts.append(label)
            self._top_box_items[i] = (curves, label)

            if invalid:
                marker = pg.TextItem(text="!", color=(255, 30, 30), anchor=(0, 0))
                marker.setPos(x + 4, y + 4)
                self.top_view.addItem(marker)
                self._top_view_issue_markers.append(marker)

    def _update_side_view_ranges(self):
        max_x = self.container_x
        max_z = self.container_z
        if self.chk_show_overflow.isChecked():
            for b in self.placed_boxes:
                if b.overflow:
                    max_x = max(max_x, b.position[0] + b.size[0] + 20)
                    max_z = max(max_z, b.position[2] + b.size[2] + 20)
        self.side_view.setXRange(0, max(max_x, 100))
        self.side_view.setYRange(0, max(max_z, 100))

    def _redraw_side_view_container(self):
        if self.side_view_container is not None:
            self.side_view.removeItem(self.side_view_container)
        xs = [0, self.container_x, self.container_x, 0, 0]
        zs = [0, 0, self.container_z, self.container_z, 0]
        self.side_view_container = pg.PlotCurveItem(
            xs, zs, pen=pg.mkPen((50, 150, 255), width=2)
        )
        self.side_view.addItem(self.side_view_container)

    def redraw_side_view(self, *, update_ranges=True):
        self._side_box_items.clear()
        for item in self.side_view_boxes:
            self.side_view.removeItem(item)
        self.side_view_boxes.clear()
        if update_ranges:
            self._update_side_view_ranges()
        self._redraw_side_view_container()

        show_overflow = self.chk_show_overflow.isChecked()
        for i, box in enumerate(self.placed_boxes):
            if box.overflow and not show_overflow:
                continue
            x, _, z = box.position
            dx, _, dz = box.size
            xs = [x, x + dx, x + dx, x, x]
            zs = [z, z, z + dz, z + dz, z]
            selected = i in self.selected_indices and not box.overflow
            invalid = i in self._invalid_indices and not box.overflow
            if box.overflow:
                color = (150, 150, 150)
                width = 1.5
            elif invalid:
                color = (210, 40, 40)
                width = 2.5
            elif selected:
                color = (255, 180, 0)
                width = 3.0
            else:
                r, g, b, _a = box.color
                color = (int(r * 255), int(g * 255), int(b * 255))
                width = 1.5
            curve = pg.PlotCurveItem(xs, zs, pen=pg.mkPen(color, width=width))
            self.side_view.addItem(curve)
            self.side_view_boxes.append(curve)
            self._side_box_items[i] = curve

    def _clear_3d_visuals(self):
        self._box_visuals_3d.clear()
        for visual in self._visuals_3d:
            visual.parent = None
        self._visuals_3d.clear()

    def _add_wireframe_box(self, pos, size, color=(0.15, 0.45, 0.9, 1.0), width=2.0):
        """Tylko krawędzie AABB — bez ścian, żeby widać wnętrze."""
        x, y, z = pos
        dx, dy, dz = size
        if dx <= 0 or dy <= 0 or dz <= 0:
            return
        x0, y0, z0 = float(x), float(y), float(z)
        x1, y1, z1 = x0 + float(dx), y0 + float(dy), z0 + float(dz)
        corners = [
            (x0, y0, z0),
            (x1, y0, z0),
            (x1, y1, z0),
            (x0, y1, z0),
            (x0, y0, z1),
            (x1, y0, z1),
            (x1, y1, z1),
            (x0, y1, z1),
        ]
        edges = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 4),
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),
        ]
        pts = []
        for a, b in edges:
            pts.append(corners[a])
            pts.append(corners[b])
        pos_arr = np.asarray(pts, dtype=np.float32)
        line = scene.visuals.Line(
            pos=pos_arr,
            color=color,
            width=width,
            connect="segments",
            parent=self.view3d.scene,
            method="gl",
        )
        self._visuals_3d.append(line)

    def _add_box_visual(self, pos, size, color, edge_color, alpha=0.9):
        x, y, z = pos
        dx, dy, dz = size
        if dx <= 0 or dy <= 0 or dz <= 0:
            return
        r, g, b = color[:3]
        face = (r, g, b, alpha)
        # VisPy Box: width→X, depth→Y, height→Z (nie height→Y!)
        box = scene.visuals.Box(
            width=float(dx),
            height=float(dz),
            depth=float(dy),
            color=face,
            edge_color=edge_color,
            parent=self.view3d.scene,
        )
        box.transform = scene.transforms.STTransform(
            translate=(x + dx / 2.0, y + dy / 2.0, z + dz / 2.0)
        )
        self._visuals_3d.append(box)
        return box

    def _redraw_3d(self, *, update_ranges=True):
        self._clear_3d_visuals()
        cx = float(self.container_x)
        cy = float(self.container_y)
        cz = float(self.container_z)

        # Kontener = wyłącznie krawędzie (widać paczki w środku)
        self._add_wireframe_box(
            (0.0, 0.0, 0.0),
            (cx, cy, cz),
            color=(0.12, 0.45, 0.95, 1.0),
            width=2.5,
        )

        show_overflow = self.chk_show_overflow.isChecked()
        max_x, max_y, max_z = cx, cy, cz

        for i, box in enumerate(self.placed_boxes):
            if box.overflow and not show_overflow:
                continue
            r, g, b, a = box.color
            selected = i in self.selected_indices and not box.overflow
            invalid = i in self._invalid_indices and not box.overflow
            if box.overflow:
                edge = (0.45, 0.45, 0.45, 0.9)
                face = (r, g, b)
                alpha = 0.7
            elif invalid:
                face = (min(1.0, r * 1.15 + 0.2), min(0.6, g * 0.7), min(0.6, b * 0.7))
                edge = (1.0, 0.15, 0.15, 1.0)
                alpha = 1.0
            elif selected:
                # jaśniejsza ścianka + żółta krawędź
                face = (min(1.0, r * 1.25 + 0.15), min(1.0, g * 1.15 + 0.1), min(1.0, b * 0.9))
                edge = (1.0, 0.85, 0.0, 1.0)
                alpha = 1.0
            else:
                face = (r, g, b)
                edge = (0.15, 0.15, 0.15, 1.0)
                alpha = 0.95
            self._box_visuals_3d[i] = self._add_box_visual(
                box.position,
                box.size,
                color=face,
                edge_color=edge,
                alpha=alpha,
            )
            px, py, pz = box.position
            sx, sy, sz = box.size
            max_x = max(max_x, px + sx)
            max_y = max(max_y, py + sy)
            max_z = max(max_z, pz + sz)

        # Keep camera framing on cargo space (plus a little margin)
        margin = 1.05
        if update_ranges:
            self.view3d.camera.set_range(
                x=(0, max(max_x * margin, 1.0)),
                y=(0, max(max_y * margin, 1.0)),
                z=(0, max(max_z * margin, 1.0)),
            )
        self.canvas3d.update()

    def undo(self):
        if self._drag_active:
            self._finish_drag(False)
            return
        if not self.undo_stack:
            return
        last = self.undo_stack.pop()
        self.package_model.beginResetModel()
        self.package_model.packages = [PackageType(**vars(p)) for p in last.packages]
        self.package_model.endResetModel()
        self.placed_boxes = [PlacedBox(**vars(b)) for b in last.boxes]
        self.selected_indices = {
            i for i in self.selected_indices if 0 <= i < len(self.placed_boxes)
        }
        self._sync_rotate_button()
        self._update_verdict()
        self.redraw_boxes(update_ranges=False)

    def save_config(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Zapisz konfigurację"),
            "",
            tr("Konfiguracja ładunku (*.json);;Wszystkie pliki (*.*)"),
            options=QFileDialog.DontUseNativeDialog,
        )
        if not path:
            return
        data = {
            "container": {
                "x": self.spin_x.value(),
                "y": self.spin_y.value(),
                "z": self.spin_z.value(),
            },
            "packages": [
                {
                    "count": p.count,
                    "dx": p.dx,
                    "dy": p.dy,
                    "dz": p.dz,
                    "stackable": p.stackable,
                    "rot_x": p.rot_x,
                    "rot_y": p.rot_y,
                    "rot_z": p.rot_z,
                }
                for p in self.package_model.packages
            ],
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            QMessageBox.critical(self, tr("Błąd zapisu"), tr("Nie udało się zapisać pliku:\n{error}", error=e))

    def load_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Wczytaj konfigurację"),
            "",
            tr("Konfiguracja ładunku (*.json);;Wszystkie pliki (*.*)"),
            options=QFileDialog.DontUseNativeDialog,
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, tr("Błąd odczytu"), tr("Nie udało się wczytać pliku:\n{error}", error=e))
            return

        cont = data.get("container", {})
        self.spin_x.setValue(int(cont.get("x", self.container_x)))
        self.spin_y.setValue(int(cont.get("y", self.container_y)))
        self.spin_z.setValue(int(cont.get("z", self.container_z)))

        pkgs_data = data.get("packages", [])
        self.package_model.beginResetModel()
        self.package_model.packages = [
            PackageType(
                int(p.get("count", 1)),
                int(p.get("dx", 10)),
                int(p.get("dy", 10)),
                int(p.get("dz", 10)),
                bool(p.get("stackable", True)),
                bool(p.get("rot_x", True)),
                bool(p.get("rot_y", True)),
                bool(p.get("rot_z", True)),
            )
            for p in pkgs_data
        ]
        self.package_model.endResetModel()
        for pkg in self.package_model.packages:
            self._remember_package(pkg)

        self.draw_container()
        self.placed_boxes = []
        self.selected_indices.clear()
        self._sync_rotate_button()
        self._update_verdict()
        self.redraw_boxes()


def main():
    parser = argparse.ArgumentParser(description="3D Ultimator cargo planner")
    parser.add_argument("--language", choices=("pl", "en"), help="Initial UI language")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--smoke-dir", help=argparse.SUPPRESS)
    options, qt_arguments = parser.parse_known_args()
    app = QApplication([sys.argv[0], *qt_arguments])
    if options.smoke_test:
        if not options.smoke_dir:
            parser.error("--smoke-test requires --smoke-dir")
        smoke_dir = Path(options.smoke_dir)
        settings = QSettings(str(smoke_dir / "settings.ini"), QSettings.IniFormat)
        settings.setValue("language", "en")
        w = MainWindow(settings=settings, library=PackageLibrary(smoke_dir / "library.json"))
        w.package_model.packages = [PackageType(8, 123, 83, 50, False, False, False, True)]
        w.compute_packing()
        if len(w.placed_boxes) != 8 or any(b.overflow for b in w.placed_boxes) or w.layout_issues:
            raise RuntimeError("Packaged eight-package regression failed")
        w.language_combo.setCurrentIndex(w.language_combo.findData("pl"))
        w.language_combo.setCurrentIndex(w.language_combo.findData("en"))
        w.show()
        QTimer.singleShot(250, app.quit)
        result = app.exec()
        w.close()
        app.processEvents()
        sys.exit(result)
    w = MainWindow()
    if options.language:
        w.language_combo.setCurrentIndex(w.language_combo.findData(options.language))
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
