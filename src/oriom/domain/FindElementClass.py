import logging


class Find_Element:

    """
    Find_element_class is used to find the element in the various classes throughout dictionaries.

    ???For each corrective operations all statistical results are included in this class.???

    Attributes:
        operations (list): List of object with attribute `id` for class `Operations`.
        operations_stats (list): List of object with attribute `id` for class `Operations_Stats`
        vessels (list): List of object with attribute `id` for class `Vessels`
        failures (list): List of object with attribute `operation_triggered` for class `Failures`

        operations_dict (dict): Dictionary of operations with items {oper.id: oper}
        operations_stats_dict (dict): Dictionary of operations statistcs with items {oper.id: oper}
        vessels_dict (dict): Dictionary of vessels with items {vessels.id: vessels}
        failures_dict (dict): Dictionary of failures with items {failures.id: failures}

    """

    def __init__(self, operations: list, operations_stats: list, operations_stats_pmax: list, vessels: list, failures: list):
        self.operations = operations
        self.operations_stats = operations_stats
        self.operations_stats_pmax = operations_stats_pmax
        self.vessels = vessels
        self.failures = failures

        # Dictionaries
        self.operations_dict = {}
        self.operations_stats_dict = {}
        self.operations_stats_pmax_dict = {}
        self.vessels_dict = {}
        self.failures_dict = {}
        self.failures_dict_id = {}

        self._create_find_element_dict()


    def _create_find_element_dict(self):
        """Create the dictionaries from the lists of object if not already presents"""

        if not (self.operations_dict or self.vessels_dict or self.failures_dict):
            self.operations_dict = {op.id: op for op in self.operations}
            self.operations_stats_dict = {op.id: op for op in self.operations_stats}
            self.operations_stats_pmax_dict = {op.id: op for op in self.operations_stats_pmax}
            self.vessels_dict = {v.id.lower(): v for v in self.vessels}
            self.failures_dict_id = {f.id: f for f in self.failures}

            for f in self.failures:
                if f.operation_triggered not in self.failures_dict:
                    self.failures_dict[f.operation_triggered] = []
                self.failures_dict[f.operation_triggered].append(f)


    @classmethod
    def create(cls, operations: list, operations_stats: list, operations_stats_pmax: list, vessels: list, failures: list):
        """
        Create the class

        Args:
            operations (list): List of object with attribute `id` for class `Operations`.
            operations_stats (list): List of object with attribute `id` for class `Operations_Stats` with P50 stats (or Pmain)
            operations_stats_pmax (list): List of object with attribute `id` for class `Operations_Stats` with P90 stats (or Pmax)
            vessels (list): List of object with attribute `id` for class `Vessels`
            failures (list): List of object with attribute `operation_triggered` for class `Failures`

        Returns:
            FindElement: Pbject initialized.
        """
        return cls(operations, operations_stats, operations_stats_pmax, vessels, failures)


    def find_operation(self, oper_id):

        """
        Find a operation associated to an operation_id

        Args:
            oper_id (:obj: str`): id of operation.

        Returns:
            object or int: Object operation if found

        Raises:
            NameError: If the operation is not found
        """

        op = self.operations_dict.get(oper_id)
        if op is None:
            _e = f'Operation not found {oper_id}'
            logging.error('LogDates: ' + _e)
            raise NameError(_e)
        return op


    def find_operation_stats(self, oper_id):

        """
        Find a operation_stats associated to an operation_id

        Args:
            oper_id (:obj: str`): id of operation.

        Returns:
            object or int: Object operation_stat if found

        Raises:
            NameError: If the operation is not found
        """

        op = self.operations_stats_dict.get(oper_id)
        if op is None:
            _e = f'Operation_stat not found {oper_id}'
            logging.error('LogDates: ' + _e)
            raise NameError(_e)
        return op

    def find_operation_stats_pmax(self, oper_id):

        """
        Find a operation_stats_pmax associated to an operation_id

        Args:
            oper_id (:obj: str`): id of operation.

        Returns:
            object or int: Object operation_stat if found

        Raises:
            NameError: If the operation is not found
        """

        op = self.operations_stats_pmax_dict.get(oper_id)
        if op is None:
            _e = f'Operation_stat_pmax not found {oper_id}'
            logging.error('LogDates: ' + _e)
            raise NameError(_e)
        return op

    def find_vessel(self, oper_vessel):

        """
        Find a vessel associated to an operation

        Args:
            oper_vessel (:str:): Id of the vessel.

        Returns:
            object or int: Object vessel if found

        Raises:
            NameError: If the vessel is not found
        """

        vessel_id = oper_vessel.lower()
        v = self.vessels_dict.get(vessel_id)
        if v is None:
            _e = f'LogDates: vessel not found {vessel_id}'
            logging.error(_e)
            raise NameError(_e)
        return v


    def find_failure(self, oper):

        """
        Find a failure associated to an operation

        Args:
            oper (:obj: `Operation`): Element of operation.

        Returns:
            object or int: Object failure or list of Object failure if found, `0` if the operation is a tow operation (`tow_to_port=True`).

        Raises:
            NameError: If the failure is not found and the operation analyzed is not tow operation.
        """
        f = self.failures_dict.get(oper.id)
        if f:
            return f
        elif getattr(oper, "tow_to_port", None):
            return 0
        else:
            _e = f'LogDates: Failure not found {oper.id} \nThe operation is not triggered by a failure, or some error occurred'
            logging.warning(_e)
            raise NameError(_e)

    def find_failure_from_id(self, fail_id):

        """
        Find a failure associated to an failure id

        Args:
            fail_id (str): id of the failure.

        Returns:
            object or int: Object failure if found, `0` if the operation is a tow operation (`tow_to_port=True`).

        Raises:
            NameError: If the failure is not found and the operation analyzed is not tow operation.
        """

        f = self.failures_dict_id.get(fail_id)
        if f:
            return f
        else:
            _e = f'LogDates: Failure not found {fail_id} \nThe operation is not triggered by a failure, or some error occurred'
            logging.warning(_e)
            raise NameError(_e)


    def find_oper_schedule(self, inspe):

        """
        Find the ts data associated to an opeartion.

        Args:
            inspe (object): Inpection to analize

        Returns:
            object: ts_data of the opeartion.
        """

        inspection = self.find_operation(inspe)

        return getattr(inspection, "ts_data", None)
