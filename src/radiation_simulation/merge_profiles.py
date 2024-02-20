import os
from argparse import ArgumentParser

from radiation_simulation.prepare_profile import PROFILE_FORMAT


def __get_arguments():
    parser = ArgumentParser()

    parser.add_argument(
        "-i", "--input_directory",
        help="Input directory with profiles files.",
    )
    parser.add_argument(
        "-o", "--output_profile",
        help="Output profile file.",
    )

    return parser.parse_args()


def parse_profile(profile_file):
    lines = list(map(lambda x: x.split(), profile_file.readlines()[1:]))
    profile_file.seek(0)
    return lines


def insert_profile(profile, merged_profile):
    parsed_profile = parse_profile(profile)

    ts_col = 1 # timestamp column number

    if len(merged_profile) == 0:
        return parsed_profile
    
    if len(parsed_profile) == 0:
        return merged_profile

    if int(merged_profile[-1][ts_col]) < int(parsed_profile[0][ts_col]):
        merged_profile = merged_profile + parsed_profile

    elif int(merged_profile[0][ts_col]) > int(parsed_profile[-1][ts_col]):
        merged_profile = parsed_profile + merged_profile

    else:
        if int(parsed_profile[0][ts_col]) < int(merged_profile[0][ts_col]):
            idx1 = 0
        else:
            for idx1, line in enumerate(merged_profile):
                if int(line[ts_col]) >= int(parsed_profile[0][ts_col]):
                    break

        if int(parsed_profile[-1][ts_col]) >= int(merged_profile[-1][ts_col]):
            idx2 = len(merged_profile)
        else:
            for idx2, line in enumerate(merged_profile):
                if int(line[ts_col]) > int(parsed_profile[-1][ts_col]):
                    break

        merged_profile = merged_profile[:idx1] + parsed_profile + merged_profile[idx2:]

    return merged_profile


def main():
    args = __get_arguments()
    profile_names = [os.path.join(args.input_directory, f) \
                for f in os.listdir(args.input_directory) \
                if os.path.isfile(os.path.join(args.input_directory, f))]

    with open(profile_names[0], "r") as profile:
        header = profile.readlines()[0]
        profile.seek(0)
        merged_profile = parse_profile(profile)

    for profile_name in profile_names[1:]:
        with open(profile_name, "r") as profile:
            merged_profile = insert_profile(profile, merged_profile)

    output_file = open(args.output_profile, "w")
    output_file.write(header)
    for line in merged_profile:
        line = list(map(lambda x: float(x), line))
        output_file.write((PROFILE_FORMAT % tuple(line)) + "\n")

    print(f"{args.output_profile} has been written.")


if __name__ == "__main__":
    main()
