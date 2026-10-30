import unittest

from manual_layout import snap_drag_delta
from packing import PackedBox


class ManualLayoutTests(unittest.TestCase):
    def test_snap_to_right_face_with_one_cm_gap(self):
        boxes = [PackedBox(0, (0, 0, 0), (83, 123, 50)),
                 PackedBox(1, (200, 0, 0), (83, 123, 50))]
        shift = snap_drag_delta(boxes, [1], {1: boxes[1].position}, (-113, 0), (485, 220, 245), 5)
        self.assertEqual((-116, 0), shift)
        self.assertEqual(1, 200 + shift[0] - 83)

    def test_snap_to_left_face_with_one_cm_gap(self):
        boxes = [PackedBox(0, (200, 0, 0), (83, 123, 50)),
                 PackedBox(1, (20, 0, 0), (83, 123, 50))]
        shift = snap_drag_delta(boxes, [1], {1: boxes[1].position}, (99, 0), (485, 220, 245), 5)
        self.assertEqual(1, 200 - (20 + shift[0] + 83))

    def test_group_translation_preserves_offsets_and_non_grid_dimensions(self):
        boxes = [PackedBox(0, (12, 13, 0), (83, 50, 20)),
                 PackedBox(0, (96, 13, 0), (83, 50, 20))]
        starts = {i: b.position for i, b in enumerate(boxes)}
        dx, dy = snap_drag_delta(boxes, [0, 1], starts, (21.25, 2.75), (485, 220, 245), 1)
        self.assertEqual((21.25, 2.75), (dx, dy))
        self.assertEqual(84, (starts[1][0] + dx) - (starts[0][0] + dx))

    def test_no_grid_jumps_away_from_faces(self):
        box = PackedBox(0, (50, 50, 0), (83, 50, 20))
        self.assertEqual((0.123, 0.456), snap_drag_delta(
            [box], [0], {0: box.position}, (0.123, 0.456), (485, 220, 245), 1))

    def test_wall_snap_has_no_gap(self):
        box = PackedBox(0, (100, 10, 0), (83, 50, 20))
        dx, dy = snap_drag_delta([box], [0], {0: box.position}, (-98, -8), (485, 220, 245), 3)
        self.assertEqual((0, 0), (100 + dx, 10 + dy))

    def test_remote_faces_do_not_attract_a_box_on_another_row(self):
        boxes = [PackedBox(0, (0, 0, 0), (83, 50, 20)),
                 PackedBox(1, (200, 150, 0), (83, 50, 20))]
        self.assertEqual((-113, 0), snap_drag_delta(
            boxes, [1], {1: boxes[1].position}, (-113, 0), (485, 300, 245), 5))


if __name__ == '__main__':
    unittest.main()
