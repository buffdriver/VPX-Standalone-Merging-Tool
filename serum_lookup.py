"""Locate Serum colorizations for one VPX table without scanning unrelated games.

VPX 10.8.1 expects a game-named file inside serum/<game>/
(prefer <game>.cROMc, otherwise <game>.cRZ).
"""
import os
import re
from pathlib import Path
from typing import NamedTuple, Optional, Sequence


class SerumMatch(NamedTuple):
    source: str
    game_id: str
    extension: str

    @property
    def destination_name(self):
        return self.game_id + (".cROMc" if self.extension == ".cromc" else ".cRZ")


def _resolve_dir(base: Path, *parts: str) -> Optional[Path]:
    """Resolve known path components without depending on disk case handling."""
    current = base
    for part in parts:
        if not current.is_dir():
            return None
        try:
            entries = list(current.iterdir())
        except OSError:
            return None
        found = next((p for p in entries if p.name == part and p.is_dir()), None)
        if found is None:
            found = next((p for p in entries if p.name.casefold() == part.casefold() and p.is_dir()), None)
        if found is None:
            return None
        current = found
    return current if current.is_dir() else None


def _find_file(folder: Path, game_id: str, extension: str) -> Optional[Path]:
    """Look within a game folder (including nested packaging subfolders)."""
    try:
        candidates = [
            file for file in folder.rglob("*")
            if file.is_file() and file.suffix.casefold() == extension
        ]
    except OSError:
        return None
    if not candidates:
        return None
    # A ROM-named file is best; some older packs are named pin2dmd or
    # use the pack's name, so allow those *inside the matching ROM folder*.
    def ranking(file):
        stem = file.stem.casefold()
        priority = 0 if stem == game_id.casefold() else (1 if stem == "pin2dmd" else 2)
        return (priority, len(file.relative_to(folder).parts), str(file).casefold())
    return min(candidates, key=ranking)


def _flat_file(folder: Path, game_id: str, extension: str) -> Optional[Path]:
    """Handle legacy altcolor/<rom>.cROMc without matching other ROMs."""
    try:
        for file in folder.iterdir():
            if (file.is_file() and file.stem.casefold() == game_id.casefold()
                    and file.suffix.casefold() == extension):
                return file
    except OSError:
        pass
    return None


def find_serum_colorization(
    vpinmame_directory: str, table_directory: str, game_ids: Sequence[str]
) -> Optional[SerumMatch]:
    """Find the best Serum file: matching game first, then cROMc before cRZ.

    Sources can be an existing Windows VPinMAME/altcolor installation or
    a table's local VPX 10.8.1 serum/pinmame/altcolor directories.
    Never recursively search the entire library for non-matching ROM files.
    """
    table_root = Path(table_directory) if table_directory else None
    vpm_root = Path(vpinmame_directory) if vpinmame_directory else None
    bases = []
    if table_root:
        bases.extend([
            (table_root, ("serum", "pinmame")),
            (table_root, ("serum",)),
            (table_root, ("pinmame", "altcolor")),
            (table_root, ("altcolor",)),
        ])
    if vpm_root:
        bases.extend([
            (vpm_root, ("serum", "pinmame")),
            (vpm_root, ("serum",)),
            (vpm_root, ("altcolor",)),
            (vpm_root, ("pinmame", "altcolor")),
        ])
        # Accept the VPinMAME root, its parent, or the altcolor directory
        # itself. The GUI calls the field "VPINMAME", which is easy to
        # mistake for a parent installation folder.
        if vpm_root.name.casefold() == "altcolor":
            bases.append((vpm_root, ()))
        if vpm_root.name.casefold() == "roms":
            bases.append((vpm_root.parent, ("altcolor",)))
        bases.append((vpm_root, ("VPinMAME", "altcolor")))

    seen = set()
    for raw_id in game_ids:
        game_id = (raw_id or "").strip()
        if (not game_id or game_id in (".", "..")
                or "/" in game_id or "\\" in game_id):
            continue
        if game_id.casefold() in seen:
            continue
        seen.add(game_id.casefold())
        # cROMc is preferred over legacy cRZ, even across source locations.
        for extension in (".cromc", ".crz"):
            for root, parts in bases:
                folder = _resolve_dir(root, *parts)
                if folder is None:
                    continue
                game_folder = _resolve_dir(folder, game_id)
                if game_folder:
                    file = _find_file(game_folder, game_id, extension)
                    if file:
                        return SerumMatch(str(file), game_id, extension)
                file = _flat_file(folder, game_id, extension)
                if file:
                    return SerumMatch(str(file), game_id, extension)
            # Some packs ship beside the VPX file rather than in altcolor.
            if table_root and table_root.is_dir():
                file = _flat_file(table_root, game_id, extension)
                if file:
                    return SerumMatch(str(file), game_id, extension)
    return None

