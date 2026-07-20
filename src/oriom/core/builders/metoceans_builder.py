from oriom.domain.Metocean import Metocean


def metocean_builder(        
    dirs: object,
    inputs: object,
    farm_technologies: object,
) -> tuple[object | dict, dict]:
    """
    Create Metoceans object for site, port an tow if they exist.
    
    Args:
        dirs (str | Path): Object of directory Path from the class ``ProjectDirs``.
        inputs (object): Object of the class ``Input`` to initialize the Metocean data.
        farm_technologies (object): Object of the class ``farm_technologies`` Wind farm configuration object.

    Returns:
        dict:
            A dictionaries of Metocean instances for site, port tow and tow distance between points
    """

    metocean, _ = Metocean.from_run_dir(
        run_dir=dirs.run_dir,
        tseries_inputs=inputs.tseries,
        power_farm=farm_technologies.power,
        wtg=farm_technologies.wtg,
        z0=inputs.tseries.surface_roughness["value"],
        stat_inputs=inputs.stats,
    )
    
    metocean_port, _ = Metocean.from_run_dir(
        run_dir=dirs.run_dir,
        tseries_inputs=inputs.tseries,
        stat_inputs=inputs.stats,
        port_metocean = True,
        site_metocean = metocean
    )

    # Build Metocean tow in one call
    metocean_tow, metocean_tow_distance = Metocean.from_run_dir(
        run_dir=dirs.run_dir,
        tseries_inputs=inputs.tseries,
        stat_inputs=inputs.stats,
        tow_metocean = True
    )

    # Attach power columns and get power-only view
    metocean = Metocean.attach_power_columns(metocean = metocean, power_farm = farm_technologies.power, out_dir=dirs.run_dir)

    return {
        'metocean': metocean,
        'metocean_port': metocean_port,
        'metocean_tow': metocean_tow,
        'metocean_tow_distance': metocean_tow_distance
    }
