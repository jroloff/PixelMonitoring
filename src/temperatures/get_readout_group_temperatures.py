from pathlib import Path
import datetime as dt

from utils import generalUtils as gUtl
from utils.parserUtils import ArgumentParser
from utils.modules import ReadoutGroup
from temperatures.helpers import get_sensor_temperature


def __get_arguments():

    parser = ArgumentParser()
    parser.add_input_fills_file_flag()
    parser.add_input_fills_flags(first_fill_required=True, last_fill_required=True)
    parser.add_bad_fills_file_flag()
    parser.add_output_directory_flag(default_directory="data/temperatures/readout_group")
    parser.add_sub_system_flag()
    parser.add_measurement_delay_flag("temperature")

    return parser.parse_args()


# TODO: Put this in config
def __get_readout_group_names():
    readout_group_names = []
    for layer in range(1, 5):
        for half_cylinder in ("BpI", "BpO", "BmI", "BmO"):
            for sector in range(1, 9):
                readout_group_name = "BPix_%s_SEC%s_LYR%s" % (half_cylinder, sector, layer)
                readout_group_names.append(readout_group_name)

    return readout_group_names


def main(args):

    sub_system_directory = "BPix" if args.sub_system == "Barrel" else "FPix"
    output_directory = "%s/%s" % (args.output_directory, sub_system_directory)
    Path(output_directory).mkdir(parents=True, exist_ok=True)

    fills_info = gUtl.get_fill_info(args.input_fills_file_name)
    good_fills = fills_info.fill_number.to_list()
    readout_group_names = __get_readout_group_names()

    for fill in range(args.first_fill, args.last_fill+1):
        if not fill in good_fills: continue

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
        
        temperatures = {}
        for readout_group_name in readout_group_names:
            readout_group = ReadoutGroup(readout_group_name)
            sensor_temperature = get_sensor_temperature(
                readout_group,
                begin_time,
                measurement_time,
                correct_for_fluence=False,
            )
            temperatures[readout_group_name] = sensor_temperature

        temperature_file_name = "%s/%s.txt" % (output_directory, fill)
        sorting_function = lambda item: item[0][-1] + item[0]
        with open(temperature_file_name, "w+") as file:
            for key, temperature in sorted(temperatures.items(), key=sorting_function):
                file.write("%s %.4f\n" % (key, temperature))
                
        print("%s has been written." % temperature_file_name)


if __name__ == "__main__":

    args = __get_arguments()
    main(args)
