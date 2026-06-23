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
        if key != 'operations_stats':
            del obj[key]
    
    # Overwrite Class with id
    if hasattr(obj, 'vessel1') and obj.vessel1 is not None:
        obj.vessel1 = obj.vessel1.id
    if hasattr(obj, 'vessel2') and obj.vessel2 is not None:
        obj.vessel2 = obj.vessel1.id
    if hasattr(obj, 'op_class') and obj.op_class is not None:
        obj.op_class = obj.op_class.id

    return obj


def object_to_dict(object_dict):
    """
    Converts ORIOM objects into JSON-compatible dictionaries.

    Preferred order:
    1. Use obj.to_dict() if available.
    2. Use obj.__dict__ as fallback.
    3. Return obj if already JSON-compatible.
    """

    if object_dict.keys() == 'operations_stats':
        clean_obj(object_dict.values())
        pass
    obj = object_dict.values()

    if obj is None:
        return None

    if isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, list):
        return [object_to_dict(item) for item in obj]

    if isinstance(obj, tuple):
        return [object_to_dict(item) for item in obj]

    if isinstance(obj, dict):
        return {str(k): object_to_dict(v) for k, v in obj.items()}

    if hasattr(obj, "to_dict"):
        return object_to_dict(obj.to_dict())

    if hasattr(obj, "__dict__"):
        return {
            key: object_to_dict(value)
            for key, value in obj.__dict__.items()
            if not key.startswith("_")
        }

    return str(obj)


def export_st_package(
    package_dir: str | Path,
    Config: object,
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

        # Main objects
        write_json(tmp_dir / "config.json", object_to_dict({'Config': Config}))

        # Stats
        write_json(tmp_dir / "stats" / "operations_stats.json", object_to_dict({'operations_stats': operations_stats}))

        # Atomic move at the end
        shutil.move(str(tmp_dir), str(package_dir))

    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise
