#saiftherehman
"""
Split shared NASTRAN property IDs across disconnected FE bodies.

This script finds connected FE bodies based on element adjacency using ANSA
Neighb(). It then detects any property id (PID) that is applied to more than one
body and makes a clone of that PID for each additional body so each body has a
unique property assignment.

Run inside ANSA: Scripts -> Run Script -> select this file.
"""

from collections import defaultdict
from ansa import base, constants

FE_DECK = constants.NASTRAN
FE_TYPES = ("SHELL", "SOLID")
DRY_RUN = False


def collect_all_fe_elements():
    elems = []
    for etype in FE_TYPES:
        elems.extend(base.CollectEntities(FE_DECK, None, etype) or [])
    return elems


def find_fe_bodies(elements):
    remaining = {elem._id: elem for elem in elements}
    bodies = []

    while remaining:
        _, start_elem = next(iter(remaining.items()))
        base.Or(entities=[start_elem])
        base.Neighb("ALL")

        body = []
        for etype in FE_TYPES:
            body.extend(base.CollectEntities(FE_DECK, None, etype,
                                            filter_visible=True) or [])
        for elem in body:
            remaining.pop(elem._id, None)
        bodies.append(body)

    return bodies


def get_element_pid(elem):
    values = elem.get_entity_values(FE_DECK, ("PID", "__prop__"))
    pid = values.get("PID")
    if pid is None:
        pid = values.get("__prop__")

    if hasattr(pid, "_id"):
        return pid._id
    if isinstance(pid, int):
        return pid
    try:
        return int(pid)
    except (TypeError, ValueError):
        return None


def clone_property(prop):
    card_type = prop.ansa_type(FE_DECK)
    new_prop = base.CreateEntity(FE_DECK, card_type, {})
    if new_prop is None:
        fields = [f for f in prop.card_fields(FE_DECK) if f.lower() != "type"]
        values = prop.get_entity_values(FE_DECK, tuple(fields))
        fallback = {}
        for key in ("MID", "MID1", "MID2", "MID3", "T", "ELFORM", "NIP"):
            if key in values and values[key] is not None:
                fallback[key] = values[key]._id if hasattr(values[key], "_id") else values[key]
        if fallback:
            new_prop = base.CreateEntity(FE_DECK, card_type, fallback)

    if new_prop is None:
        raise RuntimeError(
            f"Failed to create blank property for cloning {prop._id} ({card_type})"
        )

    fields = [f for f in prop.card_fields(FE_DECK) if f.lower() != "type"]
    values = prop.get_entity_values(FE_DECK, tuple(fields))

    clone_fields = {}
    for name, value in values.items():
        if name == "PID" or value is None:
            continue
        if "/" in name or name in {
            "keyword", "element type", "PSHLN1", "Name", "FROZEN_ID",
            "FROZEN_DELETE", "DEFINED", "TRIM", "USE_IN_MODEL", "INTERFACE",
            "NUMBERING_RULE_NAME", "SUBOPTION_NODES", "SUBOPTION_ELEMENTS",
            "SUBOPTION_MATERIALS", "PRESERVE", "FORCE", "COLOR_R",
            "COLOR_G", "COLOR_B", "TRANSPARENCY", "drawing/PerPidDrawing",
            "drawing/Shadow", "drawing/Wire", "drawing/Perimeters",
            "User/cad_material", "User/cad_thickness", "User/original_name",
            "User/CAD/Geometric Set Path", "User/CAD/Name",
            "User/CAD/Original Name", "User/CAD/ColorId",
            "User/CAD/Geometric Set", "User/CAD/LayerId/Name",
            "User/CAD/LayerId/Description", "User/CAD/StringMetaData/Material",
            "User/CAD/Material Name", "Labels", "Num.Elem", "Comment",
            "MBContainers",
        }:
            continue
        if hasattr(value, "_id"):
            clone_fields[name] = value._id
        else:
            clone_fields[name] = value

    if clone_fields:
        try:
            new_prop.set_entity_values(FE_DECK, clone_fields)
        except Exception:
            raise RuntimeError(
                f"Failed to populate cloned property {new_prop._id} "
                f"from original {prop._id} ({card_type})"
            )

    return new_prop


def reassign_elements_to_pid(elements, old_pid, new_pid):
    for elem in elements:
        current_pid = get_element_pid(elem)
        if current_pid == old_pid:
            elem.set_entity_values(FE_DECK, {"PID": new_pid})


def main():
    all_elements = collect_all_fe_elements()
    if not all_elements:
        print("ERROR: no FE elements found.")
        return

    bodies = find_fe_bodies(all_elements)
    print(f"Found {len(bodies)} disconnected FE body(ies).\n")

    body_pid_map = []
    pid_to_bodies = defaultdict(list)

    for body_index, body in enumerate(bodies, start=1):
        pid_map = defaultdict(list)
        for elem in body:
            pid = get_element_pid(elem)
            if pid is None:
                continue
            pid_map[pid].append(elem)
        body_pid_map.append(pid_map)
        for pid in pid_map:
            pid_to_bodies[pid].append(body_index)

    shared_pids = {pid: idxs for pid, idxs in pid_to_bodies.items()
                   if len(idxs) > 1}
    if not shared_pids:
        print("No shared PIDs found across disconnected FE bodies.")
        return

    print("Shared PIDs detected across bodies:")
    for pid, body_indices in shared_pids.items():
        print(f"  PID {pid} used by bodies: {body_indices}")

    print("\nResolving shared PIDs by cloning them for each additional body...")
    created_props = []
    reassigned = 0

    for pid, body_indices in shared_pids.items():
        original_body = body_indices[0]
        prop = base.GetEntity(FE_DECK, "__PROPERTIES__", pid)
        if prop is None:
            print(f"  WARNING: could not find property entity for PID {pid}")
            continue

        for body_index in body_indices[1:]:
            elems = body_pid_map[body_index - 1][pid]
            if not elems:
                continue

            if DRY_RUN:
                print(f"  DRY RUN: would clone PID {pid} for body {body_index}"
                      f" and reassign {len(elems)} element(s)")
                reassigned += len(elems)
                continue

            new_prop = clone_property(prop)
            created_props.append(new_prop)
            reassign_elements_to_pid(elems, pid, new_prop._id)
            reassigned += len(elems)
            print(f"  Cloned PID {pid} -> {new_prop._id} for body {body_index}"
                  f" and reassigned {len(elems)} element(s)")

    print("\nSummary:")
    print(f"  Shared PIDs resolved: {len(shared_pids)}")
    print(f"  Elements reassigned: {reassigned}")
    if not DRY_RUN:
        print(f"  Created {len(created_props)} new property(ies).")
    else:
        print("  DRY RUN mode: no properties were actually created.")


if __name__ == '__main__':
    main()
