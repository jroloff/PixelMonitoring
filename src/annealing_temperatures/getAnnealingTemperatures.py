import os
from inspect import cleandoc as multi_line_str
from pathlib import Path
import argparse
import time

from datetime import datetime, timedelta

from utils import pythonUtils as pyUtl
from utils import databaseUtils as dbUtl


def __get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o", "--output_directory",
        help="Output directory name",
        default="data/temperatures/annealing",
    )
    parser.add_argument(
        "-s", "--start_date",
        help="Start date, in the format YYYY-MM-DD",
    )
    parser.add_argument(
        "-e", "--end_date",
        help="End date, in the format YYYY-MM-DD",
    )
    parser.add_argument(
        "-ff", "--first_fill",
        help="First fill number to analyse",
        type=int,
    )
    parser.add_argument(
        "-lf", "--last_fill",
        help="Last fill number to analyse",
        type=int,
    )
    parser.add_argument(
        "-sfn", "--sensor_names",
        help="File containing temperature sensors names",
        default="config/temperatures/temperature_sensor_names.txt"
    )

    return parser.parse_args()


def __sanity_checks(args):
    assert (args.start_date and args.end_date) or (args.first_fill and args.last_fill)


def __get_dates_in_file(file_name):
    if os.path.exists(file_name):
        with open(file_name, "r") as file:
            return list(map(lambda x: x.split()[0], file.read().splitlines()))
    else:
        return []


