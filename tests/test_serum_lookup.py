"""Regression tests for VPX 10.8.1 Serum discovery/export naming."""
import tempfile
import unittest
from pathlib import Path

from serum_lookup import find_serum_colorization, serum_game_ids, serum_diagnostic_lines


class SerumLookupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vpm = self.root / "VPinMAME"
        self.table = self.root / "Tables" / "Game"
        self.vpm.mkdir(parents=True)
        self.table.mkdir(parents=True)

    def put(self, relative, data=b"dummy"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def lookup(self, *ids):
        return find_serum_colorization(str(self.vpm), str(self.table), ids)

    def test_prefers_cromc_over_crz_in_altcolor(self):
        self.put("VPinMAME/AltColor/afm_113/afm_113.cRZ")
        source = self.put("VPinMAME/AltColor/afm_113/pin2dmd.cROMc")
        result = self.lookup("afm_113")
        self.assertEqual(result.source, str(source))
        self.assertEqual(result.destination_name, "afm_113.cROMc")

    def test_old_crz_still_supported(self):
        self.put("VPinMAME/altcolor/afm_113/colorization.cRZ")
        self.assertEqual(self.lookup("afm_113").destination_name, "afm_113.cRZ")

    def test_flat_legacy_file(self):
        self.put("VPinMAME/altcolor/afm_113.cromc")
        self.assertEqual(self.lookup("afm_113").destination_name, "afm_113.cROMc")

    def test_prefers_cromc_even_when_crz_is_in_table(self):
        self.put("Tables/Game/serum/afm_113/afm_113.cRZ")
        source = self.put("VPinMAME/altcolor/afm_113/afm_113.cROMc")
        self.assertEqual(self.lookup("afm_113").source, str(source))

    def test_local_namespaced_serum(self):
        self.put("Tables/Game/Serum/PinMAME/afm_113/afm_113.cROMc")
        self.assertEqual(self.lookup("afm_113").destination_name, "afm_113.cROMc")

    def test_resolves_case_insensitively(self):
        source = self.put("VPinMAME/ALTCOLOR/AFM_113/Pin2Dmd.CrOmC")
        self.assertEqual(self.lookup("afm_113").source, str(source))

    def test_ignores_other_game(self):
        self.put("VPinMAME/altcolor/other_rom/other_rom.cROMc")
        self.assertIsNone(self.lookup("afm_113"))

    def test_secondary_game_key(self):
        source = self.put("VPinMAME/altcolor/ss_15/ss_15.cROMc")
        result = self.lookup("unused_key", "ss_15")
        self.assertEqual(result.source, str(source))
        self.assertEqual(result.game_id, "ss_15")

    def test_rejects_unsafe_game_path(self):
        self.put("VPinMAME/altcolor/afm_113/afm_113.cROMc")
        self.assertIsNone(self.lookup("../afm_113"))

    def test_empty_config_paths(self):
        self.assertIsNone(find_serum_colorization("", "", ["afm_113"]))

    def test_extracts_rom_from_external_override_before_embedded(self):
        ids = serum_game_ids(
            embedded_script='Const cGameName = "old_rom"',
            override_script='Const cGameName = "afm_113"\\n pGameName = "afm_113"',
            detected_rom="old_rom",
            table_name="Addams Family VPX",
        )
        self.assertEqual(ids[0], "afm_113")
        self.assertIn("old_rom", ids)
        self.put("VPinMAME/altcolor/afm_113/pin2dmd.cROMc")
        self.assertEqual(self.lookup(*ids).destination_name, "afm_113.cROMc")

    def test_vpinmame_parent_misconfigured_as_root(self):
        source = self.put("VPinMAME/altcolor/afm_113/pin2dmd.cROMc")
        found = find_serum_colorization(str(self.root), str(self.table), ["afm_113"])
        self.assertEqual(found.source, str(source))

    def test_altcolor_selected_directly(self):
        source = self.put("VPinMAME/altcolor/afm_113/pin2dmd.cROMc")
        found = find_serum_colorization(str(self.vpm / "altcolor"), str(self.table), ["afm_113"])
        self.assertEqual(found.source, str(source))

    def test_diagnostics_show_expected_folder_and_identifiers(self):
        self.put("VPinMAME/altcolor/another_rom/another_rom.cROMc")
        lines = serum_diagnostic_lines(str(self.vpm), ["afm_113"])
        self.assertTrue(any("afm_113" in x for x in lines))
        self.assertTrue(any("No matching ROM subfolder" in x for x in lines))


if __name__ == "__main__":
    unittest.main()
