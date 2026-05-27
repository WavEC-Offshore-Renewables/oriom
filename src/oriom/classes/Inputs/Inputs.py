from oriom.classes.Inputs.Costs import Cost
from oriom.classes.Inputs.Statisticals import Statistical
from oriom.classes.Inputs.Timeseries import TimeSeries
from oriom.classes.Inputs.Generals import General


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