def get_temperatures(output_directory, start_date, end_date, sensors_list):

    hours = 0.
    prevhours = 0
    prevtemp = 0
    avgtemp = 0
    restofday = 0.
    averaging = False

    start_date_str = str(start_date.date())
    end_date_str = str(end_date.date())

    query = multi_line_str("""
        WITH ids AS (
            SELECT id,
                   alias,
                   since,
                   RTRIM(dpe_name,'.') AS dp,
                   SUBSTR(alias, INSTR(alias,'/',-1)+1) AS part,
                   update_count,
                   cms_trk_dcs_pvss_cond.dp_name2id.dpname AS dpname
            FROM cms_trk_dcs_pvss_cond.aliases,
                 cms_trk_dcs_pvss_cond.dp_name2id
            WHERE dpname LIKE '%Pixel%'
                  AND RTRIM(cms_trk_dcs_pvss_cond.aliases.dpe_name, '.') = dpname
            )
        SELECT part, alias, since, update_count, value_converted, change_date, dpname
        FROM cms_trk_dcs_pvss_cond.tkplcreadsensor, ids
        WHERE ids.id = cms_trk_dcs_pvss_cond.tkplcreadsensor.dpid
              AND change_date >= TO_TIMESTAMP('{start_time}', 'RRRR-MM-DD HH24:MI:SS.FF')
              AND change_date < TO_TIMESTAMP('{end_time}', 'RRRR-MM-DD HH24:MI:SS.FF')
        ORDER BY part, change_date""".format(
            start_time=start_date_str,
            end_time=end_date_str,
        )
    )
    rows = dbUtl.fetch(query)

    temperatures = {}

    for i, item in enumerate(rows):
        moduleName = item[0]
        temp = item[4]
        date_changed = format(item[5]) # format: Julia

        if moduleName not in temperatures:
            temperatures[moduleName] = [ [], [] ]


        temperatures[moduleName][0].append( date_changed )
        temperatures[moduleName][1].append( temp )

    d = temperatures
    
    # access datetimes and temperatures
    for sensor_name in sensors_list:
        sensor_file_name = output_directory + "/" + sensor_name + ".txt"
        DBentry_i = 0;
        times = d[sensor_name][0]
        temps = d[sensor_name][1]
        if (len(times) != len(temps)) :
            print("DB file: Number of temperature entries and date entries do not match");
            continue;
        while DBentry_i < len(temps):
            ## construct one temperature entry per day:
            ## average according to hours in case of multiple entries
            ## continue last valid value for days without entry
            dates_in_file = __get_dates_in_file(sensor_file_name)
            with open(sensor_file_name, "a") as outfile:
                date_i = start_date;
                day_i = 0;
                while (date_i.date() <= end_date.date()):
                    if ((averaging == False) and (DBentry_i < len(temps))):
                        try:
                            currentdatetime = datetime.strptime(times[DBentry_i], '%Y-%m-%d %H:%M:%S.%f')
                        except:
                            currentdatetime = datetime.strptime(times[DBentry_i], '%Y-%m-%d %H:%M:%S')
                        finally:
                            if (date_i.date() < currentdatetime.date()):
                                if (day_i > 0): # write from 23 May onwards
                                    if (day_i == 1):
                                        print("Start writing from this date onwards: " + str(date_i.date()))
                                    date = str(int(time.mktime(date_i.timetuple()))) + "000"
                                    if date not in dates_in_file:
                                        outfile.write(date + '\t' + str(prevtemp) + '\n');
                                day_i += 1;
                                date_i = start_date + timedelta(day_i);
                                avgtemp = 0;
                            else :
                                averaging = True;
                                prevhours = float(currentdatetime.hour) + float(currentdatetime.minute)/60 + float(currentdatetime.second/3600); # until the new entrytime prevtemp is valid
                                try:
                                    avgtemp = prevhours * prevtemp;
                                except:
                                    pass
                                finally:
                                    prevtemp = temps[DBentry_i];
                                    DBentry_i += 1; # next entry
                    elif (averaging == True) and (DBentry_i < len(temps)):
                        try:
                            currentdatetime = datetime.strptime(times[DBentry_i], '%Y-%m-%d %H:%M:%S.%f')
                        except:
                            print("Format of " + str(times[DBentry_i]) + " does not match %Y-%m-%d %H:%M:%S.%f - try without %f:")
                            currentdatetime = datetime.strptime(times[DBentry_i], '%Y-%m-%d %H:%M:%S')
                        finally:
                            if (date_i.date() < currentdatetime.date()):
                                try :
                                    prevminutes =  int((float(prevhours) % int(prevhours))*60.0);
                                except :
                                    prevminutes = 0;
                                try :
                                    prevseconds = int(((float(prevhours) % int(prevhours))*60.0 %  int((float(prevhours) % int(prevhours))*60.0))*60.0);
                                except :
                                    prevseconds = 0;
                                try :
                                    restofday = float((datetime(date_i.year, date_i.month, date_i.day, 23, 59, 59, 999999) - datetime(date_i.year, date_i.month, date_i.day, int(prevhours), prevminutes, prevseconds, 0)).seconds / 3600.);
                                except :
                                    print("ERROR")
                                    print("No more entry for " + str(date_i))
                                    print("Previous valid entry for current day was " + str(times[DBentry_i-1]))
                                    print("Next entry at " + str(times[DBentry_i]))
                                    print(prevhours)
                                    print("ZeroDivisionError? float modulo...")

                                try:
                                    avgtemp += prevtemp * restofday;
                                    prevhours += restofday;
                                except:
                                    print("exception: Skip NoneType entry in DB")
                                finally:
                                    DBentry_i+=1;
                                avgtemp = avgtemp/prevhours;
                                if (day_i > 0):
                                    date = str(int(time.mktime(date_i.timetuple()))) + "000"
                                    if date not in dates_in_file:
                                        outfile.write(date + '\t' + str(avgtemp) + '\n');
                                averaging = False;
                                day_i += 1;
                                date_i = start_date + timedelta(day_i);
                            elif (date_i.date() == currentdatetime.date()):
                                try:
                                    hours = (float(currentdatetime.hour) + float(currentdatetime.minute)/60. + float(currentdatetime.second/3600.))  - prevhours;
                                    prevhours = float(currentdatetime.hour) + float(currentdatetime.minute)/60. + float(currentdatetime.second/3600.);
                                    prevtemp = temps[DBentry_i];
                                    avgtemp += prevtemp * hours;
                                except:
                                    print("exception: Skip NoneType entry in DB")
                                finally:
                                    DBentry_i += 1;
                            else :
                                print("Startdate after first DBentry?")
                    else:
                        if (day_i > 0):
                            outfile.write(str(int(time.mktime(date_i.timetuple()))) + '000\t' + str(prevtemp) + '\n');
                        day_i += 1;
                        date_i = start_date + timedelta(day_i);
                date_i = start_date + timedelta(day_i);
                avgtemp = 0;
            print("%s has been written" % sensor_file_name)


def main(args):

    __sanity_checks(args)
    Path(args.output_directory).mkdir(parents=True, exist_ok=True)

    if args.first_fill and args.last_fill:
        start_date_timestamp = dbUtl.get_timestamps(args.first_fill)[0]
        end_date_timestamp = dbUtl.get_timestamps(args.last_fill)[-1]
        start_date = datetime.fromtimestamp(start_date_timestamp)
        end_date = datetime.fromtimestamp(end_date_timestamp)
        start_date = start_date.replace(hour=12, minute=0, second=0)
        end_date = end_date.replace(hour=12, minute=0, second=0)
    else:
        date_list = list(map(lambda x: int(x), args.start_date.split("-"))) + [12]
        start_date = datetime(*date_list)
        date_list = list(map(lambda x: int(x), args.end_date.split("-"))) + [12]
        end_date = datetime(*date_list)

    sensors_list = pyUtl.read_txt_file(args.sensor_names)

    # TODO: The output is so big that the output of cursor.fetchall() does not fit in memory!!!
    # Need to do it per chunks
    get_temperatures(args.output_directory, start_date, end_date, sensors_list)


if __name__ == "__main__":

    args = __get_arguments()
    main(args)
