from inspect import cleandoc as multi_line_str
from pathlib import Path
import argparse 

import cx_Oracle
import datetime as dt

from utils import generalUtils as gUtl
from utils import databaseUtils as dbUtl
from utils import eraUtils as eraUtl
from utils import pixelDesignUtils as designUtl
import currents.helpers as helpers


user_name, password, database_name = dbUtl.get_oms_database_user_password_and_name()


def __get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i", "--input_fills_file_name",
        help="Fills file, default=%(default)s",
        required=False,
        default="data/fills_info/fills.csv",
    )
    parser.add_argument(
        "-o", "--output_directory",
        help="Output directory name, default=%(default)s",
        required=False,
        default="data/currents/from_database",
    )
    parser.add_argument(
        "-ff", "--first_fill",
        help="First fill number to analyse",
        type=int,
        required=True,
    )
    parser.add_argument(
        "-lf", "--last_fill",
        help="Last fill number to analyse",
        type=int,
        required=True,
    )
    parser.add_argument(
        "-s", "--sub_system",
        help="Sub-detector to analyse",
        choices=["Barrel", "EndCap"],
        required=True,
    )
    parser.add_argument(
        "-t", "--measurement_delay",
        help="Time in s after which to measure the currents, default=%(default)s s",
        default=1200,
        type=int,
        required=False,
    )

    return parser.parse_args()


def main(args):

    Path(args.output_directory).mkdir(parents=True, exist_ok=True)

    python_time_mask = "%d-%b-%Y %H.%M.%S.%f"
    oracle_time_mask = "DD-Mon-YYYY HH24.MI.SS.FF"
    
    connection = cx_Oracle.connect('%s/%s@%s' % (user_name, password, database_name))
    cursor = connection.cursor()
    cursor.arraysize = 50


    fills_info = gUtl.get_fill_info(args.input_fills_file_name)
    good_fills = fills_info.fill_number.to_list()

    for fill in range(args.first_fill, args.last_fill+1):
        
        if not fill in good_fills: continue
    
        phase = eraUtl.get_phase_from_fill(fill)
        allowed_layers = designUtl.get_layer_names(phase) + designUtl.get_disk_names(phase)

        fill_info = fills_info[fills_info.fill_number == fill]
        if len(fill_info) != 1:
            print("Error!")
            exit(0)

        begin_time = dt.datetime.fromisoformat(fill_info.start_stable_beam.to_list()[0])
        end_time = dt.datetime.fromisoformat(fill_info.end_stable_beam.to_list()[0])
        delay = dt.timedelta(0, args.measurement_delay)
        if (end_time - begin_time) < delay:
            measurement_time = end_time
        else:
            measurement_time = begin_time + delay

        output = helpers.read_currents_from_db(connection, cursor, begin_time, measurement_time, "(lal.alias LIKE 'CMS_TRACKER/%Pixel%/channel00%')")
        
        currents_file_name = args.output_directory + "/" + str(fill) + "_" + args.sub_system + ".txt"
        output_file = open(currents_file_name, "w+")
        for row in output:
            print (row)
            cable, i_mon, v_mon, time  = row
            layer = designUtl.get_layer_name_from_cable_name(cable)
            if layer not in allowed_layers:
                continue
            if not args.sub_system in cable:
                continue
            else:
                line = "%s   %s   %s   %s\n" % (cable, i_mon, v_mon, time)
                output_file.write(line)
    
        output_file.close()
        print("%s saved." % currents_file_name)
    
    connection.close()
    

if __name__ == "__main__":

    args = __get_arguments()
    main(args)
