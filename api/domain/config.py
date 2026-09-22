"""Build an ORIOM ``ConfigRun`` from an API request.

ORIOM's only supported input is an Excel form, so each farm maps to a form
baked into the image under ``forms/``.
"""
import os

from oriom.inputs.Configuration import ConfigRun

FORMS_DIR = os.environ.get("ORIOM_FORMS_DIR", os.path.join(os.getcwd(), "forms"))


def build_config(farm_id: str, job_id: str) -> ConfigRun:
    # The job id in PROJECT_NAME makes run_dir unique: oriom timestamps it
    # only to the second, so same-second starts would otherwise collide.
    return ConfigRun(
        PROJECT_NAME=f"{farm_id}_{job_id[:8]}",
        BASEFILES_FROM_EXCEL=False,
        EXCEL_FILE_PATH="unused",
        FORM_NAME="unused",
        STATISTICAL_CHART=True,
        ENERGY_AVAILABILITY_CALCULATION=True,
        ENERGY_STATISTICAL_CALCULATION=False,
        ST=False,
    )
