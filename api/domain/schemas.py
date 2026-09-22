from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class AssetCondition(BaseModel):
    infant_mortality_years: float = Field(ge=0)
    wear_out_years: float = Field(ge=0)


class Reliability(BaseModel):
    failure_rate_multiplier: float = Field(1.0, gt=0)
    major_component_lead_time_days: Optional[int] = Field(None, ge=0)


class Inspections(BaseModel):
    interval_months: float = Field(gt=0)
    preferred_start_month: Optional[int] = Field(None, ge=1, le=12)


class Corrective(BaseModel):
    noncritical_strategy: Literal["campaign", "immediate", "defer"] = "campaign"
    maximum_deferral_days: Optional[int] = Field(None, ge=0)


class Vessels(BaseModel): 
    ctv_quantity: int = Field(ge=1)


class Economics(BaseModel):
    electricity_value_eur_mwh: Optional[float] = Field(None, gt=0)
    electricity_price_multiplier: float = Field(1.0, gt=0)
    cost_multiplier: float = Field(1.0, gt=0)


class RunRequest(BaseModel):
    farm_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    planning_start: str = Field(pattern=r"^\d{4}-\d{2}$")
    planning_horizon_years: int = Field(ge=1)
    asset_condition: Optional[AssetCondition] = None
    reliability: Optional[Reliability] = None
    execution_percentile: Optional[int] = Field(None, ge=1, le=99)
    preventive_timing: Optional[Literal["best_month", "asap"]] = None
    inspections: Optional[Inspections] = None
    corrective: Optional[Corrective] = None
    vessels: Optional[Vessels] = None
    working_pattern: Optional[Literal["single_shift", "double_shift"]] = None
    economics: Optional[Economics] = None

    @field_validator("working_pattern", mode="before")
    @classmethod
    def baseline_means_no_override(cls, value):
        # "baseline" = keep the form's own shift settings, same as omitting it.
        return None if value == "baseline" else value


class RunAccepted(BaseModel):
    job_id: str
    status: str


class JobStatus(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "failed", "deleted"]
    detail: Optional[str] = None
    run_dir: Optional[str] = None
