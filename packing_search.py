"""Deterministic multi-start packing and bounded search of alternative layouts."""

from __future__ import annotations

from random import Random
from time import monotonic

from packing import (PackItem, PackedBox, Pos, Size, _can_place,
                     _pack_greedy_legacy, generate_orientations)

SEARCH_SECONDS = 3.0
MAX_NODES = 20_000


def _quality(boxes):
    inside = [b for b in boxes if not b.overflow]
    return len(inside), sum(b.size[0] * b.size[1] * b.size[2] for b in inside)


def _result(items, layout, container):
    result = []
    outside_y = 0.0
    for i, item in enumerate(items):
        if i in layout:
            result.append(layout[i])
        else:
            result.append(PackedBox(item.package_index, (container[0] + 50, outside_y, 0),
                                    (item.dx, item.dy, item.dz), True, item.stackable))
            outside_y += item.dy + 20
    return result


def _score(pos, size, placed, mode):
    x, y, z = pos
    dx, dy, dz = size
    # Different row directions and footprint preferences avoid the original
    # tie that always preferred the dimensions entered by the user.
    if mode == 0:
        return z, y, x, dx, dy, dz
    if mode == 1:
        return z, x, y, dy, dx, dz
    if mode == 2:
        return z, y, x, dy, dx, dz
    if mode == 3:
        return z, x, y, dx, dy, dz
    ex = max([x + dx] + [b.position[0] + b.size[0] for b in placed])
    ey = max([y + dy] + [b.position[1] + b.size[1] for b in placed])
    ez = max([z + dz] + [b.position[2] + b.size[2] for b in placed])
    if mode == 4:
        return ez, ex * ey, z, y, x, dz
    return z, dz, ex * ey, y, x, dx


def _placements(item, orientations, placed, container, mode, deadline):
    """Face-aligned positions, including projections between different boxes.

    Combining X and Y faces also finds holes that the three original extreme
    points miss. Alignments to both walls and both ends of each face allow a
    differently rotated box to fill the remaining space.
    """
    cx, cy, cz = container
    candidates = []
    for size in orientations:
        dx, dy, dz = size
        levels = {0.0} | {b.position[2] + b.size[2] for b in placed if b.stackable}
        for z in sorted(levels):
            if z + dz > cz + 1e-9:
                continue
            active = [b for b in placed
                      if b.position[2] < z + dz and b.position[2] + b.size[2] > z]
            support = [b for b in placed if abs(b.position[2] + b.size[2] - z) < 1e-6]
            xs, ys = {0.0, cx - dx}, {0.0, cy - dy}
            for b in active + support:
                x, y, _ = b.position
                sx, sy, _ = b.size
                xs.update((x, x + sx, x - dx, x + sx - dx))
                ys.update((y, y + sy, y - dy, y + sy - dy))
            for y in sorted(v for v in ys if 0 <= v <= cy - dy + 1e-9):
                if monotonic() >= deadline:
                    return sorted(candidates)
                for x in sorted(v for v in xs if 0 <= v <= cx - dx + 1e-9):
                    pos = (x, y, z)
                    if _can_place(pos, size, item.stackable, cx, cy, cz, placed):
                        candidates.append((_score(pos, size, placed, mode), pos, size))
    return sorted(candidates)


def _row_layout(items, orientations, container, deadline):
    """Try mixed-orientation rows before the general 3D search.

    Choosing a whole row at once prevents a large early box from splitting
    space needed by several smaller boxes. Both truck directions are tried.
    """
    if len(items) > 24 or any(not sizes for sizes in orientations):
        return None
    if sum(min(s[0] * s[1] for s in sizes) for sizes in orientations) > container[0] * container[1]:
        return None
    for axis in (0, 1):
        across = 1 - axis
        length, width = container[axis], container[across]
        failed = set()
        layout = {}

        def rows(remaining, offset):
            if not remaining:
                return dict(layout)
            if monotonic() >= deadline or (remaining, offset) in failed:
                return None
            failed.add((remaining, offset))
            heights = sorted({s[across] for i in remaining for s in orientations[i]
                              if offset + s[across] <= width + 1e-9})
            candidates = []
            for height in heights:
                options = [(i, s) for i in remaining for s in orientations[i] if s[across] == height]
                # Build subsets in item order, so equivalent row permutations
                # do not consume the bounded search budget.
                subsets = []

                def subsets_for_row(start, used, chosen):
                    if monotonic() >= deadline or len(subsets) >= 512:
                        return
                    if chosen:
                        subsets.append((used, tuple(chosen)))
                    equivalent = set()
                    for k in range(start, len(options)):
                        i, size = options[k]
                        signature = (orientations[i], items[i].stackable, size)
                        if signature in equivalent or used + size[axis] > length + 1e-9:
                            continue
                        if chosen and i <= chosen[-1][0]:
                            continue
                        equivalent.add(signature)
                        subsets_for_row(k + 1, used + size[axis], chosen + [(i, size)])

                subsets_for_row(0, 0, [])
                for used, chosen in subsets:
                    candidates.append(((length - used) * height, -len(chosen), height, chosen))
            for _, _, height, chosen in sorted(candidates):
                cursor = 0.0
                for i, size in chosen:
                    pos = (cursor, offset, 0.0) if axis == 0 else (offset, cursor, 0.0)
                    layout[i] = PackedBox(items[i].package_index, pos, size, False, items[i].stackable)
                    cursor += size[axis]
                chosen_indices = {i for i, _ in chosen}
                result = rows(tuple(i for i in remaining if i not in chosen_indices), offset + height)
                if result is not None:
                    return result
                for i in chosen_indices:
                    del layout[i]
                if monotonic() >= deadline:
                    return None
            return None

        result = rows(tuple(range(len(items))), 0.0)
        if result is not None:
            return result
    return None


