"""Locate Serum colorizations for one VPX table without scanning unrelated games.

VPX 10.8.1 expects a game-named file inside serum/<game>/
(prefer <game>.cROMc, otherwise <game>.cRZ).
"""
import os
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
