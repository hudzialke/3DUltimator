"""Trwała historia i ulubione typy paczek."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from i18n import tr


@dataclass
class SavedPackage:
    dx: int
    dy: int
    dz: int
    count: int = 1
    stackable: bool = True
    rot_x: bool = True
    rot_y: bool = True
    rot_z: bool = True
    last_used: str = ""

    def signature(self) -> tuple:
        return (
            int(self.dx),
            int(self.dy),
            int(self.dz),
            bool(self.stackable),
            bool(self.rot_x),
            bool(self.rot_y),
            bool(self.rot_z),
        )

    def label(self) -> str:
        stack = tr("piętrowalna" if self.stackable else "niepiętrowalna")
        rots = []
        if self.rot_x:
            rots.append("X")
        if self.rot_y:
            rots.append("Y")
        if self.rot_z:
            rots.append("Z")
        rot_txt = ",".join(rots) if rots else tr("brak")
        return tr(
            "{count} szt.  |  {dx}×{dy}×{dz} cm  |  {stack}  |  rot: {rot_txt}",
            count=self.count, dx=self.dx, dy=self.dy, dz=self.dz, stack=stack, rot_txt=rot_txt,
        )


def library_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "3DUltimator"
    base.mkdir(parents=True, exist_ok=True)
    return base / "package_library.json"


class PackageLibrary:
    """Historia + ulubione zapisane lokalnie (przetrwa restart)."""

    MAX_HISTORY = 80

    def __init__(self, path: Path | None = None):
        self.path = path or library_path()
        self.history: List[SavedPackage] = []
        self.favorites: List[SavedPackage] = []
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.history = []
            self.favorites = []
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            self.history = []
            self.favorites = []
            return
        self.history = [self._from_dict(x) for x in data.get("history", [])]
        self.favorites = [self._from_dict(x) for x in data.get("favorites", [])]

    def save(self) -> None:
        data = {
            "history": [asdict(x) for x in self.history],
            "favorites": [asdict(x) for x in self.favorites],
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    @staticmethod
    def _from_dict(d: dict) -> SavedPackage:
        return SavedPackage(
            dx=int(d.get("dx", 50)),
            dy=int(d.get("dy", 50)),
            dz=int(d.get("dz", 50)),
            count=max(1, int(d.get("count", 1))),
            stackable=bool(d.get("stackable", True)),
            rot_x=bool(d.get("rot_x", True)),
            rot_y=bool(d.get("rot_y", True)),
            rot_z=bool(d.get("rot_z", True)),
            last_used=str(d.get("last_used", "")),
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def remember(self, pkg: SavedPackage) -> None:
        """Dodaj/aktualizuj wpis w historii (najnowsze na górze)."""
        entry = deepcopy(pkg)
        entry.last_used = self._now()
        sig = entry.signature()
        self.history = [h for h in self.history if h.signature() != sig]
        self.history.insert(0, entry)
        self.history = self.history[: self.MAX_HISTORY]
        # jeśli jest w ulubionych — zaktualizuj wymiary/ilość
        for i, fav in enumerate(self.favorites):
            if fav.signature() == sig:
                updated = deepcopy(entry)
                self.favorites[i] = updated
                break
        self.save()

    def is_favorite(self, pkg: SavedPackage) -> bool:
        sig = pkg.signature()
        return any(f.signature() == sig for f in self.favorites)

    def set_favorite(self, pkg: SavedPackage, favorite: bool) -> None:
        sig = pkg.signature()
        self.favorites = [f for f in self.favorites if f.signature() != sig]
        if favorite:
            entry = deepcopy(pkg)
            if not entry.last_used:
                entry.last_used = self._now()
            self.favorites.insert(0, entry)
        self.save()

    def remove_from_history(self, index: int) -> None:
        if 0 <= index < len(self.history):
            del self.history[index]
            self.save()

    def remove_favorite(self, index: int) -> None:
        if 0 <= index < len(self.favorites):
            del self.favorites[index]
            self.save()
