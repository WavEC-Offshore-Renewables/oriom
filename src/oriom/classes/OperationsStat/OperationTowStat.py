import pandas as pd
import logging
import os

class OperationsTowStat():
    '''OperationsTowStat class.

    Attributes:
        id (:obj:`str`): ID of the towing operation.
        op_class (:class:`~oriom.classes.Operations.OperationTow`):
           Towing operation class.
        vessel1 (:class:`~oriom.classes.Vessel.Vessel`): Main vessel
            used in this operation. Its value is ``None`` if not defided.
        vessel2 (:class:`~oriom.classes.Vessel.Vessel`): Auxiliary vessel
            used in this operation. Its value is ``None`` if not defided.
        dur_total_dict (:obj:`dict`): Dict statistical analysis of "dur_total".
            Defaults to ``None``.
        wait_start_dict (:obj:`dict`): Dict statistical analysis of "wait_start".
            Defaults to ``None``.
        dur_net_port_dict (:obj:`dict`): Dict statistical analysis of "dur_net_port".
            Defaults to ``None``.
        transit_to_site_dict (:obj:`dict`): Dict statistical analysis of "transit_ts".
            Defaults to ``None``.
        wait_site_dict (:obj:`dict`): Dict statistical analysis of "wait_site".
            Defaults to ``None``.
        dur_net_site_dict (:obj:`dict`): Dict statistical analysis of "dur_net_site".
            Defaults to ``None``.
        transit_to_port_dict (:obj:`dict`): Dict statistical analysis of "transit_tp".
            Defaults to ``None``.
        wait_port_dict (:obj:`dict`): Dict statistical analysis of "wait_port".
            Defaults to ``None``.
        wtg_shutdown_dict (:obj:`dict`): Dict statistical analysis of "wtg_shutdown".
            Defaults to ``None``.
        wec_shutdown_dict (:obj:`dict`): Dict statistical analysis of "wec_shutdown".
            Defaults to ``None``.
        pv_shutdown_dict (:obj:`dict`): Dict statistical analysis of "pv_shutdown".
            Defaults to ``None``.

    '''

    def __init__(
        self,
        operation,
        PERCENTILE: int,
        run_dir: str
    ):
        '''
        Args:
            operation (:class:`~oriom.classes.Operations.OperationTow`):
                Towing operation class.
            PERCENTILE (:obj:`int`): Percentile for the statistical analysis.
            run_dur (:obj:`str`): Folder in which there is the statistical analysis.

        '''
        self.id = str(operation.id).lower()
        self.op_class = operation
        self.vessel1 = operation.vessel1
        self.vessel2 = operation.vessel2
        self.dur_total_dict = None
        self.wait_start_dict = None
        self.dur_net_port_dict = None
        self.transit_to_site_dict = None
        self.wait_site_dict = None
        self.dur_net_site_dict = None
        self.transit_to_port_dict = None
        self.wait_port_dict = None
        self.wtg_shutdown_dict = None
        self.wec_shutdown_dict = None
        self.pv_shutdown_dict = None

        dict_statistics = self.get_operation_statistics(
            run_dir,
            PERCENTILE
        )

        if dict_statistics['dur_total_dict'] is not None:
            self.dur_total_dict = dict_statistics['dur_total_dict']
        if dict_statistics['wait_start_dict'] is not None:
            self.wait_start_dict = dict_statistics['wait_start_dict']
        if dict_statistics['transit_to_site_dict'] is not None:
            self.transit_to_site_dict = dict_statistics['transit_to_site_dict']
        if dict_statistics['wait_site_dict'] is not None:
            self.wait_site_dict = dict_statistics['wait_site_dict']
        if dict_statistics['dur_net_site_dict'] is not None:
            self.dur_net_site_dict = dict_statistics['dur_net_site_dict']
        if dict_statistics['dur_net_port_dict'] is not None:
            self.dur_net_port_dict = dict_statistics['dur_net_port_dict']
        if dict_statistics['transit_to_port_dict'] is not None:
            self.transit_to_port_dict = dict_statistics['transit_to_port_dict']
        if dict_statistics['wait_port_dict'] is not None:
            self.wait_port_dict = dict_statistics['wait_port_dict']
        if dict_statistics['wtg_shutdown_dict'] is not None:
            self.wtg_shutdown_dict = dict_statistics['wtg_shutdown_dict']
        if dict_statistics['wec_shutdown_dict'] is not None:
            self.wec_shutdown_dict = dict_statistics['wec_shutdown_dict']
        if dict_statistics['pv_shutdown_dict'] is not None:
            self.pv_shutdown_dict = dict_statistics['pv_shutdown_dict']


        self._check_attributes()

    def _check_attributes(self):

        if self.vessel1 is None:
            raise ValueError('"Vessel not found": vessel must be defined from operation')
        logging.debug('OperationTowStat: operation %s attributes valid.' % self.id)

    def get_operation_statistics(
            self,
            run_dir: str,
            PERCENTILE: int
    ):
        '''
        Args:
            run_dur (:obj:`str`): Folder in which there is the statistical analysis.
            PERCENTILE (:obj:`int`): Percentile for the statistical analysis.
        '''

        op_path = os.path.join(run_dir, self.id, 'statistical_analysis_P' + str(PERCENTILE) + '.csv')
        df_stats = pd.read_csv(op_path)
        list_months = [str(c) for c in range(1,13)]
        dur_total_row = df_stats[
            df_stats['percentile'] == 'dur_total_p'
        ]
        dur_total_dict = dur_total_row[list_months].to_dict(orient='records')[0]
        wait_start_row = df_stats[
            df_stats['percentile'] == 'wait_start'
        ]
        wait_start_dict= wait_start_row[list_months].to_dict(orient='records')[0]
        dur_net_port_row = df_stats[
            df_stats['percentile'] == 'dur_net_port'
        ]
        dur_net_port_dict=dur_net_port_row[list_months].to_dict(orient='records')[0]
        transit_to_site_row = df_stats[
            df_stats['percentile'] == 'transit_to_site'
        ]
        transit_to_site_dict=transit_to_site_row[list_months].to_dict(orient='records')[0]
        wait_site_row = df_stats[
            df_stats['percentile'] == 'wait_site'
        ]
        wait_site_dict=wait_site_row[list_months].to_dict(orient='records')[0]
        dur_net_site_row = df_stats[
            df_stats['percentile'] == 'dur_net_site'
        ]
        dur_net_site_dict=dur_net_site_row[list_months].to_dict(orient='records')[0]
        transit_to_port_row = df_stats[
            df_stats['percentile'] == 'transit_to_port'
        ]
        transit_to_port_dict=transit_to_port_row[list_months].to_dict(orient='records')[0]
        wait_port_row = df_stats[
            df_stats['percentile'] == 'wait_port'
        ]
        wait_port_dict=wait_port_row[list_months].to_dict(orient='records')[0]
        wtg_shutdown_row = df_stats[
            df_stats['percentile'] == 'dur_shutdown_wtg'
        ]
        wtg_shutdown_dict = wtg_shutdown_row[list_months].to_dict(orient='records')[0]
        wec_shutdown_row = df_stats[
            df_stats['percentile'] == 'dur_shutdown_wec'
        ]
        wec_shutdown_dict =wec_shutdown_row[list_months].to_dict(orient='records')[0]
        pv_shutdown_row = df_stats[
            df_stats['percentile'] == 'dur_shutdown_pv'
        ]
        pv_shutdown_dict = pv_shutdown_row[list_months].to_dict(orient='records')[0]

        dict_statistics = {
            'dur_total_dict':dur_total_dict,
            'wait_start_dict':wait_start_dict,
            'dur_net_port_dict':dur_net_port_dict,
            'transit_to_site_dict':transit_to_site_dict,
            'wait_site_dict':wait_site_dict,
            'dur_net_site_dict':dur_net_site_dict,
            'transit_to_port_dict':transit_to_port_dict,
            'wait_port_dict':wait_port_dict,
            'wtg_shutdown_dict':wtg_shutdown_dict,
            'wec_shutdown_dict':wec_shutdown_dict,
            'pv_shutdown_dict':pv_shutdown_dict
        }
        return dict_statistics

    def get_towing_statistics(
        operations: list,
        PERCENTILE: int,
        run_dir: int
    ):
        '''
        Args:
            operations (:obj:`list`):
                list of :class:`~oriom.classes.Operations.OperationTow`.
            PERCENTILE (:obj:`int`): Percentile for the statistical analysis.
            run_dur (:obj:`str`): Folder in which there is the statistical analysis.
        '''
        operations_tow_stat = []
        for op in operations:
            operations_tow_stat.append(
                OperationsTowStat(
                    operation=op,
                    PERCENTILE=PERCENTILE,
                    run_dir=run_dir
                )
            )
        logging.info('OperationsTowStat: operations defined based on file class "OperationsTow"')
        return operations_tow_stat