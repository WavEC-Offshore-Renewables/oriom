# technology_builder
from oriom.classes.Techs.WindTurbineGenerator import WindTurbineGenerator
from oriom.classes.Techs.WaveEnergyConverter import  WaveEnergyConverter
from oriom.classes.Techs.PVProduction import PVProduction
from oriom.classes.Techs import Power

from oriom.utils.aux_functions import save_file_csv

try:
    from oriom.core.functions.private.check_files import check_file_exists
except ImportError:
    check_file_exists = None


class PowerTechResult:

    """Bundle for power tech objects and metadata."""

    def __init__(
        self,
        power_losses,
        wtg_number_devices = None, wtg_pcurve = None,
        wec_number_devices = None, wec_pmatrix = None,
        pv_number_devices = None, pv_farm_prod = None,
        degradation_rate = None, pv_max_failure_module = None,
    ):
        self.power_losses = power_losses
        self.wtg_number_devices = wtg_number_devices
        self.wtg_pcurve = wtg_pcurve
        self.wec_number_devices = wec_number_devices
        self.wec_pmatrix = wec_pmatrix
        self.pv_number_devices = pv_number_devices
        self.pv_farm_prod = pv_farm_prod
        self.degradation_rate = degradation_rate
        self.pv_max_failure_module = pv_max_failure_module

    def is_any_defined(self):

        """Return True if at least one tech is defined."""

        return any([
            self.wtg_number_devices,
            self.wec_number_devices,
            self.pv_number_devices
        ])


class TechFarm:

    """Bundle for technology domain objects (WTG, WEC, PV) and derived power tech."""

    def __init__(self, wtg = None, wec = None, pv = None, power = None):

        self.wtg = wtg
        self.wec = wec
        self.pv = pv
        self.power = power

class TechnologyBuilder:

    """Create or reuse technologies and build derived power-tech artifacts."""

    @staticmethod
    def _load_or_build_wtg(run_dir, wtg_file):

        """Return WTG instance (reuse if exists, else build from YAML)."""
        if check_file_exists and check_file_exists(run_dir, file_name = "wtg.yaml"):
            return WindTurbineGenerator.from_yaml(directory = run_dir, name = "wtg")
        return WindTurbineGenerator.get_wtg_from_yaml(file_path = wtg_file, out_dir = run_dir)


    @staticmethod
    def _load_or_build_wec(run_dir, wec_file):

        """Return WEC instance (reuse if exists, else build from YAML)."""
        if check_file_exists and check_file_exists(run_dir, file_name = "wec.yaml"):
            return WaveEnergyConverter.from_yaml(directory = run_dir, name = "wec")
        return WaveEnergyConverter.get_wec_from_yaml(file_path = wec_file, out_dir = run_dir)


    @staticmethod
    def _load_or_build_pv(run_dir, pv_file):

        """Return PV instance (reuse if exists, else build from YAML)."""
        if check_file_exists and check_file_exists(run_dir, file_name = "pv.yaml"):
            return PVProduction.from_yaml(directory = run_dir, name = "pv")
        return PVProduction.get_pv_from_yaml(file_path = pv_file, out_dir = run_dir)


    @classmethod
    def create_technologies(cls, run_dir, wtg_file, wec_file, pv_file):
        """
        Create or reuse domain objects (WTG/WEC/PV) from YAMLs under run_dir.
        Return (wtg, wec, pv).
        """
        wtg = cls._load_or_build_wtg(run_dir, wtg_file)
        wec = cls._load_or_build_wec(run_dir, wec_file)
        pv = cls._load_or_build_pv(run_dir, pv_file)

        if not any([
            hasattr(wtg, "number_devices"),
            hasattr(wec, "number_devices"),
            hasattr(pv, "number_devices"),
        ]):
            raise ValueError("At least one technology has to be defined")

        return wtg, wec, pv


    @staticmethod
    def build_power_technologies(wtg, wec, pv, run_dir: str, file_electrical_loss: str, file_wake_loss: str):

        """
        Build derived power-tech artifacts from domain objects.
        - out_dir: where to save PV CSV (optional)
        - save_pv_csv: toggle CSV saving
        """

        # --- Power Loss ---
        power_losses = Power.Power_Losses(
            file_electric_loss = file_electrical_loss,
            file_wake_loss  = file_wake_loss,
        )

        # --- WTG ---
        if hasattr(wtg, "number_devices"):
            wtg_number_devices  =  wtg.number_devices
            wtg_pcurve = Power.Curve(
                file_ = wtg.pcurve_file,
                c_in = wtg.cut_in,
                c_off = wtg.cut_off,
                rated = wtg.rated_power,
            )
        else:
            wtg_number_devices  =  None
            wtg_pcurve  =  None


        # --- WEC ---
        if hasattr(wec, "number_devices"):
            wec_number_devices  =  wec.number_devices
            wec_pmatrix = Power.Matrix(
                file_ = wec.pmatrix_file,
                rated = wec.rated_power,
            )
        else:
            wec_number_devices  =  None
            wec_pmatrix  =  None


        # --- PV ---
        if hasattr(pv, "number_devices"):
            pv_number_devices = pv.number_devices
            pv_max_failure_module = pv.max_failure_module
            degradation_rate = pv.degradation_rate

            pv_farm_prod = PVProduction.pv_farm_statistical_analysis(
                pvprod_file = pv.pvprod_file,
                number_devices = pv_number_devices,
            )

            save_file_csv(pv_farm_prod, run_dir,'power_pv_farm.csv')

        else:
            pv_number_devices  =  None
            pv_farm_prod  =  None
            degradation_rate  =  None
            pv_max_failure_module  =  None

        return PowerTechResult(
            power_losses = power_losses,
            wtg_number_devices = wtg_number_devices,
            wtg_pcurve = wtg_pcurve,
            wec_number_devices = wec_number_devices,
            wec_pmatrix = wec_pmatrix,
            pv_number_devices = pv_number_devices,
            pv_farm_prod = pv_farm_prod,
            degradation_rate = degradation_rate,
            pv_max_failure_module = pv_max_failure_module,
        )

    def build_power_losses(file_electrical_loss, file_wake_loss):
        return 

    @classmethod
    def build_technologies(
        cls,
        run_dir: str,
        wtg_file: str,
        wec_file: str,
        pv_file: str,
        file_electrical_loss: str,
        file_wake_loss: str
    ):

        """
        Technologies builder and relative power production
        - create or reuse domain techs
        - build derived power artifacts
        - return TechBundle(wtg, wec, pv, power)

        Args:
            run_dir (string): path of the run directory
            wtg_file (string): path of the wtg techology
            wec_file (string): path of the wec techology
            pv_file (string): path of the pv techology
            file_electrical_loss (string): path of the electric losses file
            file_wake_loss (string): path of the wake losses file


        Return:
            TechFarm
        """

        wtg, wec, pv = cls.create_technologies(run_dir, wtg_file, wec_file, pv_file)
        power = cls.build_power_technologies(
            wtg = wtg,
            wec = wec,
            pv = pv,
            run_dir = run_dir,
            file_electrical_loss = file_electrical_loss,
            file_wake_loss = file_wake_loss
        )

        return TechFarm(wtg = wtg, wec = wec, pv = pv, power = power)
