import csv
import os
from datetime import datetime
from pathlib import Path
import shutil
import yaml
import oriom.main


METOCEAN_FILE_KEYS = [
    "metocean file location",
    "metocean file location tow1",
    "metocean file port",
]

DATETIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%y %H:%M:%S",
    "%d-%m-%y %H:%M:%S",
    "%d-%m-%y %H:%M",
    "%d-%m-%Y %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%m/%d/%Y %H:%M",
]

INSPECTION_FILES = {
    "operations_inspections_site.yaml",
    "operations_inspections_port.yaml",
}

OPERATION_COST_KEYS = ["tech_cost", "parts_cost", "other_costs", "port_costs"]
VESSEL_COST_KEYS = [
    "daily_charter",
    "annual_contract",
    "monthly_contract_cost",
    "mobilisation_cost",
]
ROV_COST_KEYS = ["daily_charter", "cost_half_day"]
GLOBAL_COST_KEYS = [
    "vessel cost year",
    "port cost day",
    "fuel cost hfo",
    "fuel cost mgo",
    "fuel cost mdo",
    "port cost annual",
    "technicians year",
]


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def save_yaml(path: Path, data) -> None:
    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(data, file, sort_keys=False)


def parse_timestamp(text: str):
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue

    return None


def extend_metocean(
    base_dir: Path,
    start_year: int,
    start_month: int,
    lifetime: int,
) -> None:
    tseries_path = base_dir / "inputs_tseries.yaml"

    if not tseries_path.exists():
        return

    tseries = load_yaml(tseries_path)

    entry = tseries.get(METOCEAN_FILE_KEYS[0]) or {}
    source = entry.get("value")

    if not source:
        return

    source_path = Path(source)

    if not source_path.is_absolute():
        source_path = Path.cwd() / source_path

    if not source_path.exists():
        return

    with source_path.open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    if len(rows) < 2:
        return

    first = parse_timestamp(rows[0]["datetime"])
    second = parse_timestamp(rows[1]["datetime"])
    last = parse_timestamp(rows[-1]["datetime"])

    if not (first and second and last):
        return

    needed_end = datetime(start_year + lifetime, start_month, 1)

    if last >= needed_end:
        return

    step = second - first
    extended_path = base_dir / "metocean_extended.csv"

    with extended_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()

        stamp = first
        index = 0

        while stamp < needed_end:
            row = dict(rows[index % len(rows)])
            row["datetime"] = stamp.strftime("%Y-%m-%d %H:%M")
            writer.writerow(row)

            stamp += step
            index += 1

    for key, entry in tseries.items():
        is_metocean_file = (
            key in METOCEAN_FILE_KEYS
            or key.startswith("metocean file location tow")
        )

        if is_metocean_file and isinstance(entry, dict):
            entry["value"] = str(extended_path)

    save_yaml(tseries_path, tseries)


def find_campaign_month(failures: list) -> int:
    for failure in failures:
        strategy = str(failure.get("maintenance_strategy", "")).lower()

        if strategy == "specific month" and failure.get("preferred_month") is not None:
            return int(failure["preferred_month"])

    raise ValueError("No baseline corrective campaign month was found.")


def update_failures(base_dir: Path, request: dict, cost_multiplier: float) -> None:
    reliability = request.get("reliability")
    corrective = request.get("corrective")

    if not (reliability or corrective) and cost_multiplier == 1.0:
        return

    path = base_dir / "failures.yaml"
    failures = load_yaml(path)

    if corrective and corrective["noncritical_strategy"] == "campaign":
        campaign_month = find_campaign_month(failures)

    for failure in failures:
        if reliability:
            failure["probability_failure"] = (
                float(failure["probability_failure"])
                * float(reliability["failure_rate_multiplier"])
            )

            lead_time_days = reliability.get("major_component_lead_time_days")

            if lead_time_days is not None and failure.get("potential_shutdown"):
                failure["lead_time"] = int(lead_time_days) * 24

        if corrective:
            strategy = corrective["noncritical_strategy"]

            if failure.get("potential_shutdown") or strategy == "immediate":
                failure["maintenance_strategy"] = "Immediately"
                failure.pop("preferred_month", None)

            elif strategy == "defer":
                failure["maintenance_strategy"] = "Never repair"
                failure.pop("preferred_month", None)

            else:
                failure["maintenance_strategy"] = "Specific month"
                failure["preferred_month"] = campaign_month

                if corrective.get("maximum_deferral_days") is not None:
                    failure["lead_time"] = int(corrective["maximum_deferral_days"]) * 24

        if cost_multiplier != 1.0 and failure.get("parts_cost") is not None:
            failure["parts_cost"] = float(failure["parts_cost"]) * cost_multiplier

    save_yaml(path, failures)


def update_operations(base_dir: Path, request: dict, cost_multiplier: float) -> None:
    inspections = request.get("inspections")
    working_pattern = request.get("working_pattern")
    timing = request.get("preventive_timing")

    if not (inspections or working_pattern or timing) and cost_multiplier == 1.0:
        return

    for path in sorted(base_dir.glob("operations_*.yaml")):
        operations = load_yaml(path)

        if not isinstance(operations, list):
            continue

        for operation in operations:
            if inspections and path.name in INSPECTION_FILES:
                operation["periodicity"] = float(inspections["interval_months"]) / 12.0

                if inspections.get("preferred_start_month") is not None:
                    operation["months"] = int(inspections["preferred_start_month"])

            # Without "months", oriom considers all months (InspectionSite
            # falls back to list(range(1, 13))).
            if timing == "asap" and path.name in INSPECTION_FILES:
                operation.pop("months", None)

            if working_pattern and "double_shift" in operation:
                operation["double_shift"] = working_pattern == "double_shift"

            if cost_multiplier != 1.0:
                for key in OPERATION_COST_KEYS:
                    if operation.get(key) is not None:
                        operation[key] = float(operation[key]) * cost_multiplier

        save_yaml(path, operations)


