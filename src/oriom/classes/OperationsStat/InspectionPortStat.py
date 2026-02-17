import logging
import os
import pandas as pd
import math
from datetime import datetime

class InspectionPortStat():
    '''InspectionPortStat class.

    At this stage the TTP campaign is planned and total durations is calculated.

    Attributes:
        id (:obj:`str`): ID of the inspection at site.
        insp_class (:class:`~oriom.classes.Operations.InspectionPort`):
                Inspection at port.
        vessel1 (:class:`~oriom.classes.Vessel.Vessel`): Main vessel
            used in this operation.
        n_vessel_1 (:obj:`int`): Number of main vessel.
        n_vessel_2 (:obj:`int`): Number of auxialiary vessel.
        dur_total_dict (:obj:`dict`): Total duration in days.
            Defaults to ``None.
        transit_time_dict (:obj:`dict`): Number of transit trips per inspection scheduled.
            Defaults to ``None``.
        standby_time_dict (:obj:`dict`): Number of towing trips per inspection scheduled.
            Defaults to ``None``.
        shutdown (:obj:`dict`): Total shutdown per inspection scheduled.
            Defaults to ``None``.
    '''

    def __init__(
        self,
        inspection,
        PERCENTILE: int,
        run_dir: str,
        n_port_inspections: int,
        operations_tow_stat,
        shift: int=None
    ):
        '''
        Args:
            inspection (:class:`~oriom.classes.Operations.InspectionPort`):
                Inspection with its attributes.
            PERCENTILE (:obj:`int`): Percentile for the statistical analysis.
            run_dir (:obj:`str`): Current working folder.
            n_port_inspection (:obj:`dict`): Number of devices to be inspected
                simultaneously at port per each device.
            operations_tow_stat (:obj:`list`): List of statistical operations tow.
            shift (:obj:`int`): Working shift in hours.
                Defaults to ``None``.
        '''

        self.id = str(inspection.id).lower()
        self.insp_class = inspection
        self.vessel1 = None
        self.n_vessel_1 = None
        self.n_vessel_2 = None
        self.dur_total_dict = None
        self.transit_time_dict = None
        self.standby_time_dict = None
        self.shutdown_dict = None

        dict_statistics = self.towing_plan(
            inspection,
            PERCENTILE,
            run_dir,
            operations_tow_stat,
            n_port_inspections[self.id[:3]],
            shift
        )

        if dict_statistics['vessel'] is not None:
            self.vessel1 = dict_statistics['vessel']
            self.insp_class.vessel1 = dict_statistics['vessel']
        if dict_statistics['vessel_1id'] is not None:
            self.insp_class.vessel1_id = dict_statistics['vessel_1id']
        if dict_statistics['vessel_2'] is not None:
            self.insp_class.vessel2 = dict_statistics['vessel_2']
        if dict_statistics['vessel_2id'] is not None:
            self.insp_class.vessel2_id = dict_statistics['vessel_2id']
        if dict_statistics['n_vessel_1'] is not None:
            self.n_vessel_1 = dict_statistics['n_vessel_1']
        if dict_statistics['n_vessel_2'] is not None:
            self.n_vessel_2 = dict_statistics['n_vessel_2']
        if dict_statistics['dur_total_dict'] is not None:
            self.dur_total_dict = dict_statistics['dur_total_dict']
            month = min(self.dur_total_dict, key=lambda x: (-self.dur_total_dict[x], x))
            self.insp_class.months = int(month)
        if dict_statistics['transit_time_dict'] is not None:
            self.transit_time_dict = dict_statistics['transit_time_dict']
        if dict_statistics['standby_time_dict'] is not None:
            self.standby_time_dict= dict_statistics['standby_time_dict']
        if dict_statistics['shutdown_dict'] is not None:
            self.shutdown_dict = dict_statistics['shutdown_dict']
        
        op_path_file_perc = os.path.join(run_dir, inspection.id, 'statistical_analysis_P' + str(PERCENTILE) + '.csv')
        shutdown_insp_port = self.shutdown_dict_insp_port(op_path = op_path_file_perc)

        if shutdown_insp_port:
            self.shutdown_dict = shutdown_insp_port

    def towing_plan(
            self,
            inspection,
            PERCENTILE: int,
            run_dir: str,
            operations_tow_stat: list,
            n_port_inspections: int,
            shift: int=None
    ):
        '''
        Args:
            inspection inspection (:class:`~oriom.classes.Operations.InspectionPort`):
                Inspection at port.
            PERCENTILE (:obj:`int`): Percentile for the statistical analysis.
            run_dir (:obj:`str`): Current working folder.
            operations_tow_stat (:obj:`list`): List of statistical operations tow.
            n_port_inspection (:obj:`int`): Number of devices to be inspected
                simultaneously at port.
            shift (:obj:`int`): Working shift in hours.
                Defaults to ``None``.
        '''
        def op_in_sequence(
            n_devices_to_inspect: int,
            n_vessels: int,
            dur_op1: float,
            dur_op2: float,
            dur_op3: float,
            duration_inspection_port: float,
            shutdown_op1: float,
            shutdown_op2: float,
            shutdown_op3: float,
            total_wait_op1: float,
            total_wait_op2: float,
            total_wait_op3: float,
            transit_time_op1: float,
            transit_time_op2: float,
            transit_time_op3: float
        ):
            '''
            Args:
                n_devices_to_inspect (:obj:`int`): Total numer of devices to inspect.
                n_vessels (:obj:`int`): Number of vessels available to perform the inspection.
                dur_op1 (:obj:`float`): Statistical value of "total_duration" for the towing op to port.
                dur_op2 (:obj:`float`): Statistical value of "total_duration" for the towing op to site.
                dur_op3 (:obj:`float`): Statistical value of "total_duration" for the towing to site,
                    transiting to another device and tow back to port.
                duration_inspection_port (:obj:`float`): Duration of one device port inspection in hours.
                shutdown_op1 (:obj:`float`): Shutdown duration for op1
                shutdown_op2 (:obj:`float`): Shutdown duration for op2
                shutdown_op3 (:obj:`float`): Shutdown duration for op3
            '''
            d=0
            transit_time=0
            standby_time=0
            dur_shutdown=0
            dict_sequence = {}
            while d < n_devices_to_inspect:
                if d==0:
                    dict_sequence.update({'op_1.1':{'duration':dur_op1, 'n_devices': n_vessels}})
                    dict_sequence.update({'insp.1':{'duration':duration_inspection_port,'n_devices':n_vessels}})
                    transit_time+=transit_time_op1 * n_vessels
                    standby_time+=total_wait_op1 * n_vessels
                    d+=n_vessels
                    actual_dev=1
                    dur_shutdown+= (shutdown_op1 +duration_inspection_port) * n_vessels
                else:
                    dict_sequence.update({f"{'op_3.'}{actual_dev}{actual_dev+1}":{'duration':dur_op3,'n_devices':n_vessels}})
                    transit_time+=transit_time_op3*n_vessels
                    standby_time+=total_wait_op3*n_vessels
                    actual_dev+=1
                    dur_shutdown += shutdown_op3*n_vessels
                    dict_sequence.update({f"{'insp.'}{actual_dev}":{'duration':duration_inspection_port,'n_devices':n_vessels}})
                    dur_shutdown += duration_inspection_port*n_vessels
                    if d >= n_devices_to_inspect or d >= n_devices_to_inspect-n_vessels:
                        dev = n_devices_to_inspect-math.floor(n_devices_to_inspect/n_vessels)*n_vessels
                        if dev == 0:
                            dev=n_vessels
                        dict_sequence.update({f"{'insp.'}{actual_dev}":{'duration':duration_inspection_port,'n_devices':dev}})
                        dict_sequence.update({f"{'op_2.'}{math.ceil(n_devices_to_inspect/n_vessels)}":{'duration':dur_op2,'n_devices':dev}})
                        transit_time+=transit_time_op2*dev
                        standby_time+=total_wait_op2*dev
                        dur_shutdown += (shutdown_op2)*dev
                        break
                    d+=n_vessels
            return dict_sequence, transit_time, standby_time, dur_shutdown

        op_tow_port = inspection.op_tow_port
        op_tow_site = inspection.op_tow_site
        op_tow_site_port = inspection.op_tow_site_port

        to_port_found = False
        for o_tow in operations_tow_stat:
            if o_tow.id == op_tow_port:
                to_port_found = True
                break
        if to_port_found is False:
            _e = 'Operation tow to port not found'
            logging.error('InspectionPortStat: ' +_e)
            raise NameError(_e)
        op_tow_port = o_tow

        to_site_found = False
        for o_tow in operations_tow_stat:
            if o_tow.id == op_tow_site:
                to_site_found = True
                break
        if to_site_found is False:
            _e = 'Operation tow to site not found'
            logging.error('InspectionPortStat: ' +_e)
            raise NameError(_e)
        op_tow_site = o_tow

        site_port_found = False
        for o_tow in operations_tow_stat:
            if o_tow.id == op_tow_site_port:
                site_port_found = True
                break
        if site_port_found is False:
            _e = 'Operation tow to site and to port not found'
            logging.error('InspectionPortStat: ' +_e)
            raise NameError(_e)
        op_tow_site_port = o_tow

        def get_stats(
                operation_tow,
                month: int
        ):
            '''
            Args:
                operation_tow  (:class:`~oriom.classes.OperationStat.OperationTowStat`):
                    Towing operation statistical.
                month (:obj:`int`): Month of the event.
            '''
            dict_dur_total = operation_tow.dur_total_dict
            wait_start = operation_tow.wait_start_dict
            wait_site = operation_tow.wait_site_dict
            wait_port = operation_tow.wait_port_dict
            dur_port = operation_tow.dur_net_port_dict
            transit_ts = operation_tow.transit_to_site_dict
            transit_tp = operation_tow.transit_to_port_dict
            shut_wtg = operation_tow.wtg_shutdown_dict
            shut_wec = operation_tow.wec_shutdown_dict
            shut_pv = operation_tow.pv_shutdown_dict

            standby_tot = wait_start[str(month)]+wait_site[str(month)]+wait_port[str(month)]+dur_port[str(month)]

            dict_durs = {
                'dur_total': dict_dur_total[str(month)],
                'standby': standby_tot,
                'transit': transit_ts[str(month)]+transit_tp[str(month)],
                'wtg_shut': shut_wtg[str(month)],
                'wec_shut': shut_wec[str(month)],
                'pv_shut': shut_pv[str(month)]
            }
            return dict_durs

        total_dur_month = {}
        transit_time_month = {}
        standby_time_month = {}
        shutdown_month = {}
        n_vessels = op_tow_port.vessel1.n_vessels
        op_path = os.path.join(run_dir, inspection.id, 'statistical_analysis_P' + str(PERCENTILE) + '.csv')
        df_stat = pd.read_csv(op_path)
        dur_total = df_stat[
            df_stat['percentile'] == 'dur_total_p'
        ]

        if isinstance(inspection.months,int):
            list_months = [inspection.months]
        else:
            list_months = inspection.months
        for m in list_months:
            dict_op1 = get_stats(op_tow_port, m)
            dict_op2 = get_stats(op_tow_site, m)
            dict_op3 = get_stats(op_tow_site_port, m)
            dur_inspection = inspection.dur_per_device

            if inspection.id[0:3] == 'ofw':
                shutdown_op1 = dict_op1['wtg_shut']
                shutdown_op2 = dict_op2['wtg_shut']
                shutdown_op3 = dict_op3['wtg_shut']
            elif inspection.id[0:3] == 'owc':
                shutdown_op1 = dict_op1['wec_shut']
                shutdown_op2 = dict_op2['wec_shut']
                shutdown_op3 = dict_op3['wec_shut']
            elif inspection.id[0:3] == 'opv':
                shutdown_op1 = dict_op1['pv_shut']
                shutdown_op2 = dict_op2['pv_shut']
                shutdown_op3 = dict_op3['pv_shut']

            if dict_op1['dur_total'] >= dur_inspection:
                if n_port_inspections==1:
                    n_vessels=1
                elif n_port_inspections < n_vessels:
                    n_vessels = n_port_inspections
                dict_sequence,transit_time,standby_time,dur_shutdown = op_in_sequence(
                    inspection.intervened_devices,
                    n_vessels,
                    dict_op1['dur_total'],
                    dict_op2['dur_total'],
                    dict_op3['dur_total'],
                    dur_inspection,
                    shutdown_op1,
                    shutdown_op2,
                    shutdown_op3,
                    dict_op1['standby'],
                    dict_op2['standby'],
                    dict_op3['standby'],
                    dict_op1['transit'],
                    dict_op2['transit'],
                    dict_op3['transit']
                    )
            else:
                if n_port_inspections==1:
                    n_vessels=1
                    dict_sequence,transit_time,standby_time,dur_shutdown = op_in_sequence(
                        inspection.intervened_devices,
                        n_vessels,
                        dict_op1['dur_total'],
                        dict_op2['dur_total'],
                        dict_op3['dur_total'],
                        dur_inspection,
                        shutdown_op1,
                        shutdown_op2,
                        shutdown_op3,
                        dict_op1['standby'],
                        dict_op2['standby'],
                        dict_op3['standby'],
                        dict_op1['transit'],
                        dict_op2['transit'],
                        dict_op3['transit']
                    )
                elif n_port_inspections > 1:
                    if n_vessels >= n_port_inspections:
                        n_vessels = n_port_inspections
                        dict_sequence,transit_time,standby_time,dur_shutdown = op_in_sequence(
                            inspection.intervened_devices,
                            n_vessels,
                            dict_op1['dur_total'],
                            dict_op2['dur_total'],
                            dict_op3['dur_total'],
                            dur_inspection,
                            shutdown_op1,
                            shutdown_op2,
                            shutdown_op3,
                            dict_op1['standby'],
                            dict_op2['standby'],
                            dict_op3['standby'],
                            dict_op1['transit'],
                            dict_op2['transit'],
                            dict_op3['transit']
                        )
                    else:
                        n_devices_to_inspect_1 = math.ceil(inspection.intervened_devices/n_port_inspections)*n_vessels
                        n_devices_to_inspect_2 = inspection.intervened_devices - n_devices_to_inspect_1*n_port_inspections
                        dict_sequence_1,transit_time_1,standby_time_1,dur_shutdown_1 = op_in_sequence(
                            n_devices_to_inspect_1,
                            n_vessels,
                            dict_op1['dur_total'],
                            dict_op2['dur_total'],
                            dict_op3['dur_total'],
                            dur_inspection,
                            shutdown_op1,
                            shutdown_op2,
                            shutdown_op3,
                            dict_op1['standby'],
                            dict_op2['standby'],
                            dict_op3['standby'],
                            dict_op1['transit'],
                            dict_op2['transit'],
                            dict_op3['transit']
                        )
                        transit_time_1*=n_port_inspections
                        standby_time_1*=n_port_inspections
                        dur_shutdown_1*=n_port_inspections
                        tot_duration_1 = 0
                        for k in dict_sequence_1.keys():
                            tot_duration_1+=dict_sequence_1[k]['duration']
                        n_vessels_2=(n_port_inspections-n_vessels)
                        if n_devices_to_inspect_2 != 0:
                            dict_sequence_2,transit_time_2,standby_time_2,dur_shutdown_2 = op_in_sequence(
                                n_devices_to_inspect_2,
                                n_vessels_2,
                                dict_op1['dur_total'],
                                dict_op2['dur_total'],
                                dict_op3['dur_total'],
                                dur_inspection,
                                shutdown_op1,
                                shutdown_op2,
                                shutdown_op3,
                                dict_op1['standby'],
                                dict_op2['standby'],
                                dict_op3['standby'],
                                dict_op1['transit'],
                                dict_op2['transit'],
                                dict_op3['transit']
                            )
                            tot_duration_2 = 0
                            for k in dict_sequence_2.keys():
                                tot_duration_2+=dict_sequence_2[k]['duration']
                            add_shutdown = dict_op3['dur_total'] - dict_op1['dur_total']
                            add_duration = abs(tot_duration_2+dict_op1['dur_total'] + add_shutdown-tot_duration_1)
                            dict_sequence_1.update({'add_shutdown':{'duration':add_duration,'n_devices':n_devices_to_inspect_2}})
                            dict_sequence=dict_sequence_1
                            transit_time = transit_time_1+transit_time_2
                            standby_time = standby_time_1+standby_time_2
                            dur_shutdown = dur_shutdown_1+dur_shutdown_2+add_shutdown
                        else:
                            dict_sequence=dict_sequence_1
                            transit_time = transit_time_1
                            standby_time = standby_time_1
                            dur_shutdown = dur_shutdown_1
                else:
                    _e = 'Case not considered'
                    logging.error('InspectionPortStat:' +_e)
                    raise ValueError(_e)

            ### adapt based on working shift
            if  shift is None:
                shift = 24
            days = 0
            time = 0
            for i in dict_sequence.keys():
                if time + dict_sequence[i]['duration'] > shift:
                    if time + dict_sequence[i]['duration'] > 24:
                        days+=math.ceil((time + dict_sequence[i]['duration'])/24)
                    else:
                        days+=1
                    time=0
                    if 'op_2' in i:
                        continue
                    else:
                        dur_shutdown+=24-time
                else:
                    if i == list(dict_sequence.keys())[-1]:
                        days+=1
                    else:
                        time += dict_sequence[i]['duration']
            total_dur_month.update({str(m): days})
            transit_time_month.update({str(m):transit_time})
            standby_time_month.update({str(m):standby_time})
            shutdown_month.update({str(m):dur_shutdown})

        if op_tow_port.vessel2 is not None:
            ves2 = op_tow_port.vessel2
            ves2_id = op_tow_port.vessel2.id
            ves2_n = 1
        else:
            ves2 = None
            ves2_id = None
            ves2_n = None

        dict_statistics = {
            'vessel': op_tow_port.vessel1,
            'vessel_1id': op_tow_port.vessel1.id,
            'n_vessel_1' : n_vessels,
            'vessel_2' : ves2,
            'vessel_2id': ves2_id,
            'n_vessel_2': ves2_n,
            'dur_total_dict': total_dur_month,
            'transit_time_dict': transit_time_month,
            'standby_time_dict': standby_time_month,
            'shutdown_dict': shutdown_month
        }

        return dict_statistics

    def shutdown_dict_insp_port(self, op_path:str):

        """ This function is done to subsitute the shutdown_dict as the towing plan works on statistics
        This func give only inspection_port shutdown_stats for all the devices. In log_events creation
        The towing shutdown hours are added."""

        df_stats = pd.read_csv(op_path)
        list_months = [str(c) for c in range(1,13)]

        wtg_shutdown_row = df_stats[df_stats['percentile'] == 'dur_shutdown_wtg']
        wtg_shutdown_dict=wtg_shutdown_row[list_months].to_dict(orient='records')[0]

        wec_shutdown_row = df_stats[df_stats['percentile'] == 'dur_shutdown_wec']
        wec_shutdown_dict=wec_shutdown_row[list_months].to_dict(orient='records')[0]

        pv_shutdown_row = df_stats[df_stats['percentile'] == 'dur_shutdown_pv']
        pv_shutdown_dict=pv_shutdown_row[list_months].to_dict(orient='records')[0]

        # Return only the dict with non zeros values
        for d in [pv_shutdown_dict, wec_shutdown_dict, wtg_shutdown_dict]:
            if any(float(v) > 0 for v in d.values()):
                return d

        return {}
    
    def get_inspection_statistics(
        insepctions_port: list,
        PERCENTILE: int,
        run_dir: str,
        n_port_inspections: dict,
        operations_tow_stat: list,
        shift: int
    ):
        inspections_stat = []
        for insp in insepctions_port:
            inspections_stat.append(
                InspectionPortStat(
                    inspection=insp,
                    PERCENTILE=PERCENTILE,
                    run_dir=run_dir,
                    n_port_inspections=n_port_inspections,
                    operations_tow_stat=operations_tow_stat,
                    shift=shift
                )
            )
        logging.info('InspectionPortStat: operations defined based on file class "InspectionPort"')

        return inspections_stat

    def statistical_analysis_replace(
        inspection_port
    ):
        months = [str(c) for c in range(1,13)]
        cols = ['operation_id','percentile'] + months
        stat_analysis = pd.DataFrame(columns=cols)
        stats_term = [
            'dur_total_p',
            'dur_net_port',
            'dur_net_site',
            'wait_start',
            'wait_port',
            'wait_site',
            'transit_to_site',
            'transit_to_port',
            'dur_shutdown_wtg',
            'dur_shutdown_wec',
            'dur_shutdown_pv'
        ]
        stat_analysis['percentile'] = stats_term
        stat_analysis['operation_id'] = [inspection_port.id] * len(stats_term)
        dur_tot = stat_analysis[stat_analysis['percentile'] == 'dur_total_p']
        for k in inspection_port.dur_total_dict.keys():
            dur_tot[k] = inspection_port.dur_total_dict[k]*24
        stat_analysis.update(dur_tot)
        trans_tot = stat_analysis[stat_analysis['percentile'] == 'transit_to_port']
        for k in inspection_port.transit_time_dict.keys():
            trans_tot[k] = inspection_port.transit_time_dict[k]
        stat_analysis.update(trans_tot)
        if inspection_port.id[0:3] == 'ofw':
            shut_wtg = stat_analysis[stat_analysis['percentile'] == 'dur_shutdown_wtg']
            for k in inspection_port.shutdown_dict.keys():
                shut_wtg[k] = inspection_port.shutdown_dict[k]
            stat_analysis.update(shut_wtg)
        elif inspection_port.id[0:3] == 'owc':
            shut_wec = stat_analysis[stat_analysis['percentile'] == 'dur_shutdown_wec']
            for k in inspection_port.shutdown_dict.keys():
                shut_wec[k] = inspection_port.shutdown_dict[k]
            stat_analysis.update(shut_wec)
        elif inspection_port.id[0:3] == 'opv':
            shut_pv = stat_analysis[stat_analysis['percentile'] == 'dur_shutdown_pv']
            for k in inspection_port.shutdown_dict.keys():
                shut_pv[k] = inspection_port.shutdown_dict[k]
            stat_analysis.update(shut_pv)
        else:
            _e = 'Prefix not recognized'
            logging.error('InspectionPortStat: '+_e)
            raise ValueError(_e)

        return stat_analysis