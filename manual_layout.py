"""Geometry for smooth dragging with a one-centimetre cargo gap."""

from packing import _inside_container


def snap_drag_delta(boxes, selected, starts, delta, container, tolerance, gap=1.0):
    """Snap one shared translation; preserve all relative group positions.

    Container walls have no padding. Cargo faces attract at `gap` centimetres.
    Movement away from those faces is continuous, without a coarse grid.
    """
    dx, dy = delta
    selected = set(selected)
    candidates = [[], []]
    for i in selected:
        box = boxes[i]
        start = starts[i]
        for axis, movement in enumerate((dx, dy)):
            origin, extent = start[axis], box.size[axis]
            targets = [0.0, container[axis] - extent]
            for j, other in enumerate(boxes):
                if j in selected:
                    continue
                # Only cargo on overlapping vertical levels is adjacent.
                if (start[2] >= other.position[2] + other.size[2]
                        or start[2] + box.size[2] <= other.position[2]):
                    continue
                cross_axis = 1 - axis
                cross_start = start[cross_axis] + delta[cross_axis]
                # A distant face elsewhere in the truck must not attract the
                # pointer. Only faces that actually face this box can dock.
                if (cross_start >= other.position[cross_axis] + other.size[cross_axis]
                        or cross_start + box.size[cross_axis] <= other.position[cross_axis]):
                    continue
                left = other.position[axis]
                right = left + other.size[axis]
                targets.extend((left - extent - gap, right + gap))
            for target in targets:
                shift = target - origin
                distance = abs(shift - movement)
                if distance <= tolerance:
                    candidates[axis].append((distance, shift))
    if candidates[0]:
        dx = min(candidates[0])[1]
    if candidates[1]:
        dy = min(candidates[1])[1]
    return dx, dy


def inside(box, container):
    return _inside_container(box.position, box.size, *container)
