import pandas as pd
import logging
import os

class CorrectiveStat():
    '''CorrectiveStat class.

        For each corrective operations all statistical results are included in this class.

        Attributes:
            id (:obj:`str`): ID of the corrective operation.
            op_class (:class:`~oriom.classes.Operations.CorrectiveMinor/Major`):
                Corrective minor or major operation class.
            vessel1 (:class:`~oriom.classes.Vessel.Vessel`): Main vessel
                used in this operation.
            vessel2 (:class:`~oriom.classes.Vessel.Vessel`): Auxiliary vessel
                used in this operation.
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
            tow_to_site_dict (:obj:`dict`): Dict statistical of the op_to_to_site.
                Defaults to ``None``.
            tow_to_site_id (:obj:`str`): Name of operations tow_to_site.
                Defaults to ``None``.
            tow_to_port_dict (:obj:`dict`): Dict statistical of the op_tow_to_port.
                Defaults to ``None``.
            tow_to_port_id (:obj:`str`): Name of operations tow_to_port.
                Defaults to ``None``.

    '''
    def __init__(
            self,
            operation,
            PERCENTILE: int,
            run_dir: str,
            operations_tow_stat: list
    ):
        '''
        Args:
            operation (:class:`~oriom.classes.Operations.CorrectiveMinor/Major`): 
                Corrective operation class.
            PERCENTILE (:obj:`int`): Percentile for the statistical analysis.
            run_dur (:obj:`str`): Folder in which there is the statistical analysis.
            operations_tow_stat (:obj:`list`): List of operations tow statistics.
        '''
        self.id = str(operation.id).lower()
        self.op_class = operation
        self.vessel1 = None
        self.vessel2 = None
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
        self.tow_to_site_dict = None
        self.tow_to_port_dict = None
        self.tow_to_site_id = None
        self.tow_to_port_id = None

        dict_statistics = self.get_operation_statistics(
            operation,
            run_dir,
            PERCENTILE,
            operations_tow_stat
        )

        if dict_statistics['vessel'] is not None:
            self.vessel1 = dict_statistics['vessel']
            if self.op_class.vessel1_id is None:
                self.op_class.vessel1 = dict_statistics['vessel']
                self.op_class.vessel1_id = dict_statistics['vessel_id']
                self.op_class.vessel1_qt = dict_statistics['vessel_qt']
        if dict_statistics['vessel_2'] is not None:
            self.vessel2 = dict_statistics['vessel_2']
            if self.op_class.vessel2_id is None:
                self.op_class.vessel2 = dict_statistics['vessel_2']
                self.op_class.vessel2_id = dict_statistics['vessel_2id']
        if dict_statistics['dur_total_dict'] is not None:
            self.dur_total_dict = dict_statistics['dur_total_dict']
        if dict_statistics['wait_start_dict'] is not None:
            self.wait_start_dict = dict_statistics['wait_start_dict']
        if dict_statistics['dur_net_port_dict'] is not None:
            self.dur_net_port_dict = dict_statistics['dur_net_port_dict']
        if dict_statistics['transit_to_site_dict'] is not None:
            self.transit_to_site_dict = dict_statistics['transit_to_site_dict']
        if dict_statistics['wait_site_dict'] is not None:
            self.wait_site_dict = dict_statistics['wait_site_dict']
        if dict_statistics['dur_net_site_dict'] is not None:
            self.dur_net_site_dict = dict_statistics['dur_net_site_dict']
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
        if dict_statistics['tow_to_port_dict'] is not None:
            self.tow_to_port_dict = dict_statistics['tow_to_port_dict']
        if dict_statistics['tow_to_site_dict'] is not None:
            self.tow_to_site_dict = dict_statistics['tow_to_site_dict']
        if dict_statistics['tow_to_site_id'] is not None:
            self.tow_to_site_id = dict_statistics['tow_to_site_id']
        if dict_statistics['tow_to_port_id'] is not None:
            self.tow_to_port_id = dict_statistics['tow_to_port_id']


        self._check_attributes()

    def _check_attributes(self):

        if self.tow_to_site_dict is not None and self.tow_to_port_dict is None:
            raise ValueError('if "tow_to_site" defined, "tow_to_port" is to be defined')
        if self.tow_to_port_dict is not None and self.tow_to_site_dict is None:
            raise ValueError('if "tow_to_port" is defined, "tow_to_site" is to be defined')
        if self.vessel1 is None:
            raise ValueError('"Vessel not found": vessel must be defined from operation or from tow operation')
        logging.debug('CorrectiveStat: operation %s attributes valid.' % self.id)

    def get_operation_statistics(
            self,
            operation,
            run_dir: str,
            PERCENTILE: int,
            operations_tow_stat: list,
    ):
        '''
        Args:
            operation (:class:`~oriom.classes.Operations.CorrectiveMinor/Major`):
                Corrective minor or major operation class.
            run_dir (:obj:`str`): Folder in which there is the statistical analysis.
            PERCENTILE (:obj:`int`): Percentile for the statistical analysis.
            operations_tow_stat (:obj:`list`):
                List of :class:`~oriom.classes.OperationTowStat.OperationTowStat`.
        '''

        op_path = os.path.join(run_dir, self.id, 'statistical_analysis_P' + str(PERCENTILE) + '.csv')
        df_stats = pd.read_csv(op_path)
        list_months = [str(c) for c in range(1,13)]
        dur_total_row = df_stats[
            df_stats['percentile'] == 'dur_total_p'
        ]
        dur_total_row = dur_total_row.fillna(0)
        dur_total_dict = dur_total_row[list_months].to_dict(orient='records')[0]
        wait_start_row = df_stats[
            df_stats['percentile'] == 'wait_start'
        ]
        wait_start_row = wait_start_row.fillna(0)
        wait_start_dict= wait_start_row[list_months].to_dict(orient='records')[0]
        if 'dur_net_port' in df_stats['percentile']:
            dur_net_port_row = df_stats[
                df_stats['percentile'] == 'dur_net_port'
            ]
            dur_net_port_row = dur_net_port_row.fillna(0)
            dur_net_port_dict=dur_net_port_row[list_months].to_dict(orient='records')[0]
        else: dur_net_port_dict = None
        transit_to_site_row = df_stats[
            df_stats['percentile'] == 'transit_to_site'
        ]

        transit_to_site_row = transit_to_site_row.fillna(0)
        transit_to_site_dict=transit_to_site_row[list_months].to_dict(orient='records')[0]
        if 'wait_site' in df_stats['percentile']:
            wait_site_row = df_stats[
                df_stats['percentile'] == 'wait_site'
            ]
            
            wait_site_row = wait_site_row.fillna(0)
            wait_site_dict=wait_site_row[list_months].to_dict(orient='records')[0]
        else: wait_site_dict = None
        dur_net_site_row = df_stats[
            df_stats['percentile'] == 'dur_net_site'
        ]

        dur_net_site_row = dur_net_site_row.fillna(0)
        dur_net_site_dict=dur_net_site_row[list_months].to_dict(orient='records')[0]
        transit_to_port_row = df_stats[
            df_stats['percentile'] == 'transit_to_port'
        ]

        transit_to_port_row = transit_to_port_row.fillna(0)
        transit_to_port_dict=transit_to_port_row[list_months].to_dict(orient='records')[0]
        wait_port_row = df_stats[
            df_stats['percentile'] == 'wait_port'
        ]

        wait_port_row = wait_port_row.fillna(0)
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

        vessel1 = operation.vessel1
        vessel1_id = operation.vessel1_id
        vessel2 = operation.vessel2
        vessel2_id = operation.vessel2_id

        if vessel1 is None:
            op_tow_port = operation.op_tow_port
            op_port_found = False
            for op_t in operations_tow_stat:
                if op_t.id == op_tow_port:
                    op_port_found = True
                    break
            if op_port_found is False:
                _e = 'Operation tow to port not found'
                logging.error('LogDates: ' + _e)
                raise NameError(_e, operation.id)
            op_tow_port = op_t

            op_tow_site = operation.op_tow_site
            op_site_found = False
            for op_t in operations_tow_stat:
                if op_t.id == op_tow_site:
                    op_site_found = True
                    break
            if op_site_found is False:
                _e = 'Operation tow not found'
                logging.error('LogDates: ' + _e)
                raise NameError(_e)
            op_tow_site = op_t

            vessel1 = op_tow_site.vessel1
            vessel1_id = op_tow_site.vessel1.id
            vessel1_qt = op_tow_site.op_class.vessel1_qt
            vessel2 = op_tow_site.vessel2
            if op_tow_site.vessel2 is not None:
                vessel2_id = op_tow_site.vessel2.id
            else: vessel2_id = None

            tow_to_site_id = op_tow_site.id
            tow_to_port_id = op_tow_port.id
            tow_to_port_dict = op_tow_port.dur_total_dict
            tow_to_site_dict = op_tow_site.dur_total_dict
        else:
            tow_to_site_id = None
            tow_to_port_id = None
            tow_to_port_dict = None
            tow_to_site_dict = None
            vessel1_qt = 1

        dict_statistics = {
            'vessel': vessel1,
            'vessel_id': vessel1_id,
            'vessel_qt': vessel1_qt,
            'vessel_2': vessel2,
            'vessel_2id': vessel2_id,
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
            'pv_shutdown_dict':pv_shutdown_dict,
            'tow_to_site_dict':tow_to_site_dict,
            'tow_to_port_dict':tow_to_port_dict,
            'tow_to_port_id':tow_to_port_id,
            'tow_to_site_id':tow_to_site_id
        }

        return dict_statistics

    def get_corrective_statistics(
        operations: list,
        operations_tow_stat: list,
        PERCENTILE: int,
        run_dir: int,
    ):
        '''
        Args:
            operations (:obj:`list`):
                List of :class:`~oriom.classes.Operations.CorrectiveMinor/Major`
            operations_tow_stat (:obj:`list`):
                list of :class:`~oriom.classes.OperationTowStat.OperationTowStat`
            PERCENTILE (:obj:`int`): Percentile for the statistical analysis.
            run_dur (:obj:`str`): Folder in which there is the statistical analysis.
        '''
        operations_stat = []
        for op in operations:
            operations_stat.append(
                CorrectiveStat(
                    operation=op,
                    PERCENTILE=PERCENTILE,
                    run_dir=run_dir,
                    operations_tow_stat=operations_tow_stat
                )
            )
        logging.info('CorrectiveStat: operations defined based on file class "CorrectiveMajor" and "CorrectiveMinor"')
        return operations_stat