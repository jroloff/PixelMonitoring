import re
from inspect import cleandoc as multi_line_str

import cx_Oracle
import datetime as dt

from voltages.helpers import is_hv_on
from utils import pythonUtils as pyUtl
from utils import databaseUtils as dbUtl
from config.cooling.omds_dcs_aliases import omds_to_dcs_alias
from utils.constants import CELSIUS_TO_KELVIN


USER_NAME, PASSWORD, DATABASE_NAME = dbUtl.get_oms_database_user_password_and_name()


def get_number_of_sensors_in_cooling_loop(cooling_loop_sensor_name):
    """Get number of working sensors in the given cooling pipe.

    Args:
        cooling_loop_sensor_name (str): OMDS database cooling pipe name, e.g. PixelBarrel_BmI_1I_L4D2MN

    Returns:
        int
    """

    if ("L1D1" in cooling_loop_sensor_name):
        n_sensors = 3 if "F" in cooling_loop_sensor_name else 2

    if ("L1D2" in cooling_loop_sensor_name):
        n_sensors = 2 if "F" in cooling_loop_sensor_name else 3

    if ("L2D1" in cooling_loop_sensor_name):
        n_sensors = 3

    if ("L2D2" in cooling_loop_sensor_name):
        n_sensors = 2

    if ("L3D1" in cooling_loop_sensor_name):
        n_sensors = 3 if "F" in cooling_loop_sensor_name else 2

    if ("L3D2" in cooling_loop_sensor_name):
        n_sensors = 3

    if ("L3D3" in cooling_loop_sensor_name):
        n_sensors = 3

    if ("L3D4" in cooling_loop_sensor_name):
        n_sensors = 3

    if ("L4D" in cooling_loop_sensor_name):
        n_sensors = 3

    return n_sensors


def get_sectors_regex_from_cooling_loop_sensor_name(cooling_loop_sensor_name):
    """Get regex of the BPix sectors cooled down by a cooling pipe.

    Args:
        cooling_loop_sensor_name (str): OMDS database cooling pipe name, e.g. PixelBarrel_BmI_1I_L4D2MN

    Returns:
        str
    """

    def __make_regex(cooling_loop_sensor_name, suffix):
    
        if ("N" in cooling_loop_sensor_name): # Near
            sectors_regex = cooling_loop_sensor_name[:5] + "B[mp]I_" + suffix
    
        if ("F" in cooling_loop_sensor_name): # Far
            sectors_regex = cooling_loop_sensor_name[:5] + "B[mp]O_" + suffix
    
        return sectors_regex


    cooling_loop_sensor_name = cooling_loop_sensor_name.replace("PixelBarrel", "BPix")
    cooling_loop_sensor_name = cooling_loop_sensor_name.replace("PixelEndcap", "FPix")

    if ("L1D1" in cooling_loop_sensor_name):
        sectors_regex = __make_regex(cooling_loop_sensor_name, "SEC[1234]_LYR1")

    if ("L1D2" in cooling_loop_sensor_name):
        sectors_regex = __make_regex(cooling_loop_sensor_name, "SEC[5678]_LYR1")

    if ("L2D1" in cooling_loop_sensor_name):
        sectors_regex = __make_regex(cooling_loop_sensor_name, "SEC[1234]_LYR2")

    if ("L2D2" in cooling_loop_sensor_name):
        sectors_regex = __make_regex(cooling_loop_sensor_name, "SEC[5678]_LYR2")

    if ("L3D1" in cooling_loop_sensor_name):
        sectors_regex = __make_regex(cooling_loop_sensor_name, "SEC[12]_LYR3")

    if ("L3D2" in cooling_loop_sensor_name):
        sectors_regex = __make_regex(cooling_loop_sensor_name, "SEC[34]_LYR3")

    if ("L3D3" in cooling_loop_sensor_name):
        sectors_regex = __make_regex(cooling_loop_sensor_name, "SEC[56]_LYR3")

    if ("L3D4" in cooling_loop_sensor_name):
        sectors_regex = __make_regex(cooling_loop_sensor_name, "SEC[78]_LYR3")

    if ("L4D1" in cooling_loop_sensor_name):
        sectors_regex = __make_regex(cooling_loop_sensor_name, "SEC[12]_LYR4")

    if ("L4D2" in cooling_loop_sensor_name):
        sectors_regex = __make_regex(cooling_loop_sensor_name, "SEC[34]_LYR4")

    if ("L4D3" in cooling_loop_sensor_name):
        sectors_regex = __make_regex(cooling_loop_sensor_name, "SEC[56]_LYR4")

    if ("L4D4" in cooling_loop_sensor_name):
        sectors_regex = __make_regex(cooling_loop_sensor_name, "SEC[78]_LYR4")

    return sectors_regex


