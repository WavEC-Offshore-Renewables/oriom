import logging
import os
import pandas as pd

from oriom.common.constants import LIST_MONTHS_STR


class InspectionSiteStat():
    '''InspectionSiteStat class.

    Attributes:
        id (:obj:`str`): ID of the inspection at site.
        vessel1 (:class:`~oriom.classes.Vessel.Vessel`): Main vessel
            used in this operation.
        insp_class (:class:`~oriom.classes.Operations.InspectionSite`):
            Inspection at site.
        dur_total_dict (:obj:`dict`): Statistical time of "dur_total".
            Defaults to ``None``.
        wait_start_dict (:obj:`dict`): Dict statistical analysis of "wait_start".
            Defaults to ``None``.
        transit_to_site_dict (:obj:`dict`): Dict statistical analysis of "transit_ts".
            Defaults to ``None``.
        transit_to_site_group_dict (:obj:`dict`): Dict statistical analysis of "transit_ts".
            Defaults to ``None``.
        transit_to_site_solo_dict (:obj:`dict`): Dict statistical analysis of "transit_ts".
            Defaults to ``None``.
        dur_net_site_dict (:obj:`dict`): Dict statistical analysis of "dur_net_site".
            Defaults to ``None``.
        dur_net_site_group_dict (:obj:`dict`): Dict statistical analysis of "dur_net_site".
            Defaults to ``None``.
        dur_net_site_solo_dict (:obj:`dict`): Dict statistical analysis of "dur_net_site".
            Defaults to ``None``.
        transit_to_port_dict (:obj:`dict`): Dict statistical analysis of "transit_tp".
            Defaults to ``None``.
        transit_to_port_group_dict (:obj:`dict`): Dict statistical analysis of "transit_tp".
            Defaults to ``None``.
        transit_to_port_solo_dict (:obj:`dict`): Dict statistical analysis of "transit_tp".
            Defaults to ``None``.
        wait_port_dict (:obj:`dict`): Dict statistical analysis of "wait_port".
            Defaults to ``None``.
        wait_port_group_dict (:obj:`dict`): Dict statistical analysis of "wait_port".
            Defaults to ``None``.
        wait_port_solo_dict (:obj:`dict`): Dict statistical analysis of "wait_port".
            Defaults to ``None``.
        wtg_shutdown_dict (:obj:`dict`): Statistical time of "dur_shutdown_wtg".
            Defaults to ``None``.
        wec_shutdown_dict (:obj:`dict`): Statistical time of "dur_shutdown_wec".
            Defaults to ``None``.
        pv_shutdown_dict (:obj:`dict`): Statistical time of "dur_shutdown_pv".
            Defaults to ``None``.
        n_vessel_1 (:obj:`int`): Number of main vessel.
            Defaults to ``0``.
        n_vessel_2 (:obj:`int`): Number of auxiliary vessel.
            Defaults to ``0``.
    '''
    def __init__(
            self,
            inspection,
            PERCENTILE: int,
            run_dir: str
    ):
        '''
        Args:
            inspection (:class:`~oriom.classes.Operations.InspectionSite`):
                Inspection at site with its attributes.
            PERCENTILE (:obj:`int`): Percentile for the statistical analysis.
            run_dur (:obj:`str`): Folder in which there is the statistical analysis.
        '''
        self.id = str(inspection.id).lower()
        self.vessel1 = inspection.vessel1
        self.insp_class = inspection
        self.dur_total_dict = None
        self.wait_start_dict = None
        self.dur_net_site_dict = None
        self.dur_net_site_group_dict = None
        self.dur_net_site_solo_dict = None
        self.transit_to_site_dict = None
        self.transit_to_site_group_dict = None
        self.transit_to_site_solo_dict = None
        self.transit_to_port_dict = None
        self.transit_to_port_group_dict = None
        self.transit_to_port_solo_dict = None
        self.wait_port_dict = None
        self.wait_port_group_dict = None
        self.wait_port_solo_dict = None
        self.wtg_shutdown_dict = None
        self.wec_shutdown_dict = None
        self.pv_shutdown_dict = None
        self.n_vessel_1 = inspection.n_vessel_main
        self.n_vessel_2 = None

        dict_statistics = self.get_statistics(
            inspection,
            run_dir,
            PERCENTILE
        )

        if dict_statistics['dur_total_dict'] is not None:
            self.dur_total_dict = dict_statistics['dur_total_dict']
        if dict_statistics['wait_start_dict'] is not None:
            self.wait_start_dict = dict_statistics['wait_start_dict']
        if dict_statistics['dur_net_site_dict'] is not None:
            self.dur_net_site_dict = dict_statistics['dur_net_site_dict']
        if dict_statistics['dur_net_site_group_dict'] is not None:
            self.dur_net_site_group_dict = dict_statistics['dur_net_site_group_dict']
        if dict_statistics['dur_net_site_solo_dict'] is not None:
            self.dur_net_site_solo_dict = dict_statistics['dur_net_site_solo_dict']
        if dict_statistics['transit_to_site_dict'] is not None:
            self.transit_to_site_dict = dict_statistics['transit_to_site_dict']
        if dict_statistics['transit_to_site_group_dict'] is not None:
            self.transit_to_site_group_dict = dict_statistics['transit_to_site_group_dict']
        if dict_statistics['transit_to_site_solo_dict'] is not None:
            self.transit_to_site_solo_dict = dict_statistics['transit_to_site_solo_dict']
        if dict_statistics['transit_to_port_dict'] is not None:
            self.transit_to_port_dict = dict_statistics['transit_to_port_dict']
        if dict_statistics['transit_to_port_group_dict'] is not None:
            self.transit_to_port_group_dict = dict_statistics['transit_to_port_group_dict']
        if dict_statistics['transit_to_port_solo_dict'] is not None:
            self.transit_to_port_solo_dict = dict_statistics['transit_to_port_solo_dict']
        if dict_statistics['wait_port_dict'] is not None:
            self.wait_port_dict = dict_statistics['wait_port_dict']
        if dict_statistics['wait_port_group_dict'] is not None:
            self.wait_port_group_dict = dict_statistics['wait_port_group_dict']
        if dict_statistics['wait_port_solo_dict'] is not None:
            self.wait_port_solo_dict = dict_statistics['wait_port_solo_dict']
        if dict_statistics['wtg_shutdown_dict'] is not None:
            self.wtg_shutdown_dict = dict_statistics['wtg_shutdown_dict']
        if dict_statistics['wec_shutdown_dict'] is not None:
            self.wec_shutdown_dict = dict_statistics['wec_shutdown_dict']
        if dict_statistics['pv_shutdown_dict'] is not None:
            self.pv_shutdown_dict = dict_statistics['pv_shutdown_dict']

        if inspection.vessel2_id is not None:
            self.n_vessel_2 = 1

    def get_statistics(
        self,
        inspection,
        run_dir: str,
        PERCENTILE: int
    ):
        '''
        Args:
            inspection (:class:`~oriom.classes.Operations.InspectionSite`):
                Inspection at site.
            run_dur (:obj:`str`): Folder in which there is the statistical analysis.
            PERCENTILE (:obj:`int`): Percentile for the statistical analysis.
        '''
        op_path = os.path.join(run_dir, inspection.id, 'statistical_analysis_P' + str(PERCENTILE) + '.csv')
        df_stats = pd.read_csv(op_path)
        list_months = [str(c) for c in range(1,13)]
        dur_total_row = df_stats[
            df_stats['percentile'] == 'dur_total_p'
        ]
        dur_total_dict = dur_total_row[LIST_MONTHS_STR].to_dict(orient='records')[0]
        wait_start_row = df_stats[
            df_stats['percentile'] == 'wait_start'
        ]
        wait_start_dict= wait_start_row[LIST_MONTHS_STR].to_dict(orient='records')[0]
        if 'dur_net_site' in df_stats['percentile'].tolist():
            dur_net_site_row = df_stats[
                df_stats['percentile'] == 'dur_net_site'
            ]
            dur_net_site_dict=dur_net_site_row[LIST_MONTHS_STR].to_dict(orient='records')[0]
            dur_net_site_group_dict = None
            dur_net_site_solo_dict = None
        else:
            dur_net_site_group_row = df_stats[
                df_stats['percentile'] == 'dur_net_site_group'
            ]
            dur_net_site_group_dict=dur_net_site_group_row[LIST_MONTHS_STR].to_dict(orient='records')[0]
            dur_net_site_solo_row = df_stats[
                df_stats['percentile'] == 'dur_net_site_solo'
            ]
            dur_net_site_solo_dict=dur_net_site_solo_row[LIST_MONTHS_STR].to_dict(orient='records')[0]
            dur_net_site_dict = None
        if 'transit_to_site' in df_stats['percentile'].tolist():
            transit_to_site_row = df_stats[
                df_stats['percentile'] == 'transit_to_site'
            ]
            transit_to_site_dict=transit_to_site_row[LIST_MONTHS_STR].to_dict(orient='records')[0]
            transit_to_site_group_dict=None
            transit_to_site_solo_dict=None
        else:
            transit_to_site_group_row = df_stats[
                df_stats['percentile'] == 'transit_to_site_group'
            ]
            transit_to_site_group_dict=transit_to_site_group_row[LIST_MONTHS_STR].to_dict(orient='records')[0]
            transit_to_site_solo_row = df_stats[
                df_stats['percentile'] == 'transit_to_site_solo'
            ]
            transit_to_site_solo_dict=transit_to_site_solo_row[LIST_MONTHS_STR].to_dict(orient='records')[0]
            transit_to_site_dict = None
        if 'transit_to_port' in df_stats['percentile'].tolist():
            transit_to_port_row = df_stats[
                df_stats['percentile'] == 'transit_to_port'
            ]
            transit_to_port_dict=transit_to_port_row[LIST_MONTHS_STR].to_dict(orient='records')[0]
            transit_to_port_group_dict=None
            transit_to_port_solo_dict=None
        else:
            transit_to_port_group_row = df_stats[
                df_stats['percentile'] == 'transit_to_port_group'
            ]
            transit_to_port_group_dict=transit_to_port_group_row[LIST_MONTHS_STR].to_dict(orient='records')[0]
            transit_to_port_solo_row = df_stats[
                df_stats['percentile'] == 'transit_to_port_solo'
            ]
            transit_to_port_solo_dict=transit_to_port_solo_row[LIST_MONTHS_STR].to_dict(orient='records')[0]
            transit_to_port_dict=None
        if 'wait_port' in df_stats['percentile'].tolist():
            wait_port_row = df_stats[
                df_stats['percentile'] == 'wait_port'
            ]
            wait_port_dict=wait_port_row[LIST_MONTHS_STR].to_dict(orient='records')[0]
            wait_port_group_dict=None
            wait_port_solo_dict=None
        else:
            wait_port_group_row = df_stats[
                df_stats['percentile'] == 'wait_port_group'
            ]
            wait_port_group_dict=wait_port_group_row[LIST_MONTHS_STR].to_dict(orient='records')[0]
            wait_port_solo_row = df_stats[
                df_stats['percentile'] == 'wait_port_solo'
            ]
            wait_port_solo_dict=wait_port_solo_row[LIST_MONTHS_STR].to_dict(orient='records')[0]
            wait_port_dict = None
        wtg_shutdown_row = df_stats[
            df_stats['percentile'] == 'dur_shutdown_wtg'
        ]
        wtg_shutdown_dict=wtg_shutdown_row[LIST_MONTHS_STR].to_dict(orient='records')[0]
        wec_shutdown_row = df_stats[
            df_stats['percentile'] == 'dur_shutdown_wec'
        ]
        wec_shutdown_dict=wec_shutdown_row[LIST_MONTHS_STR].to_dict(orient='records')[0]
        pv_shutdown_row = df_stats[
            df_stats['percentile'] == 'dur_shutdown_pv'
        ]
        pv_shutdown_dict=pv_shutdown_row[LIST_MONTHS_STR].to_dict(orient='records')[0]

        dict_statistics = {
            'dur_total_dict' : dur_total_dict,
            'wait_start_dict':wait_start_dict,
            'dur_net_site_dict':dur_net_site_dict,
            'dur_net_site_group_dict':dur_net_site_group_dict,
            'dur_net_site_solo_dict':dur_net_site_solo_dict,
            'transit_to_site_dict':transit_to_site_dict,
            'transit_to_site_group_dict':transit_to_site_group_dict,
            'transit_to_site_solo_dict':transit_to_site_solo_dict,
            'transit_to_port_dict':transit_to_port_dict,
            'transit_to_port_group_dict':transit_to_port_group_dict,
            'transit_to_port_solo_dict':transit_to_port_solo_dict,
            'wait_port_dict':wait_port_dict,
            'wait_port_group_dict':wait_port_group_dict,
            'wait_port_solo_dict':wait_port_solo_dict,
            'wtg_shutdown_dict':wtg_shutdown_dict,
            'wec_shutdown_dict':wec_shutdown_dict,
            'pv_shutdown_dict':pv_shutdown_dict
        }

        return dict_statistics


    def get_inspection_statistics(
        insepctions_site: list,
        PERCENTILE: int,
        run_dir: int,
    ):
        '''
        Args:
            inspection (:obj:`list`):
                List of :class:`~oriom.classes.Operations.InspectionSite`.
            PERCENTILE (:obj:`int`): Percentile for the statistical analysis.
            run_dur (:obj:`str`): Folder in which there is the statistical analysis.

        '''
        inspections_stat = []
        for insp in insepctions_site:
            inspections_stat.append(
                InspectionSiteStat(
                inspection=insp,
                PERCENTILE=PERCENTILE,
                run_dir=run_dir
                )
            )
        logging.info('InspectionSiteStat: operations defined based on file class "InspectionSite"')
        return inspections_stat