def search_packing(container, items, initial):
    fixed = [PackedBox(b.package_index, b.position, b.size, False, b.stackable)
             for b in initial if not b.overflow]
    if any(d <= 0 for d in container):
        raise ValueError("Wymiary przestrzeni muszą być dodatnie")
    if any(min(it.dx, it.dy, it.dz) <= 0 for it in items):
        raise ValueError("Wymiary paczki muszą być dodatnie")
    best = _pack_greedy_legacy(container, items, fixed)
    if not items or all(not b.overflow for b in best):
        return best

    deadline = monotonic() + SEARCH_SECONDS
    orientations = [tuple(s for s in generate_orientations(it)
                          if all(d <= bound + 1e-9 for d, bound in zip(s, container)))
                    for it in items]
    possible = [i for i, sizes in enumerate(orientations) if sizes]
    if not possible:
        return best
    if not fixed:
        rows = _row_layout(items, orientations, container, monotonic() + SEARCH_SECONDS * 0.1)
        if rows is not None:
            return _result(items, rows, container)
    volume = lambda i: items[i].dx * items[i].dy * items[i].dz
    keys = (
        lambda i: (-volume(i), not items[i].stackable),
        lambda i: (not items[i].stackable, -max(s[0] * s[1] for s in orientations[i]), -volume(i)),
        lambda i: (len(orientations[i]), -volume(i)),
        lambda i: (-max(items[i].dx, items[i].dy, items[i].dz), -volume(i)),
        lambda i: (not items[i].stackable, volume(i)),
    )
    orders = [sorted(possible, key=key) for key in keys]
    shuffled = list(possible)
    Random(0).shuffle(shuffled)
    orders.append(shuffled)
    best_quality = _quality(best)
    greedy_deadline = monotonic() + SEARCH_SECONDS * 0.4
    # Alternate rotation preferences first, then item orders.
    for trial in range(36):
        if monotonic() >= greedy_deadline:
            break
        order = orders[(trial // 6) % len(orders)]
        mode = trial % 6
        layout = {}
        placed = list(fixed)
        pending = list(order)
        while pending and monotonic() < greedy_deadline:
            deferred = []
            for i in pending:
                choices = _placements(items[i], orientations[i], placed, container, mode, greedy_deadline)
                if not choices:
                    deferred.append(i)
                    continue
                _, pos, size = choices[0]
                box = PackedBox(items[i].package_index, pos, size, False, items[i].stackable)
                placed.append(box)
                layout[i] = box
            if len(deferred) == len(pending):
                break
            pending = deferred
        result = _result(items, layout, container)
        quality = _quality(result)
        if quality > best_quality:
            best, best_quality = result, quality
        if best_quality[0] == len(items):
            return best

    # A necessary volume bound avoids spending search time proving an obvious
    # impossibility. The best partial layout from the trials is still returned.
    free_volume = container[0] * container[1] * container[2] - sum(
        b.size[0] * b.size[1] * b.size[2] for b in fixed)
    if sum(volume(i) for i in possible) > free_volume + 1e-9 or len(possible) != len(items):
        return best
    if not fixed and not any(it.stackable for it in items):
        if sum(min(s[0] * s[1] for s in sizes) for sizes in orientations) > container[0] * container[1]:
            return best
    # Keep recursion below Python's limit for very large cargo lists.
    if len(items) > 150:
        return best

    placed = list(fixed)
    layout = {}
    visited = set()
    nodes = 0

    def search(remaining):
        nonlocal nodes, best, best_quality
        nodes += 1
        if nodes > MAX_NODES or monotonic() >= deadline:
            return False
        if len(layout) > best_quality[0]:
            result = _result(items, layout, container)
            best, best_quality = result, _quality(result)
        if not remaining:
            return True
        # Labels of identical boxes do not matter for future geometry.
        state = (tuple(sorted((items[i].dx, items[i].dy, items[i].dz, items[i].stackable,
                               items[i].rot_x, items[i].rot_y, items[i].rot_z) for i in remaining)),
                 tuple(sorted((b.position, b.size, b.stackable) for b in placed)))
        if state in visited:
            return False
        visited.add(state)
        tried = set()
        for i in remaining:
            signature = (orientations[i], items[i].stackable)
            if signature in tried:
                continue
            tried.add(signature)
            choices = _placements(items[i], orientations[i], placed, container, 0, deadline)
            for _, pos, size in choices:
                if nodes > MAX_NODES or monotonic() >= deadline:
                    return False
                box = PackedBox(items[i].package_index, pos, size, False, items[i].stackable)
                layout[i] = box
                placed.append(box)
                if search(tuple(j for j in remaining if j != i)):
                    return True
                placed.pop()
                del layout[i]
        return False

    search(tuple(orders[0]))
    return best