# Keep this parser separate from VPX's embedded-script reader: external .vbs
# overrides may supply a different game ID, and should be checked first.
_GAME_ASSIGNMENT = re.compile(
    r'^\s*(?:Const\s+)?(?:cGameName|GameName|RomName|OptRom|pGameName)\s*=\s*"([^"\r\n]+)"',
    re.IGNORECASE | re.MULTILINE,
)


def serum_game_ids(
    embedded_script: str = "",
    override_script: str = "",
    detected_rom: str = "",
    table_name: str = "",
) -> list[str]:
    """Return literal game identifiers, prioritizing an external VBS override.

    Includes the existing embedded-script ROM as a fallback, and finally the
    table file base name. Never guess by selecting an unrelated ROM folder.
    """
    game_ids = []
    seen = set()

    def add(name):
        if name:
            name = name.strip()
            if name and name.casefold() not in seen:
                seen.add(name.casefold())
                game_ids.append(name)

    for text in (override_script or "", embedded_script or ""):
        for match in _GAME_ASSIGNMENT.finditer(text):
            add(match.group(1))
    add(detected_rom)
    add(table_name)
    return game_ids


def serum_diagnostic_lines(vpinmame_directory: str, game_ids: Sequence[str]) -> list[str]:
    """Short actionable scan diagnostics, for users with real-world VPinMAME trees."""
    root = Path(vpinmame_directory) if vpinmame_directory else None
    if root is None:
        return ["VPINMAME source is not set in the SOURCE FOLDERS panel."]
    if not root.is_dir():
        return [f"VPINMAME source folder does not exist: {root}"]
    if not game_ids:
        return [f"VPINMAME source: {root}", "No ROM identifier was found in the table or its .vbs override."]

    # The expected legacy location is the first place to inspect.
    possible_roots = [(_resolve_dir(root, "altcolor"), root / "altcolor")]
    if root.name.casefold() == "altcolor":
        possible_roots.insert(0, (root, root))
    possible_roots.append((_resolve_dir(root, "VPinMAME", "altcolor"), root / "VPinMAME" / "altcolor"))
    messages = [f"VPINMAME source: {root}",
                f"ROM identifiers tried: {', '.join(game_ids[:8])}"]
    available = [(p, expected) for p, expected in possible_roots if p is not None]
    if not available:
        messages.append("No altcolor directory found under this VPINMAME source.")
        messages.append(f"Expected path: {root / 'altcolor' / game_ids[0]}")
        return messages

    for base, expected in available[:2]:
        found = [(_resolve_dir(base, key), key) for key in game_ids]
        matches = [(folder, key) for folder, key in found if folder is not None]
        if matches:
            for folder, key in matches[:3]:
                try:
                    packs = [p.name for p in folder.rglob("*")
                             if p.is_file() and p.suffix.casefold() in (".cromc", ".crz")]
                    messages.append(f"Matching ROM folder: {folder} (Serum files: {', '.join(packs[:4]) or 'none'})")
                except OSError as exc:
                    messages.append(f"Cannot inspect {folder}: {exc}")
        else:
            messages.append(f"No matching ROM subfolder in: {base}")
            messages.append(f"Expected: {base / game_ids[0]}")
    return messages
