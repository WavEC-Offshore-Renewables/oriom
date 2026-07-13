
from datetime import datetime

IPMA = {
    'DF_COLUMNS' : { 
        0: [
            "year", "month", "day", "hour", "msl [hPa]", 
            "prec [mm]", "swh [m]", "pp1d [s]", "mwd [°]", 
            "mwp [s]", "wind [m/s]", "dwi [°]"
        ],
        1: [
            'year', 'month', 'day', 'hour',
            'per10swh [m]', 'per50swh [m]', 'per90swh [m]',
            'per10prec [mm]', 'per50prec [mm]', 'per90prec [mm]',
        ]
    },
    'FORECAST_COLUMNS_CONVERSION' : { 
        0: {
            'swh [m]': 'hs',
            'mwp [s]': 'tp',
            'wind [m/s]': 'ws',
        },
        1 : {}
    },
    'NAME_FILE' : datetime.now().date(),
    'NAME_FILE_SAVE' : ['previsao', 'listagem_ens']
}