def update_vessels(base_dir: Path, request: dict, cost_multiplier: float) -> None:
    vessel_request = request.get("vessels")

    if not vessel_request and cost_multiplier == 1.0:
        return

    path = base_dir / "vessels.yaml"
    vessels = load_yaml(path)

    if vessel_request:
        ctvs = [
            vessel for vessel in vessels
            if str(vessel.get("type", "")).lower() == "ctv"
        ]

        if not ctvs:
            raise ValueError("No CTV was found in the farm's vessel inputs.")

        for ctv in ctvs:
            ctv["number_vessels"] = int(vessel_request["ctv_quantity"])

    if cost_multiplier != 1.0:
        for vessel in vessels:
            for key in VESSEL_COST_KEYS:
                if vessel.get(key) is not None:
                    vessel[key] = float(vessel[key]) * cost_multiplier

    save_yaml(path, vessels)


def update_costs(base_dir: Path, economics: dict, cost_multiplier: float) -> None:
    if not economics:
        return

    path = base_dir / "inputs_costs.yaml"
    costs = load_yaml(path)

    if economics.get("electricity_value_eur_mwh") is not None:
        costs["electricity price"]["value"] = float(
            economics["electricity_value_eur_mwh"]
        )

    price_multiplier = float(economics.get("electricity_price_multiplier", 1.0))

    if price_multiplier != 1.0:
        costs["electricity price"]["value"] = (
            float(costs["electricity price"]["value"]) * price_multiplier
        )

    if cost_multiplier != 1.0:
        for key in GLOBAL_COST_KEYS:
            if key in costs and costs[key].get("value") is not None:
                costs[key]["value"] = float(costs[key]["value"]) * cost_multiplier

    save_yaml(path, costs)


def update_rovs(base_dir: Path, cost_multiplier: float) -> None:
    path = base_dir / "rovs.yaml"

    if cost_multiplier == 1.0 or not path.exists():
        return

    rovs = load_yaml(path)

    for rov in rovs:
        for key in ROV_COST_KEYS:
            if rov.get(key) is not None:
                rov[key] = float(rov[key]) * cost_multiplier

    save_yaml(path, rovs)


def apply_user_inputs(base_dir: Path, request: dict) -> None:
    year, month = map(int, request["planning_start"].split("-"))
    lifetime = int(request["planning_horizon_years"])

    stats_path = base_dir / "inputs_stats.yaml"
    stats = load_yaml(stats_path)

    stats["start year"]["value"] = year
    stats["start month"]["value"] = month
    stats["lifetime"]["value"] = lifetime

    condition = request.get("asset_condition")

    if condition:
        stats["period infant mortality"]["value"] = condition["infant_mortality_years"]
        stats["period wear out"]["value"] = condition["wear_out_years"]

    if request.get("execution_percentile") is not None:
        stats["percentile main"]["value"] = int(request["execution_percentile"])

    save_yaml(stats_path, stats)

    extend_metocean(base_dir, year, month, lifetime)

    economics = request.get("economics") or {}
    cost_multiplier = float(economics.get("cost_multiplier", 1.0))

    update_failures(base_dir, request, cost_multiplier)
    update_operations(base_dir, request, cost_multiplier)
    update_vessels(base_dir, request, cost_multiplier)
    update_costs(base_dir, economics, cost_multiplier)
    update_rovs(base_dir, cost_multiplier)


def normalise_paths(base_dir: Path) -> None:
    tseries_path = base_dir / "inputs_tseries.yaml"

    if not tseries_path.exists():
        return

    tseries = load_yaml(tseries_path)

    changed = False

    for entry in tseries.values():
        if not isinstance(entry, dict):
            continue

        value = entry.get("value")

        if isinstance(value, str) and "\\" in value:
            entry["value"] = value.replace("\\", "/")
            changed = True

    if changed:
        save_yaml(tseries_path, tseries)


def apply_fast_test_overrides(base_dir: Path) -> None:
    if os.environ.get("ORIOM_FAST_TEST") != "1":
        return

    gen_path = base_dir / "inputs_gen.yaml"

    if gen_path.exists():
        gen = load_yaml(gen_path)

        if isinstance(gen.get("number_runs"), dict):
            gen["number_runs"]["value"] = 1
            save_yaml(gen_path, gen)


def install(request: dict) -> None:
    def wrapper(dirs, base_file_excel, sharepoint_file_path, excel_file_path, form_name):
        for source in (Path(__file__).parent / "defaults").glob("*.yaml"):
            shutil.copy(source, dirs.base_dir)

        base_dir = Path(dirs.base_dir)
        normalise_paths(base_dir)
        apply_user_inputs(base_dir, request)
        apply_fast_test_overrides(base_dir)

    oriom.main.extract_input_from_excel = wrapper