def get_module_cooling_loop_temperature(readout_group, begin_time, end_time):
    """Get cooling loop temperature corresponding to a BPix read out group.

    Args:
        readout_group (utils.modules.ReadoutGroup)
        begin_time (datetime.datetime)
        end_time (datetime.datetime)
    
    Returns:
        float: Cooling pipe temperature in K
    """

    connection = cx_Oracle.connect('%s/%s@%s' % (USER_NAME, PASSWORD, DATABASE_NAME))
    cursor = connection.cursor()
    cursor.arraysize = 50

    name = "PixelBarrel(.*)(PF|PN|MF|MN)(.*)"
    
    query = multi_line_str("""
        WITH ids as (
            SELECT id, SUBSTR(alias, INSTR(alias,'/',-1)+1) AS part 
            FROM cms_trk_dcs_pvss_cond.aliases
            JOIN cms_trk_dcs_pvss_cond.dp_name2id 
            ON RTRIM(cms_trk_dcs_pvss_cond.aliases.dpe_name,'.') = cms_trk_dcs_pvss_cond.dp_name2id.dpname
            WHERE REGEXP_LIKE(substr(alias,instr(alias,'/',-1)+1), :name)
        )
        SELECT part, value_converted, change_date 
        FROM ids
        JOIN cms_trk_dcs_pvss_cond.tkplcreadsensor ON ids.id = cms_trk_dcs_pvss_cond.tkplcreadsensor.DPID 
        WHERE cms_trk_dcs_pvss_cond.tkplcreadsensor.change_date >= :start_time
        AND cms_trk_dcs_pvss_cond.tkplcreadsensor.change_date < :stop_time
        ORDER BY cms_trk_dcs_pvss_cond.tkplcreadsensor.change_date DESC
    """)

    cursor.execute(query, {'name': name, 'start_time': begin_time, 'stop_time': end_time})
    rows = cursor.fetchall()
    connection.close()

    n_sensors = None
    temperatures = {}

    for item in rows:
        cooling_loop_sensor_name = item[0]
        temperature = item[1]
        date_changed = item[2]

        if temperature is None:
            print("Warning: Cooling loop sensor %s temperature is None" % cooling_loop_sensor_name)
            continue

        if float(temperature) > 40:
            print("Warning: Faulty sensor for cooling loop sensor %s" % cooling_loop_sensor_name)
            continue # ignore the broken temperature sensors giving crazy values

        # Correct the cooling loop alias mismapping from OMDS to DCS
        omds_alias = pyUtl.list_to_str(cooling_loop_sensor_name.split("_")[-2:], "_")
        dcs_alias = omds_to_dcs_alias(omds_alias)
        if dcs_alias is None:
            continue # Error message must have been sent by the omds_to_dcs_alias function
        
        cooling_loop_sensor_name = cooling_loop_sensor_name.replace(omds_alias, dcs_alias) 

        sectors_regex = get_sectors_regex_from_cooling_loop_sensor_name(cooling_loop_sensor_name)

        if re.search(sectors_regex, readout_group.name):
            # We get the first occurence of the temperature, because
            # temperatures are ordered by decreasing time
            if cooling_loop_sensor_name not in temperatures.keys():
                temperatures[cooling_loop_sensor_name] = temperature
                
            if n_sensors is None:
                n_sensors = get_number_of_sensors_in_cooling_loop(cooling_loop_sensor_name)

    if n_sensors is None or len(temperatures.keys()) < n_sensors:
        time_window_extension = 10 * dt.timedelta(0, 3600)
        return get_module_cooling_loop_temperature(readout_group, begin_time - time_window_extension, end_time)

    else:
        temperatures_values = temperatures.values()
        temperatures_avg = sum(temperatures_values) / len(temperatures_values)
        return temperatures_avg + CELSIUS_TO_KELVIN


def correct_temperature_for_self_heating(temperature, readout_group_name, hv_on):
    """Correct cooling pipe temperature for self heating to get the sensor temperature.
    
    Args:
        temperature: Cooling pipe temperature
        readout_group_name (str): e.g. BPix_BmI_SEC4_LYR1
        hv_on (bool)
    
    Returns:
        float: Sensor temperature in K
    """

    if hv_on:
        if "LYR4" in readout_group_name:
            temperature_difference = 4
        else:
            temperature_difference = 3
    else:
        temperature_difference = 0

    return temperature + temperature_difference


def correct_temperature_for_fluence(temperature, fluence, scaling_factor=3e-8):
    """Correct cooling pipe temperature for self heating to get the sensor temperature.
    
    Args:
        temperature: Cooling pipe temperature
        fluence: Instantaneous fluence in n_eq/cm2/s
    
    Returns:
        float: Sensor temperature in K
    """

    return temperature + scaling_factor * fluence


def get_sensor_temperature(
        readout_group,
        begin_time,
        end_time,
        correct_for_self_heating=True,
        correct_for_fluence=True,
        fluence=None,
    ):
    """Get silicon sensor temperature.
    
    Args:
        readout_group (utils.modules.ReadoutGroup)
        begin_time (datetime.datetime)
        end_time (datetime.datetime)
        correct_for_self_heating (bool, optional, default=True)
        correct_for_fluence (bool, optional, default=True)
        fluence (float): Instantaneous fluence in n_eq/cm2/s.
            Must be provided if correct_for_fluence=True.
    
    Returns:
        float: Sensor temperature in K
    """

    hv_on = is_hv_on(begin_time, end_time, readout_group)
    assert (correct_for_fluence and fluence is not None) or not correct_for_fluence

    temperature =  get_module_cooling_loop_temperature(
        readout_group,
        begin_time,
        end_time,
    )
    if correct_for_self_heating:
        temperature = correct_temperature_for_self_heating(
            temperature,
            readout_group.name,
            hv_on,
        )
    if correct_for_fluence and hv_on:
        temperature = correct_temperature_for_fluence(
            temperature,
            fluence,
        )

    return temperature
