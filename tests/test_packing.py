import itertools
import random
import unittest
from copy import deepcopy

from packing import (PackItem, PackedBox, _pack_greedy_legacy,
                     generate_orientations, pack_single_bin, validate_layout)


def item(index, size, stackable=False, rotations=(False, False, True)):
    return PackItem(index, *size, stackable, *rotations)


class PackingTests(unittest.TestCase):
    def assert_valid(self, container, items, boxes, initial=()):
        self.assertEqual(len(items), len(boxes))
        by_type = {it.package_index: it for it in items}
        for box in boxes:
            self.assertIn(box.size, generate_orientations(by_type[box.package_index]))
            self.assertEqual(box.stackable, by_type[box.package_index].stackable)
        inside = [b for b in list(initial) + boxes if not b.overflow]
        self.assertEqual([], validate_layout([(b.position, b.size) for b in inside],
                                            container, stackable=[b.stackable for b in inside]))

    def test_eight_packages_from_screenshot_need_mixed_rotations(self):
        container = (485, 220, 245)
        items = [item(0, (123, 83, 50)) for _ in range(8)]
        self.assertEqual(1, sum(b.overflow for b in _pack_greedy_legacy(container, items)))
        result = pack_single_bin(container, items)
        self.assertFalse(any(b.overflow for b in result))
        self.assertEqual({(123, 83, 50), (83, 123, 50)}, {b.size for b in result})
        self.assertTrue(all(b.position[2] == 0 for b in result))
        self.assert_valid(container, items, result)

    def test_disabled_z_rotation_is_respected(self):
        items = [item(0, (123, 83, 50), rotations=(False, False, False)) for _ in range(8)]
        result = pack_single_bin((485, 220, 245), items)
        self.assertTrue(any(b.overflow for b in result))
        self.assertTrue(all(b.size == (123, 83, 50) for b in result))
        self.assert_valid((485, 220, 245), items, result)

    def test_only_permitted_axis_rotations(self):
        for flags in itertools.product((False, True), repeat=3):
            it = item(0, (2, 3, 5), rotations=flags)
            sizes = generate_orientations(it)
            self.assertEqual(len(sizes), len(set(sizes)))
            if sum(flags) == 0:
                self.assertEqual([(2, 3, 5)], sizes)
            elif sum(flags) == 1:
                self.assertEqual(2, len(sizes))
                unchanged_axis = flags.index(True)
                self.assertTrue(all(s[unchanged_axis] == (2, 3, 5)[unchanged_axis] for s in sizes))
            else:
                self.assertEqual(6, len(sizes))

    def test_each_single_axis_can_make_a_package_fit(self):
        for flags, container in [((True, False, False), (2, 5, 3)),
                                 ((False, True, False), (5, 3, 2)),
                                 ((False, False, True), (3, 2, 5))]:
            result = pack_single_bin(container, [item(0, (2, 3, 5), rotations=flags)])
            self.assertFalse(result[0].overflow)
            self.assertEqual(container, result[0].size)

    def test_projected_faces_find_space_missed_by_original_extreme_points(self):
        fixed = [PackedBox(1, (0, 0, 0), (3, 2, 1)), PackedBox(2, (3, 0, 0), (2, 4, 1))]
        original = deepcopy(fixed)
        items = [item(0, (5, 3, 1), rotations=(False, False, False))]
        result = pack_single_bin((5, 7, 1), items, fixed)
        self.assertEqual((0, 4, 0), result[0].position)
        self.assertEqual(original, fixed)
        self.assert_valid((5, 7, 1), items, result, fixed)

    def test_stacking_on_allowed_base(self):
        items = [item(0, (10, 10, 5), True), item(1, (10, 10, 5), False)]
        result = pack_single_bin((10, 10, 10), items)
        self.assertFalse(any(b.overflow for b in result))
        self.assert_valid((10, 10, 10), items, result)

    def test_cannot_stack_on_nonstackable_base(self):
        items = [item(0, (10, 10, 5)), item(1, (10, 10, 5))]
        result = pack_single_bin((10, 10, 10), items)
        self.assertEqual(1, sum(b.overflow for b in result))
        self.assert_valid((10, 10, 10), items, result)

    def test_mixed_support_cannot_load_nonstackable_box(self):
        boxes = [((0, 0, 0), (5, 10, 5)), ((5, 0, 0), (5, 10, 5)),
                 ((0, 0, 5), (10, 10, 5))]
        issues = validate_layout(boxes, (10, 10, 10), stackable=[True, False, True])
        self.assertEqual([(2, 'support')], [(i.index, i.kind) for i in issues])

    def test_empty_and_oversize(self):
        self.assertEqual([], pack_single_bin((10, 10, 10), []))
        items = [item(0, (11, 11, 11))]
        self.assertTrue(pack_single_bin((10, 10, 10), items)[0].overflow)

    def test_tiled_mixed_cargo_and_fixed_seed_regressions(self):
        rng = random.Random(8)
        for case in range(12):
            # Produce known feasible guillotine partitions of a truck floor.
            widths = [rng.randrange(20, 60), rng.randrange(20, 60)]
            length = 120
            sizes = []
            for width in widths:
                a, b = sorted(rng.sample(range(20, 100), 2))
                sizes.extend([(a, width, 10), (b - a, width, 10), (length - b, width, 10)])
            rng.shuffle(sizes)
            items = [item(i, size if rng.randrange(2) else (size[1], size[0], size[2]))
                     for i, size in enumerate(sizes)]
            container = (length, sum(widths), 10)
            with self.subTest(case=case):
                result = pack_single_bin(container, items)
                self.assertFalse(any(b.overflow for b in result))
                self.assert_valid(container, items, result)


if __name__ == '__main__':
    unittest.main()
