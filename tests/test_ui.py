"""Qt integration checks using isolated package history and disposable cargo."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import Qt, QPointF, QSettings
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit

from main import MainWindow, PackageType, PlacedBox, PackageDialog, PackageLibraryDialog
from package_library import SavedPackage


class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        cls.library_patch = patch('package_library.library_path', return_value=Path(cls.temp.name) / 'library.json')
        cls.library_patch.start()
        cls.settings = QSettings(str(Path(cls.temp.name) / 'settings.ini'), QSettings.IniFormat)
        cls.settings.setValue('language', 'pl')
        cls.window = MainWindow(settings=cls.settings)
        cls.window.setWindowTitle('3D Ultimator — testy integracyjne')
        cls.window.show()
        cls.app.processEvents()

    @classmethod
    def tearDownClass(cls):
        cls.window.close()
        cls.app.processEvents()
        cls.library_patch.stop()
        cls.temp.cleanup()

    def setUp(self):
        w = self.window
        w.language_combo.setCurrentIndex(w.language_combo.findData('pl'))
        w._finish_drag(False)
        w.package_model.beginResetModel()
        w.package_model.packages = [PackageType(2, 83, 123, 50, False, False, False, True)]
        w.package_model.endResetModel()
        w.placed_boxes = [PlacedBox((0, 0, 0), (83, 123, 50), w._color_for_package(0, False), 0),
                          PlacedBox((200, 0, 0), (83, 123, 50), w._color_for_package(0, False), 0)]
        w.undo_stack.clear()
        w.selected_indices.clear()
        w._update_verdict()
        w.redraw_boxes()
        self.app.processEvents()

    def begin_drag(self, indices):
        w = self.window
        w.selected_indices = set(indices)
        w.redraw_boxes(update_ranges=False)
        w._drag_active = True
        w._drag_started = True
        w._drag_selection = list(indices)
        w._drag_start_positions = {i: w.placed_boxes[i].position for i in indices}
        w._drag_original_snapshot = w._snapshot()

    def viewport_point(self, x, y):
        w = self.window
        return w.top_view.mapFromScene(w.top_view.plotItem.vb.mapViewToScene(QPointF(x, y)))

    def test_mouse_drag_events_snap_at_one_cm_and_keep_view_fixed(self):
        w = self.window
        viewport = w.top_view.viewport()
        start = self.viewport_point(241.5, 61.5)
        finish = self.viewport_point(127, 61.5)
        before = w.top_view.viewRange()
        QTest.mousePress(viewport, Qt.LeftButton, pos=start)
        QTest.mouseMove(viewport, finish, delay=20)
        QTest.mouseRelease(viewport, Qt.LeftButton, pos=finish)
        self.app.processEvents()
        self.assertEqual({1}, w.selected_indices)
        self.assertAlmostEqual(84, w.placed_boxes[1].position[0])
        self.assertEqual(before, w.top_view.viewRange())
        self.assertFalse(w._drag_active)
        self.assertEqual(1, len(w.undo_stack))

    def test_ctrl_click_toggles_once_and_preserves_other_selection(self):
        w = self.window
        viewport = w.top_view.viewport()
        QTest.mouseClick(viewport, Qt.LeftButton, pos=self.viewport_point(40, 60))
        self.assertEqual({0}, w.selected_indices)
        QTest.mouseClick(viewport, Qt.LeftButton, Qt.ControlModifier, self.viewport_point(240, 60))
        self.assertEqual({0, 1}, w.selected_indices)
        QTest.mouseClick(viewport, Qt.LeftButton, Qt.ControlModifier, self.viewport_point(240, 60))
        self.assertEqual({0}, w.selected_indices)

    def test_language_switch_updates_ui_without_changing_cargo(self):
        w = self.window
        before = w._snapshot()
        original_mesh = w._box_visuals_3d[0]
        w.language_combo.setCurrentIndex(w.language_combo.findData('en'))
        self.assertEqual('Language:', w.language_label.text())
        self.assertEqual('File', w.menuBar().actions()[0].text())
        self.assertEqual('Quantity', w.package_model.headerData(0, Qt.Horizontal))
        self.assertEqual('No', w.package_model.data(w.package_model.index(0, 4)))
        self.assertEqual('Result: FITS — all 2 packages', w.verdict_label.text())
        self.assertIn('Volume used:', w.stats_label.text())
        self.assertEqual(before, w._snapshot())
        self.assertIs(original_mesh, w._box_visuals_3d[0])
        self.assertEqual([], w.undo_stack)
        w.language_combo.setCurrentIndex(w.language_combo.findData('pl'))
        self.assertEqual('Język:', w.language_label.text())
        self.assertEqual('Ilość', w.package_model.headerData(0, Qt.Horizontal))
        self.assertIn('MIEŚCI SIĘ', w.verdict_label.text())

    def test_about_identifies_author_and_ai_implementation_in_both_languages(self):
        w = self.window
        for code, title, phrase in [('pl', 'O programie', 'w całości wykonany przez agentów AI'),
                                    ('en', 'About', 'implemented entirely by AI agents')]:
            w.language_combo.setCurrentIndex(w.language_combo.findData(code))
            with patch('main.QMessageBox.about') as about:
                w.show_about()
                args = about.call_args.args
                self.assertEqual(title, args[1])
                self.assertIn('hudzialke', args[2])
                self.assertIn(phrase, args[2])

    def test_language_preference_is_restored_in_a_new_window(self):
        w = self.window
        w.language_combo.setCurrentIndex(w.language_combo.findData('en'))
        saved = QSettings(self.settings.fileName(), QSettings.IniFormat)
        self.assertEqual('en', saved.value('language'))
        restored = MainWindow(settings=saved)
        try:
            self.assertEqual('en', restored.language_combo.currentData())
            self.assertEqual('Language:', restored.language_label.text())
        finally:
            restored.close()

    def test_dialogs_and_history_follow_the_selected_language(self):
        w = self.window
        w.language_combo.setCurrentIndex(w.language_combo.findData('en'))
        dialog = PackageDialog(w)
        self.assertEqual('Add package type', dialog.windowTitle())
        self.assertEqual(' pcs', dialog.spin_count.suffix())
        self.assertIn('Stackable', dialog.chk_stackable.text())
        dialog.close()
        w.package_library.history = [SavedPackage(123, 83, 50, count=8, stackable=False)]
        history = PackageLibraryDialog(w, w.package_library, mode='history')
        self.assertEqual('Package history', history.windowTitle())
        self.assertEqual('Add to list', history.btn_add.text())
        self.assertIn('8 pcs', history.list_widget.item(0).text())
        self.assertIn('not stackable', history.list_widget.item(0).text())
        history.close()

    def test_preview_reuses_graphics_and_preserves_camera_and_ranges(self):
        w = self.window
        self.begin_drag([1])
        mesh = w._box_visuals_3d[1]
        curve = w._top_box_items[1][0][0]
        old_ranges = w.top_view.viewRange()
        old_camera = w.view3d.camera.get_state()
        w._drag_pending = (-114, 0, False)
        with patch.object(w, '_redraw_3d', wraps=w._redraw_3d) as redraw:
            w._apply_pending_drag()
            redraw.assert_not_called()
        self.assertIs(mesh, w._box_visuals_3d[1])
        self.assertIs(curve, w._top_box_items[1][0][0])
        self.assertEqual(old_ranges, w.top_view.viewRange())
        self.assertEqual(old_camera, w.view3d.camera.get_state())
        self.assertAlmostEqual(84, w.placed_boxes[1].position[0])
        w._finish_drag()
        self.assertEqual(1, len(w.undo_stack))
        w.undo()
        self.assertEqual((200, 0, 0), w.placed_boxes[1].position)

    def test_invalid_drop_rolls_back_without_undo_entry(self):
        w = self.window
        self.begin_drag([1])
        w._drag_pending = (-180, 0, True)
        w._finish_drag()
        self.assertEqual((200, 0, 0), w.placed_boxes[1].position)
        self.assertEqual([], w.undo_stack)
        self.assertFalse(w.layout_issues)

    def test_group_drag_preserves_one_cm_gap_and_undo_is_one_step(self):
        w = self.window
        w.placed_boxes[1].position = (84, 0, 0)
        self.begin_drag([0, 1])
        w._drag_pending = (12.25, 8.75, True)
        w._finish_drag()
        self.assertEqual((12.25, 8.75, 0), w.placed_boxes[0].position)
        self.assertEqual((96.25, 8.75, 0), w.placed_boxes[1].position)
        self.assertEqual(1, len(w.undo_stack))
        w.undo()
        self.assertEqual([(0, 0, 0), (84, 0, 0)], [b.position for b in w.placed_boxes])

    def test_moving_base_cannot_leave_stationary_cargo_unsupported(self):
        w = self.window
        w.package_model.packages[0].stackable = True
        w.placed_boxes[0].size = (83, 123, 50)
        w.placed_boxes[1].size = (83, 123, 50)
        w.placed_boxes[1].position = (0, 0, 50)
        self.begin_drag([0])
        w._drag_pending = (200, 0, True)
        w._finish_drag()
        self.assertEqual((0, 0, 0), w.placed_boxes[0].position)
        self.assertEqual((0, 0, 50), w.placed_boxes[1].position)
        self.assertFalse(w.layout_issues)

    def test_escape_rolls_back_preview(self):
        w = self.window
        self.begin_drag([1])
        w._drag_pending = (-50, 20, True)
        w._apply_pending_drag()
        self.assertEqual((150, 20, 0), w.placed_boxes[1].position)
        w._finish_drag(False)
        self.assertEqual((200, 0, 0), w.placed_boxes[1].position)
        self.assertEqual([], w.undo_stack)

    def test_overflow_is_adopted_only_when_inside(self):
        w = self.window
        w.placed_boxes[1].position = (535, 0, 0)
        w.placed_boxes[1].overflow = True
        self.begin_drag([1])
        w._drag_pending = (-20, 0, True)
        w._apply_pending_drag()
        self.assertTrue(w.placed_boxes[1].overflow)
        w._drag_pending = (-451, 0, True)
        w._finish_drag()
        self.assertFalse(w.placed_boxes[1].overflow)
        self.assertEqual((84, 0, 0), w.placed_boxes[1].position)
        self.assertIn('MIEŚCI SIĘ', w.verdict_label.text())

    def test_delete_removes_type_boxes_reindexes_and_undo_restores(self):
        w = self.window
        w.package_model.addPackageType(PackageType(1, 10, 10, 10, True, True, True, True))
        w.placed_boxes[1].package_index = 1
        before = w._snapshot()
        w.table.selectRow(0)
        w.table.setFocus()
        self.app.processEvents()
        QTest.keyClick(w.table, Qt.Key_Delete)
        self.app.processEvents()
        self.assertEqual(1, len(w.package_model.packages))
        self.assertEqual(1, len(w.placed_boxes))
        self.assertEqual(0, w.placed_boxes[0].package_index)
        w.undo()
        self.assertEqual(before, w._snapshot())

    def test_delete_in_dimension_editor_does_not_delete_a_package_type(self):
        w = self.window
        w.table.selectRow(0)
        w.spin_x.setFocus()
        self.app.processEvents()
        editor = w.spin_x.findChild(QLineEdit)
        QTest.keyClick(editor, Qt.Key_Delete)
        self.app.processEvents()
        self.assertEqual(1, len(w.package_model.packages))
        self.assertEqual(2, len(w.placed_boxes))

    def test_rotation_respects_allowed_axes_and_updates_verdict(self):
        w = self.window
        w.package_model.packages[0].rot_z = False
        w.selected_indices = {1}
        w.rotate_selected_z()
        self.assertEqual((83, 123, 50), w.placed_boxes[1].size)
        self.assertEqual([], w.undo_stack)
        w.package_model.packages[0].rot_z = True
        w.rotate_selected_z()
        self.assertEqual((123, 83, 50), w.placed_boxes[1].size)
        self.assertEqual(1, len(w.undo_stack))
        self.assertFalse(w.layout_issues)


if __name__ == '__main__':
    unittest.main()
