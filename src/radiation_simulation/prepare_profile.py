import os
import argparse
from pathlib import Path
from inspect import cleandoc as multi_line_str

import cx_Oracle
import datetime as dt
import ROOT

from utils import generalUtils as gUtl
from utils import databaseUtils as dbUtl
from utils import eraUtils as eraUtl
from utils import pixelDesignUtils as designUtl
from utils.modules import ReadoutGroup
from temperatures.helpers import get_sensor_temperature
from fluence.helpers import get_fluence
import currents.helpers as helpers



ROOT.PyConfig.IgnoreCommandLineOptions = True
PROFILE_FORMAT = "%d\t%d\t%d\t\t%4.2f\t\t%10d\t\t%6.2f"
USER_NAME, PASSWORD, DATABASE_NAME = dbUtl.get_oms_database_user_password_and_name()
NA_VALUE = -999

## This needs much more fine-grained information than the plots of the current, since it relies on 
## conditions at each timestep


def __get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i", "--input_fills_file_name",
        help="Luminosity file",
        required=False,
        default="data/fills_info/fills.csv",
    )
    parser.add_argument(
        "-ff", "--first_fill",
        help="First fill number to analyse",
        type=int,
        required=False,
    )
    parser.add_argument(
        "-lf", "--last_fill",
        help="Last fill number to analyse",
        type=int,
        required=False,
    )
    parser.add_argument(
        '-rog', "--readout_group",
        help='Read out group name, e.g. BPix_BmI_SEC4_LYR1',
    )
    parser.add_argument(
        "-f", "--fluence_file",
        help='Input fluence ROOT file',
        default="data/fluence/fluence_field_phase1_6500GeV.root",
    )
    parser.add_argument(
        "-o", "--output_directory",
        help="Output directory name",
        required=False,
        default="data/radiation_simulation/",
    )
    parser.add_argument(
        "-p", "--profile",
        help="Output profile file name",
        required=False,
        default="profile.csv",
    )
    parser.add_argument(
        "-skip", "--skip_existing_output",
        help="Skip if output profile file already exists",
        required=False,
        action="store_true",
    )
    parser.add_argument(
        "-di", "--interfill_delay",
        help="Time at which to perform first measurement during the interfill in seconds",
        type=int,
        required=False,
        default=1200,
    )
    parser.add_argument(
        "-df", "--fill_delay",
        help="Time at which to perform first measurement during the fill in seconds",
        type=int,
        required=False,
        default=1200,
    )
    parser.add_argument(
        "-tsi", "--interfill_time_step",
        help="Time step during interfill in seconds",
        type=int,
        required=False,
        default=3600,
    )
    parser.add_argument(
        "-tsf", "--fill_time_step",
        help="Time step during fill in seconds",
        type=int,
        required=False,
        default=3600,
    )
    parser.add_argument(
        "-v", "--verbose",
        help="Print out lines written to profile",
        required=False,
        action="store_true",
    )

    return parser.parse_args()

# TODO: Many of the functions here are a duplicate/variant of some already
#       existing functions. They should go to some helper/utility scripts
#       and be used by other scripts.

# This data should have already been processed in get_current_from_database
def __get_leakage_current(readout_group, begin_time, end_time):

    connection = cx_Oracle.connect('%s/%s@%s' % (USER_NAME, PASSWORD, DATABASE_NAME))
    cursor = connection.cursor()
    cursor.arraysize = 50

    phase = eraUtl.get_phase_from_time(begin_time)

    channel_name = designUtl.get_omds_leakage_current_cable_name_from_readout_group_name(readout_group.name, phase=phase)

    if phase == 1:
        sub_system = channel_name.split("_")[0]
        channel_name = channel_name.replace(sub_system, sub_system + "%")
        cable_condition = f"lal.alias LIKE 'CMS_TRACKER/{channel_name}'"
    else:
        raise NotImplementedError


    output = helpers.read_currents_from_db(connection, cursor, begin_time, end_time, cable_condition)
    
    # TODO: This is very slow, since it will keep going backwards in time until it finds something. Maybe there should be some sort of cap?
    # Otherwise, is there a smarter way to determine the time interval?
    if len(output) == 1:
        leakage_current = output[0][1]
    elif len(output) == 0:
        # leakage_current = NA_VALUE
        leakage_current = __get_leakage_current(readout_group, begin_time - dt.timedelta(0, 3600), begin_time)
    else:
        print("Error: Leakage current query returned %d rows, but should return at most 1 only!" % (len(output)))

    #print(begin_time, end_time, leakage_current)
    return leakage_current


