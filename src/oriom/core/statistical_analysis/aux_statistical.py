
def find_percentiles(inputs_stats:object):
    """ Find max and main percentile and return a dictionary"""
    for percent in inputs_stats.percentiles["value"]:
        try:
            perc_max = max(percent, perc_max, 0)
        except NameError:
            perc_max = percent
    inputs_stats.percentile_max = {"value": int(perc_max), "units": None}

    percentiles = {"pmax": inputs_stats.percentile_max["value"], "pmain": inputs_stats.percentile_main["value"]}
    return percentiles