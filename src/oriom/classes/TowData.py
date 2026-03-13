from dataclasses import dataclass
import pandas as pd

from oriom.utils.aux_functions import safe_getattr


@dataclass
class TowData:
    """
    Container for tow operation data and related statistics.

    This class aggregates tow operations at port and site together with
    their additional tow operations, statistics and scheduling data.

    Attributes:
        tow_op_port: Tow operation executed at port.
        tow_op_site: Tow operation executed at site.
        tow_site_port: Tow operation executed at port and remove to site.
        add_op_tow_port: Optional additional tow operation at port.
        add_op_tow_site: Optional additional tow operation at site.
        tow_op_port_stat: Statistics for the port tow operation.
        tow_op_site_stat: Statistics for the site tow operation.
        tow_site_port_stat: Statistics for the site tow operation.
        tow_port_oper_sched: Operational schedule for the port tow operation.
        tow_site_oper_sched: Operational schedule for the site tow operation.
        tow_site_port_oper_sched: Operational schedule for the site-port tow operation.
        last_valid_idx_tow_port: Last valid index in the time series for the port tow operation.
        last_valid_idx_tow_site: Last valid index in the time series for the site tow operation.
        oper_stat_op_tow_port: Statistics for the additional port tow operation (if present).
        oper_stat_op_site: Statistics for the additional site tow operation (if present).
        op_at_port: Operation executed at port.
    """

    tow_op_port: object
    tow_op_site: object
    tow_site_port: object
    add_op_tow_port: object
    add_op_tow_site: object
    tow_op_port_stat: object
    tow_op_site_stat: object
    tow_op_site_port_stat: object
    tow_port_oper_sched: pd.DataFrame
    tow_site_oper_sched: pd.DataFrame
    tow_site_port_oper_sched: pd.DataFrame
    last_valid_idx_tow_port: int
    last_valid_idx_tow_site: int
    last_valid_idx_tow_site_port: int
    oper_stat_op_tow_port: object | None = None
    oper_stat_op_site: object | None = None
    op_at_port: object = None

    def id_dict_oper(self, oper_dict_tow: dict, op_at_port: object):
        """Populate a dictionary with obj.id: obj """
        self.op_at_port = op_at_port
        ops = (
            self.op_at_port,
            self.tow_op_port,
            self.tow_op_site,
            self.add_op_tow_port,
            self.add_op_tow_site
        )

        for op in filter(None, ops):
            oper_dict_tow[op.id] = op


    @classmethod
    def from_operation(cls, finder, oper):
        """
        Build a TowData instance from an operation object.

        Args:
            finder: Object responsible for retrieving operations and statistics.
            oper: Operation object containing references to tow operations.

        Returns:
            TowData: Aggregated tow operation data.
        """

        tow_op_port = finder.find_operation(getattr(oper, 'op_tow_port'))
        tow_op_site = finder.find_operation(getattr(oper, 'op_tow_site'))
        tow_site_port = finder.find_operation(getattr(oper, 'op_tow_site_port'))

        add_op_tow_port = getattr(tow_op_port, 'addition_op_tow', None)
        add_op_tow_site = getattr(tow_op_site, 'addition_op_tow', None)

        tow_op_port_stat = finder.find_operation_stats_pmax(tow_op_port.id)
        tow_op_site_stat = finder.find_operation_stats_pmax(tow_op_site.id)
        tow_op_site_port_stat = finder.find_operation_stats_pmax(tow_op_site.id)

        tow_port_oper_sched = safe_getattr(tow_op_port, ['ts_data', 'oper_sched'])
        tow_site_oper_sched = safe_getattr(tow_op_site, ['ts_data', 'oper_sched'])
        tow_site_port_oper_sched = safe_getattr(tow_site_port, ['ts_data', 'oper_sched'])

        last_valid_idx_tow_port = safe_getattr(tow_op_port, ['ts_data', 'last_valid_index'])
        last_valid_idx_tow_site = safe_getattr(tow_op_site, ['ts_data', 'last_valid_index'])
        last_valid_idx_tow_site_port = safe_getattr(tow_site_port, ['ts_data', 'last_valid_index'])

        oper_stat_op_tow_port = (
            finder.find_operation_stats_pmax(add_op_tow_port.id)
            if add_op_tow_port else None
        )

        oper_stat_op_site = (
            finder.find_operation_stats_pmax(add_op_tow_site.id)
            if add_op_tow_site else None
        )

        return cls(
            tow_op_port,
            tow_op_site,
            tow_site_port,
            add_op_tow_port,
            add_op_tow_site,
            tow_op_port_stat,
            tow_op_site_stat,
            tow_op_site_port_stat,
            tow_port_oper_sched,
            tow_site_oper_sched,
            tow_site_port_oper_sched,
            last_valid_idx_tow_port,
            last_valid_idx_tow_site,
            last_valid_idx_tow_site_port,
            oper_stat_op_tow_port,
            oper_stat_op_site
        )