def __get_lumi(begin_datetime, end_datetime):
    """Return luminosity for the given time window.
    
    Args:
        measurement_time (datetime.datetime): end 
    """

    time_format = "%02d/%02d/%02d %02d:%02d:%02d"
    begin_time = time_format % (
        begin_datetime.month,
        begin_datetime.day,
        begin_datetime.year-2000,
        begin_datetime.hour,
        begin_datetime.minute,
        begin_datetime.second,
    )
    end_time = time_format % (
        end_datetime.month,
        end_datetime.day,
        end_datetime.year-2000,
        end_datetime.hour,
        end_datetime.minute,
        end_datetime.second,
    )
    command_line = f'brilcalc lumi --begin "{begin_time}" --end "{end_time}" -u /fb --output-style csv'
    out = os.popen(command_line).read()
    lumi = float(out.split("\n")[-2].split(",")[-2])

    return lumi



def __get_fill_data(readout_group, pp_cross_section, fluence_field, measurement_time, time_interval, is_interfill=False):
    """Return radiation simulation data for an interval during the fill.

    Returned quantities are duration, leakage current, temperature and fluence.
    """

    begin_time = measurement_time - time_interval
    end_time = measurement_time

    duration = time_interval.total_seconds()
    if is_interfill:
      leakage_current = NA_VALUE
      fluence = 0
    else:
      leakage_current = __get_leakage_current(readout_group, begin_time, end_time)
      lumi = __get_lumi(begin_time, end_time) / duration
      fluence = get_fluence(readout_group, pp_cross_section, fluence_field, lumi)

    temperature = get_sensor_temperature(
        readout_group,
        begin_time,
        end_time,
        correct_for_self_heating=True,
        correct_for_fluence= (not is_interfill),
        fluence=fluence,
    )

    return duration, temperature, leakage_current, fluence


def __get_and_write_fill_measurement(
        profile_text,
        fill_number,
        readout_group,
        pp_cross_section,
        fluence_field,
        begin_time,
        measurement_time,
        verbose,
        add_to_duration=dt.timedelta(0, 0),
        is_interfill = False,
    ):

    time_interval = measurement_time - begin_time
    duration, temperature, leakage_current, fluence = __get_fill_data(
        readout_group,
        pp_cross_section,
        fluence_field,
        measurement_time,
        time_interval,
        is_interfill = is_interfill,
    )
    duration += add_to_duration.total_seconds()
    if(fill_number==0):
      fill_number = NA_VALUE
    line = PROFILE_FORMAT % (fill_number,
        dt.datetime.timestamp(measurement_time + add_to_duration),
        duration, temperature, fluence, leakage_current)
    if verbose: print(line)
    profile_text.append(line)
    print(line)


def __add_fill_to_profile(
        profile_text,
        fill_number,
        readout_group,
        pp_cross_section,
        fluence_field,
        begin_stable_beam_time,
        end_stable_beam_time,
        fill_time_delay,
        fill_time_interval,
        verbose,
        is_interfill = False,
    ):

    # First measurement after time delay
    last_measurement_time = begin_stable_beam_time
    measurement_time = begin_stable_beam_time + fill_time_delay


    __get_and_write_fill_measurement(
        profile_text,
        fill_number,
        readout_group,
        pp_cross_section,
        fluence_field,
        last_measurement_time,
        measurement_time,
        verbose,
        is_interfill = is_interfill,
    )
    last_measurement_time = measurement_time

    # Measurements every time interval
    measurement_time = last_measurement_time + fill_time_interval
    while measurement_time < end_stable_beam_time:
        __get_and_write_fill_measurement(
            profile_text,
            fill_number,
            readout_group,
            pp_cross_section,
            fluence_field,
            last_measurement_time,
            measurement_time,
            verbose,
            is_interfill = is_interfill,
        )
        last_measurement_time = measurement_time
        measurement_time += fill_time_interval

    if(is_interfill):
      # Last measurement at end of interfill
      # Cannot read values right at the end of stable beam, because the Pixel
      # Pixel goes in HV on right when stable beams are declared
      if (begin_stable_beam_time - last_measurement_time).total_seconds() > 300:
          time_delta = dt.timedelta(0, 300)
      elif (begin_stable_beam_time - last_measurement_time).total_seconds() > 120:
          time_delta = dt.timedelta(0, 120)
      else:
          time_delta = dt.timedelta(0, 0)
      measurement_time = begin_stable_beam_time - time_delta
    else:
      # Last measurement at end of fill
      # Cannot read leakage current right at the end of stable beam, because the
      # Pixel goes in HV off a couple of minutes before the end of stable beam
      measurement_time = end_stable_beam_time
      if (end_stable_beam_time - last_measurement_time).total_seconds() > 300:
          time_delta = dt.timedelta(0, 300)
      elif (end_stable_beam_time - last_measurement_time).total_seconds() > 120:
          time_delta = dt.timedelta(0, 120)
      else:
          time_delta = dt.timedelta(0, 0) 

      measurement_time = end_stable_beam_time - time_delta
    print(measurement_time, last_measurement_time, time_delta, end_stable_beam_time)

    __get_and_write_fill_measurement(
        profile_text,
        fill_number,
        readout_group,
        pp_cross_section,
        fluence_field,
        last_measurement_time,
        measurement_time,
        verbose,
        add_to_duration=time_delta,
        is_interfill = is_interfill,
    )


