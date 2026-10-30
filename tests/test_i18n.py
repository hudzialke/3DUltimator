import string
import unittest

from i18n import EN, language, set_language, tr
from package_library import SavedPackage
from packing import validate_layout


class TranslationTests(unittest.TestCase):
    def tearDown(self):
        set_language('pl')

    def test_catalog_preserves_all_format_fields(self):
        formatter = string.Formatter()
        for source, target in EN.items():
            fields = lambda message: sorted((field, spec) for _, field, spec, _ in formatter.parse(message) if field is not None)
            with self.subTest(message=source):
                self.assertEqual(fields(source), fields(target))

    def test_english_formatted_messages(self):
        set_language('en')
        self.assertEqual('Result: FITS — all 8 packages',
                         tr('Werdykt: MIEŚCI SIĘ — wszystkie {fitted} paczek', fitted=8))
        self.assertEqual('Yes', tr('Tak'))

    def test_unknown_preference_falls_back_to_polish(self):
        set_language('invalid')
        self.assertEqual('pl', language())
        self.assertEqual('Tak', tr('Tak'))

    def test_saved_package_translation_does_not_change_cargo_data(self):
        package = SavedPackage(123, 83, 50, count=8, stackable=False, rot_x=False, rot_y=False)
        signature = package.signature()
        set_language('en')
        self.assertIn('8 pcs', package.label())
        self.assertIn('not stackable', package.label())
        self.assertEqual(signature, package.signature())
        set_language('pl')
        self.assertIn('8 szt.', package.label())

    def test_english_collision_and_support_messages(self):
        set_language('en')
        issues = validate_layout([((0, 0, 0), (5, 5, 5)), ((1, 1, 0), (5, 5, 5))], (10, 10, 10))
        self.assertEqual('collides with package 2', issues[0].detail)
        issues = validate_layout([((0, 0, 5), (5, 5, 5))], (10, 10, 10), stackable=[True])
        self.assertIn('missing support', issues[0].detail)
