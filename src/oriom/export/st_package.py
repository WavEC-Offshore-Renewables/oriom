# oriom/export/st_package.py

from pathlib import Path
import json
import shutil
import tempfile
from datetime import datetime, timezone


KEYS_TO_REMOVE = [
    "wait_start_dict",
    "dur_net_port_dict",
    "transit_to_site_dict",
    "wait_site_dict",
    "dur_net_site_dict",
    "transit_to_port_dict",
    "wait_port_dict",
    "wtg_shutdown_dict",
    "wec_shutdown_dict",
    "pv_shutdown_dict",
    "tow_to_site_dict",
    "tow_to_site_id",
    "tow_to_port_dict",
    "tow_to_port_id"
]


def write_json(path: Path, data: object):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def write_json(path: Path, data: object):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def clean_obj(obj):
    # Remove additional attributes
    keys_to_remove = KEYS_TO_REMOVE

    for key in keys_to_remove:
        if key != 'operations_stats' and hasattr(obj, key):
            delattr(obj, key)

    # Overwrite Class with id
    if hasattr(obj, 'vessel1') and obj.vessel1 is not None:
        obj.vessel1 = obj.vessel1.id

    if hasattr(obj, 'vessel2') and obj.vessel2 is not None:
        obj.vessel2 = obj.vessel2.id

    if hasattr(obj, 'op_class') and obj.op_class is not None:
        obj.op_class = obj.op_class.id

    return obj

def object_to_dict(obj, visited=None):
    if visited is None:
        visited = set()

    if obj is None:
        return None

    if isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, (list, tuple)):
        return [object_to_dict(item, visited) for item in obj]

    if isinstance(obj, dict):
        return {
            str(k): object_to_dict(v, visited)
            for k, v in obj.items()
        }

    # evita loop ricorsivi negli oggetti
    obj_id = id(obj)

    if obj_id in visited:
        return f"<recursive reference: {type(obj).__name__}>"

    visited.add(obj_id)

    if hasattr(obj, "to_dict"):
        return object_to_dict(obj.to_dict(), visited)

    if hasattr(obj, "__dict__"):
        return {
            key: object_to_dict(value, visited)
            for key, value in vars(obj).items()
            if not key.startswith("_")
        }

    return str(obj)


def export_st_package(
    package_dir: str | Path,
    operations_stats: dict,
    overwrite: bool = False,
):
    """
    Export ORIOM outputs to a stable ST_ORIOM input package.

    This package should be read by ST_ORIOM without requiring direct access
    to ORIOM runtime objects.
    """

    package_dir = Path(package_dir)

    if package_dir.exists():
        if not overwrite:
            raise FileExistsError(f"Package directory already exists: {package_dir}")
        shutil.rmtree(package_dir)

    tmp_dir = Path(tempfile.mkdtemp(prefix="st_package_tmp_"))

    try:
        # Metadata
        manifest = {
            "schema_version": "1.0.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": "ORIOM",
            "target": "ST_ORIOM",
            "files": {
                "inputs": "inputs.json",
                "config": "config.json",
                "operations_stats": "stats/operations_stats.json",
            },
        }

        write_json(tmp_dir / "manifest.json", manifest)

        # Stats
        for perc in ['pmax', 'pmain']:
            operation_list = {op.id: clean_obj(op) for oper in operations_stats.values() for op in oper[perc]}
            write_json(tmp_dir / f"operations_stats_{perc}.json", object_to_dict(operation_list))

        # Atomic move at the end
        shutil.move(str(tmp_dir), str(package_dir))

    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise


if __name__ == '__main__':

    import pandas as pd
    class Config():
        def __init__(self):
            self.id = 'ciao'
            self.ST_MAIN = True

    class DUMMY():
        def __init__(self):
            self.id = 'ciao'
            self.oper_sched = pd.DataFrame({
                1:[5]*12,
                2:[6]*12
            }
            )

    class OP_DUMMY():
        def __init__(self, op_id):
            self.id = op_id
            self.ST_MAIN = True
            self.op_scheduler = DUMMY()

    export_st_package(
    package_dir=r"C:\Users\RiccardoMeda\temp",
    operations_stats = {
        'operation_site' :[OP_DUMMY('OP_001')],
        'operation_port' :[OP_DUMMY('OP_002')],
    },
    overwrite = True
)