import os
import argparse

from utils import pixelDesignUtils as designUtl
from utils import eraUtils as eraUtl
from utils import pythonUtils as pyUtl


def __get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i", "--input_directory_name",
        help="Input directory containing currents files, default=%(default)s",
        required=False,
        default="data/currents/from_database",
    )
    parser.add_argument(
        "-o", "--output_directory",
        help="Output directory name, default=%(default)s",
        required=False,
        default="data/currents/processed",
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

    return parser.parse_args()


def main(args):

    if not os.path.exists(args.output_directory):
        os.makedirs(args.output_directory)

    for fill in range(args.first_fill, args.last_fill+1):

        phase = eraUtl.get_phase_from_fill(fill)
        if phase != 1:
            raise NotImplementedError

        allowed_layers = designUtl.get_layer_names(phase) + designUtl.get_disk_names(phase)

        # Read input file
        currents_file = args.input_directory_name + "/" + str(fill) + "_" + args.sub_system + ".txt"
        if not os.path.exists(currents_file):
            continue
        lines = pyUtl.read_txt_file(currents_file)

        # Book dictionaries to read currents
        hv_currents = {}
        analog_currents = {}
        digital_currents = {}

        # Open output files
        prefix = args.output_directory + "/" + str(fill) + "_" + args.sub_system
        hv_currents_file_name = prefix + "_HV_ByLayer.txt"
        analog_currents_file_name = prefix + "_Ana.txt"
        digital_currents_file_name = prefix + "_Dig.txt"

        # Open output files
        hv_currents_file = open(hv_currents_file_name, "w")
        analog_currents_file = open(analog_currents_file_name, "w")
        digital_currents_file = open(digital_currents_file_name, "w")

        # Fill in output files
        for line in lines:
            omds_channel_name, current, _, _, _ = line.split()
            omds_readout_group_name, channel_name = omds_channel_name.split("/")
            channel = int(channel_name[-1])
            current = float(current)

            # There are aliases of the sectors names for phase-0 and phase-1
            # which creates problems, get rid of them using allowed_layers.
            layer = designUtl.get_layer_name_from_cable_name(omds_channel_name)
            if layer not in allowed_layers:
                continue

            if channel == 0:
                digital_currents[omds_readout_group_name] = current

            elif channel == 1:
                analog_currents[omds_readout_group_name] = current

            elif channel in (2, 3):
                readout_group_name = designUtl.get_readout_group_name_from_omds_leakage_current_cable_name(omds_channel_name, phase=phase)
                hv_currents[readout_group_name] = current
            
                # TODO: Not sure this code is actually doing what one wants
                #       It seems the current is per "PixelEndCap_BpI_D1", is this
                #       a FPix readout group?
                if("_D1_" in line and ("channel002" in line or "channel003" in line)):
                    hv_currents[omds_channel_name.rsplit('1_')[0].strip()+ "1"] = current
                elif("_D2_" in line and ("channel002" in line or "channel003" in line)):
                    hv_currents[omds_channel_name[0].rsplit('2_')[0].strip()+ "2"] = current
                elif("_D3_" in line and ("channel002" in line or "channel003" in line)):
                    hv_currents[omds_channel_name[0].rsplit('3_')[0].strip()+ "3"] = current

            else:
                raise ValueError(f"Invalid channel {channel} in OMDS channel name {omds_channel_name}")

        currents_types = (hv_currents, analog_currents, digital_currents)
        files = (hv_currents_file, analog_currents_file, digital_currents_file)
        sorting_function = lambda item: item[0][-1] + item[0]
        for currents, file in zip(currents_types, files):
            for key, current in sorted(currents.items(), key=sorting_function):
                file.write("%s %.4f\n" % (key, current))

        hv_currents_file.close()
        digital_currents_file.close()
        analog_currents_file.close()

        file_names = (hv_currents_file_name, analog_currents_file_name, digital_currents_file_name)
        for file_name in file_names:
            print(f"{file_name} has been saved.")
        print("")


if __name__ == "__main__":

    args = __get_arguments()
    main(args)
