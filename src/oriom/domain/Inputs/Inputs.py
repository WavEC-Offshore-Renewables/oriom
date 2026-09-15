from oriom.domain.Inputs.Costs import Cost
from oriom.domain.Inputs.Statisticals import Statistical
from oriom.domain.Inputs.Timeseries import TimeSeries
from oriom.domain.Inputs.Generals import General


class Inputs:
    General = General
    Statistical = Statistical
    Cost = Cost
    TimeSeries = TimeSeries

    def __init__(self, general, stats, cost, tseries):
        self.general = general
        self.stats = stats
        self.cost = cost
        self.tseries = tseries


if __name__ == '__main__':
    pass