def write_profile(profile, profile_text):
    for line in profile_text:
        profile.write(line + "\n")


def quit():
    print("\nFINISHED")
    exit(0)


def main():
    args = __get_arguments()

    Path(args.output_directory).mkdir(parents=True, exist_ok=True)

    fills_info = gUtl.get_fill_info(args.input_fills_file_name)
    good_fills = fills_info.fill_number.to_list()
    fluence_root_file = ROOT.TFile.Open(args.fluence_file)
    fluence_field = fluence_root_file.Get("fluence_allpart")

    readout_group = ReadoutGroup(args.readout_group)

    end_stable_beam_datetime_last_fill = None
    interfill_time_delay = dt.timedelta(0, args.interfill_delay)
    interfill_time_interval = dt.timedelta(0, args.interfill_time_step)
    fill_time_delay = dt.timedelta(0, args.fill_delay)
    fill_time_interval = dt.timedelta(0, args.fill_time_step)

    profile_path = args.output_directory + "/" +  args.profile
    if os.path.exists(profile_path) and args.skip_existing_output:
        print(f"Skiping because {profile_path} already exists!")
        quit()

    profile_text = []

    header_line = "Fill\tTimestamp [s]\tDuration [s]\tTemperature [K]\tFluence [n_eq/cm2/s]\tLeakage_current [mA/cm2]"
    if args.verbose: print(header_line)
    profile_text.append(header_line)

    for fill in range(args.first_fill, args.last_fill+1):
        print(fill)
        if not fill in good_fills: continue

        fill_info = fills_info[fills_info.fill_number == fill]
        if len(fill_info) != 1:
            print("Error!")
            exit(0)

        pp_cross_section = eraUtl.get_pp_cross_section(fill)

        begin_stable_beam_time = dt.datetime.fromisoformat(fill_info.start_stable_beam.to_list()[0])
        end_stable_beam_time = dt.datetime.fromisoformat(fill_info.end_stable_beam.to_list()[0])

        if end_stable_beam_datetime_last_fill is not None:
            interfill_duration = begin_stable_beam_time - end_stable_beam_datetime_last_fill
            if interfill_duration < interfill_time_delay:
                print(f"Warning: Interfill duration ({interfill_duration.total_seconds()/60} min.) "
                      f"smaller than interfill time delay, no data collected during interfill "
                      f"{begin_stable_beam_time} to {end_stable_beam_datetime_last_fill}")
            else:
                __add_fill_to_profile(
                    profile_text,
                    0,
                    readout_group,
                    0,
                    0,
                    end_stable_beam_datetime_last_fill,
                    begin_stable_beam_time,
                    interfill_time_delay,
                    interfill_time_interval,
                    verbose=args.verbose,
                    is_interfill = True
                )

        fill_duration = end_stable_beam_time - begin_stable_beam_time
        if fill_duration < fill_time_delay:
            print(f"Warning: Fill duration ({fill_duration.total_seconds()/60} min.) "
                  f"smaller than fill time delay, no data collected during fill {fill}")
        else:
            __add_fill_to_profile(
                profile_text,
                fill,
                readout_group,
                pp_cross_section,
                fluence_field,
                begin_stable_beam_time,
                end_stable_beam_time,
                fill_time_delay,
                fill_time_interval,
                verbose=args.verbose,
            )

        end_stable_beam_datetime_last_fill = end_stable_beam_time

    profile = open(profile_path, "w")
    write_profile(profile, profile_text)
    #quit()


if __name__ == "__main__":
    main()
