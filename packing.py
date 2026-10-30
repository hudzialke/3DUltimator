"""Orthogonal cargo packing with multiple starts and bounded backtracking."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple
from i18n import tr

Size = Tuple[int, int, int]
Pos = Tuple[float, float, float]


@dataclass(frozen=True)
class PackItem:
    package_index: int
    dx: int
    dy: int
    dz: int
    stackable: bool
    rot_x: bool
    rot_y: bool
    rot_z: bool


@dataclass
class PackedBox:
    package_index: int
    position: Pos  # lower-back-left corner (x, y, z)
    size: Size
    overflow: bool = False
    stackable: bool = True


@dataclass(frozen=True)
class LayoutIssue:
    index: int
    kind: str
    detail: str
    other_index: int | None = None


def generate_orientations(item: PackItem) -> List[Size]:
    """All distinct (dx, dy, dz) reachable via allowed 90° axis rotations."""
    start: Size = (item.dx, item.dy, item.dz)
    q: deque[Size] = deque([start])
    seen = {start}
    out: List[Size] = []

    def rot_x(s: Size) -> Size:
        sx, sy, sz = s
        return sx, sz, sy

    def rot_y(s: Size) -> Size:
        sx, sy, sz = s
        return sz, sy, sx

    def rot_z(s: Size) -> Size:
        sx, sy, sz = s
        return sy, sx, sz

    while q:
        cur = q.popleft()
        out.append(cur)
        for fn, flag in ((rot_x, item.rot_x), (rot_y, item.rot_y), (rot_z, item.rot_z)):
            if not flag:
                continue
            nxt = fn(cur)
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return out


def _aabb_overlap(a_pos: Pos, a_size: Tuple[float, float, float], b_pos: Pos, b_size: Tuple[float, float, float]) -> bool:
    ax, ay, az = a_pos
    adx, ady, adz = a_size
    bx, by, bz = b_pos
    bdx, bdy, bdz = b_size
    return (
        ax < bx + bdx
        and ax + adx > bx
        and ay < by + bdy
        and ay + ady > by
        and az < bz + bdz
        and az + adz > bz
    )


def _inside_container(pos: Pos, size: Size, cx: float, cy: float, cz: float) -> bool:
    x, y, z = pos
    dx, dy, dz = size
    return (
        x >= 0
        and y >= 0
        and z >= 0
        and x + dx <= cx + 1e-9
        and y + dy <= cy + 1e-9
        and z + dz <= cz + 1e-9
    )


def _collides(pos: Pos, size: Size, placed: Sequence[PackedBox]) -> bool:
    for other in placed:
        if other.overflow:
            continue
        if _aabb_overlap(pos, size, other.position, other.size):
            return True
    return False


def can_occupy(
    pos: Pos,
    size: Tuple[float, float, float],
    container: Tuple[float, float, float],
    others: Sequence[Tuple[Pos, Tuple[float, float, float]]],
) -> bool:
    """True if AABB fits in container and does not overlap any other AABB."""
    cx, cy, cz = container
    x, y, z = pos
    dx, dy, dz = size
    if not (
        x >= -1e-9
        and y >= -1e-9
        and z >= -1e-9
        and x + dx <= cx + 1e-9
        and y + dy <= cy + 1e-9
        and z + dz <= cz + 1e-9
    ):
        return False
    for opos, osize in others:
        if _aabb_overlap(pos, (dx, dy, dz), opos, osize):
            return False
    return True


def validate_layout(
    boxes: Sequence[Tuple[Pos, Tuple[float, float, float]]],
    container: Tuple[float, float, float],
    *,
    stackable: Sequence[bool] | None = None,
) -> List[LayoutIssue]:
    """Validate bounds, collisions and, when supplied, stacking rules."""
    issues: List[LayoutIssue] = []
    cx, cy, cz = container

    for i, (pos, size) in enumerate(boxes):
        x, y, z = pos
        dx, dy, dz = size
        if not (
            x >= -1e-9
            and y >= -1e-9
            and z >= -1e-9
            and x + dx <= cx + 1e-9
            and y + dy <= cy + 1e-9
            and z + dz <= cz + 1e-9
        ):
            detail_bits: list[str] = []
            if x < -1e-9:
                detail_bits.append(tr("wychodzi poza lewą krawędź"))
            if y < -1e-9:
                detail_bits.append(tr("wychodzi poza dolną krawędź"))
            if z < -1e-9:
                detail_bits.append(tr("schodzi poniżej podłogi"))
            if x + dx > cx + 1e-9:
                detail_bits.append(tr("wychodzi poza długość X"))
            if y + dy > cy + 1e-9:
                detail_bits.append(tr("wychodzi poza szerokość Y"))
            if z + dz > cz + 1e-9:
                detail_bits.append(tr("wychodzi poza wysokość Z"))
            issues.append(
                LayoutIssue(
                    index=i,
                    kind="out_of_bounds",
                    detail=", ".join(detail_bits) or tr("poza przestrzenią ładunkową"),
                )
            )

    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if _aabb_overlap(boxes[i][0], boxes[i][1], boxes[j][0], boxes[j][1]):
                issues.append(
                    LayoutIssue(
                        index=i,
                        kind="collision",
                        detail=tr("koliduje z paczką {number}", number=j + 1),
                        other_index=j,
                    )
                )
                issues.append(
                    LayoutIssue(
                        index=j,
                        kind="collision",
                        detail=tr("koliduje z paczką {number}", number=i + 1),
                        other_index=i,
                    )
                )

    if stackable is not None:
        packed = [PackedBox(i, pos, size, stackable=stackable[i])
                  for i, (pos, size) in enumerate(boxes)]
        for i, box in enumerate(packed):
            if not _supported(box.position, box.size, packed[:i] + packed[i + 1:]):
                issues.append(LayoutIssue(i, "support", tr("brak podparcia lub obciążenie paczki niepiętrowalnej")))
    return issues


def _candidate_positions(
    size: Tuple[float, float, float],
    container: Tuple[float, float, float],
    others: Sequence[Tuple[Pos, Tuple[float, float, float]]],
    prefer_pos: Pos | None,
    old_size: Tuple[float, float, float] | None,
) -> List[Pos]:
    """Generate placement candidates, nearest-to-original first later."""
    cx, cy, cz = container
    dx, dy, dz = size
    cands: List[Pos] = []
    seen: set[Tuple[float, float, float]] = set()

    def add(p: Pos) -> None:
        key = (round(p[0], 3), round(p[1], 3), round(p[2], 3))
        if key in seen:
            return
        seen.add(key)
        cands.append(p)

    if prefer_pos is not None:
        px, py, pz = prefer_pos
        add((px, py, pz))
        if old_size is not None:
            odx, ody, _odz = old_size
            # środek stopy XY bez zmian
            cx0 = px + odx / 2.0
            cy0 = py + ody / 2.0
            add((cx0 - dx / 2.0, cy0 - dy / 2.0, pz))
        add((0.0, 0.0, pz))
        add((0.0, py, pz))
        add((px, 0.0, pz))

    add((0.0, 0.0, 0.0))

    for opos, osize in others:
        ox, oy, oz = opos
        odx, ody, odz = osize
        z_levels = {0.0, oz, oz + odz}
        if prefer_pos is not None:
            z_levels.add(prefer_pos[2])
        for z in z_levels:
            add((ox + odx, oy, z))
            add((ox, oy + ody, z))
            add((ox + odx, oy + ody, z))
            add((ox, oy, z))

    # Grubsza siatka po podłodze — wykorzystuje wolne 485×220
    step_x = max(10.0, min(dx, 40.0))
    step_y = max(10.0, min(dy, 40.0))
    z0 = prefer_pos[2] if prefer_pos is not None else 0.0
    x = 0.0
    while x + dx <= cx + 1e-9:
        y = 0.0
        while y + dy <= cy + 1e-9:
            add((x, y, z0))
            if z0 > 0:
                add((x, y, 0.0))
            y += step_y
        x += step_x

    return cands


def find_placement(
    size: Tuple[float, float, float],
    container: Tuple[float, float, float],
    others: Sequence[Tuple[Pos, Tuple[float, float, float]]],
    *,
    prefer_pos: Pos | None = None,
    old_size: Tuple[float, float, float] | None = None,
) -> Pos | None:
    """
    Find a free pose for `size` inside container.
    Prefers positions close to the original footprint center.
    """
    if prefer_pos is not None and old_size is not None:
        ox, oy, oz = prefer_pos
        odx, ody, _ = old_size
        prefer_center = (ox + odx / 2.0, oy + ody / 2.0, oz)
    elif prefer_pos is not None:
        prefer_center = prefer_pos
    else:
        prefer_center = (0.0, 0.0, 0.0)

    dx, dy, dz = size
    scored: List[Tuple[float, Pos]] = []
    for pos in _candidate_positions(size, container, others, prefer_pos, old_size):
        if not can_occupy(pos, size, container, others):
            continue
        px, py, pz = pos
        cx0 = px + dx / 2.0
        cy0 = py + dy / 2.0
        # Kara za zmianę wysokości — wolimy ten sam poziom
        dist = (
            (cx0 - prefer_center[0]) ** 2
            + (cy0 - prefer_center[1]) ** 2
            + 4.0 * (pz - prefer_center[2]) ** 2
        )
        scored.append((dist, pos))

    if not scored:
        return None
    scored.sort(key=lambda t: t[0])
    return scored[0][1]


def _supported(pos: Pos, size: Size, placed: Sequence[PackedBox]) -> bool:
    """Floor or sufficient support from stackable boxes below."""
    x, y, z = pos
    dx, dy, dz = size
    if z <= 1e-9:
        return True

    area = float(dx * dy)
    if area <= 0:
        return False
    supported = 0.0
    for other in placed:
        if other.overflow:
            continue
        ox, oy, oz = other.position
        odx, ody, odz = other.size
        top = oz + odz
        if abs(top - z) > 1e-6:
            continue
        ix0 = max(x, ox)
        iy0 = max(y, oy)
        ix1 = min(x + dx, ox + odx)
        iy1 = min(y + dy, oy + ody)
        if ix1 > ix0 and iy1 > iy0:
            if not other.stackable:
                return False
            supported += (ix1 - ix0) * (iy1 - iy0)
    return supported >= area * 0.5 - 1e-6


def _can_place(
    pos: Pos,
    size: Size,
    item_stackable: bool,
    cx: float,
    cy: float,
    cz: float,
    placed: Sequence[PackedBox],
) -> bool:
    if not _inside_container(pos, size, cx, cy, cz):
        return False
    if _collides(pos, size, placed):
        return False
    if not _supported(pos, size, placed):
        return False
    # Non-stackable items prefer the floor, but may sit on stackable cargo.
    # Nothing special beyond support check (support already requires stackable below).
    _ = item_stackable
    return True


def _placement_score(pos: Pos, size: Size, cx: float, cy: float, cz: float) -> Tuple[float, ...]:
    """Lower is better: prefer low Z, then tight pack (small leftover), then near origin."""
    x, y, z = pos
    dx, dy, dz = size
    leftover = (cx - (x + dx)) + (cy - (y + dy)) + (cz - (z + dz))
    return (z, leftover, x + y, x, y)


def _new_extreme_points(pos: Pos, size: Size) -> List[Pos]:
    x, y, z = pos
    dx, dy, dz = size
    return [
        (x + dx, y, z),
        (x, y + dy, z),
        (x, y, z + dz),
    ]


def _pack_greedy_legacy(
    container: Tuple[float, float, float],
    items: Iterable[PackItem],
    initial_placed: Sequence[PackedBox] | None = None,
) -> List[PackedBox]:
    """
    Pack items into one bin using extreme-point Best Fit.
    Items that do not fit are returned as overflow (placed beside the bin for display).
    `initial_placed` — stałe przeszkody już w przestrzeni (np. nieobrácane paczki).
    """
    cx, cy, cz = container
    item_list = list(items)

    # Volume descending; among equal volume, stackable first (better base for stacking).
    item_list.sort(
        key=lambda it: (
            -(it.dx * it.dy * it.dz),
            0 if it.stackable else 1,
        )
    )

    placed: List[PackedBox] = [
        PackedBox(
            package_index=b.package_index,
            position=b.position,
            size=b.size,
            overflow=False,
            stackable=b.stackable,
        )
        for b in (initial_placed or [])
        if not b.overflow
    ]
    extreme: List[Pos] = [(0.0, 0.0, 0.0)]
    for b in placed:
        for ep in _new_extreme_points(b.position, b.size):
            if ep[0] < cx - 1e-9 and ep[1] < cy - 1e-9 and ep[2] < cz - 1e-9:
                if ep not in extreme:
                    extreme.append(ep)
    overflow_y = 0.0

    newly: List[PackedBox] = []

    for item in item_list:
        orients = generate_orientations(item)
        best: Tuple[Tuple[float, ...], Pos, Size] | None = None

        for pivot in extreme:
            for orient in orients:
                if not _can_place(pivot, orient, item.stackable, cx, cy, cz, placed):
                    continue
                score = _placement_score(pivot, orient, cx, cy, cz)
                if best is None or score < best[0]:
                    best = (score, pivot, orient)

        if best is None:
            # Also try pivots derived from tops of stackable boxes (in case EP missed).
            for other in placed:
                if other.overflow or not other.stackable:
                    continue
                ox, oy, oz = other.position
                odx, ody, odz = other.size
                for pivot in (
                    (ox, oy, oz + odz),
                    (ox + odx, oy, oz + odz),
                    (ox, oy + ody, oz + odz),
                ):
                    for orient in orients:
                        if not _can_place(pivot, orient, item.stackable, cx, cy, cz, placed):
                            continue
                        score = _placement_score(pivot, orient, cx, cy, cz)
                        if best is None or score < best[0]:
                            best = (score, pivot, orient)

        if best is None:
            dx, dy, dz = item.dx, item.dy, item.dz
            box = PackedBox(
                package_index=item.package_index,
                position=(cx + 50.0, overflow_y, 0.0),
                size=(dx, dy, dz),
                overflow=True,
                stackable=item.stackable,
            )
            newly.append(box)
            overflow_y += dy + 20
            continue

        _, pos, size = best
        box = PackedBox(
            package_index=item.package_index,
            position=pos,
            size=size,
            overflow=False,
            stackable=item.stackable,
        )
        placed.append(box)
        newly.append(box)

        extreme = [p for p in extreme if p != pos]
        for ep in _new_extreme_points(pos, size):
            if ep[0] < cx - 1e-9 and ep[1] < cy - 1e-9 and ep[2] < cz - 1e-9:
                if ep not in extreme:
                    extreme.append(ep)

        cleaned: List[Pos] = []
        for ep in extreme:
            inside = False
            for b in placed:
                if b.overflow:
                    continue
                bx, by, bz = b.position
                bdx, bdy, bdz = b.size
                if (
                    bx <= ep[0] < bx + bdx - 1e-9
                    and by <= ep[1] < by + bdy - 1e-9
                    and bz <= ep[2] < bz + bdz - 1e-9
                ):
                    inside = True
                    break
            if not inside:
                cleaned.append(ep)
        extreme = cleaned

    return newly


def pack_single_bin(
    container: Tuple[float, float, float],
    items: Iterable[PackItem],
    initial_placed: Sequence[PackedBox] | None = None,
) -> List[PackedBox]:
    """Try alternative orders, orientations and earlier choices before overflow.

    The search is bounded; overflow means no complete layout was found, rather
    than a mathematical proof that packing is impossible. Fixed boxes are never
    moved and are excluded from the returned list, as in the original API.
    """
    from packing_search import search_packing

    return search_packing(container, list(items), initial_placed or [])
