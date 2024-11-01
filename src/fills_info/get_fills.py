import argparse
from pathlib import Path

import pandas as pd
import datetime as dt

from omsapi import OMSAPI


def __get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o", "--output_directory",
        help="Output directory name. Default=%(default)s",
        required=False,
        default="data/fills_info/",
    )
    parser.add_argument(
        "-suffix", "--output_file_name_suffix",
        help="Output file name. Default=\"\"",
        required=False,
        default="",
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

    return parser.parse_args()


def __get_data(first_fill, last_fill, attributes):
    omsapi = OMSAPI("https://cmsoms.cern.ch/agg/api", "v1", cert_verify=False)
    omsapi.auth_krb()
    
    # Create a query.
    query = omsapi.query("fills")
    query.set_verbose(False)

    query.attrs(attributes)
    query.filter("fill_number", first_fill, "GE")
    query.filter("fill_number", last_fill, "LE")
    # TODO: Why doing this
    for fill in range(3474, 3564):
        query.filter("fill_number", fill, "NEQ")

    query.filter("stable_beams", "true", "EQ")
    query.filter("start_stable_beam", "null", "NEQ")
    query.filter("end_stable_beam", "null", "NEQ")
    query.filter("delivered_lumi", "null", "NEQ")
    query.filter("delivered_lumi", 0, "GT")
    query.filter("injection_scheme", "null", "NEQ")

    query.paginate(1, per_page=last_fill-first_fill+1)
    
    data = pd.json_normalize(query.data().json()["data"])

    mapping = {
        x: x.replace("attributes.", "")
        for x in data.columns
    }
    data.rename(columns=mapping, inplace=True)
    data = data[attributes]

    return data


def __format_time(data, column_names):
    time_mask = "%Y-%m-%d %H:%M:%S.%f"
    func = lambda x: dt.datetime.fromisoformat(x.replace("Z", "+00:00")).strftime(time_mask)
    for column_name in column_names:
        data[column_name] = data[column_name].apply(func)
    return data
    

def main():

    args = __get_arguments()
    Path(args.output_directory).mkdir(parents=True, exist_ok=True)

    attributes = ["delivered_lumi", "fill_number", "start_stable_beam", "end_stable_beam"]
    data = __get_data(args.first_fill, args.last_fill, attributes)
    data = __format_time(data, ("start_stable_beam", "end_stable_beam"))
    data.drop(columns="delivered_lumi", inplace=True)
    
    suffix = (len(args.output_file_name_suffix) > 0) * "_" + args.output_file_name_suffix
    output_file_name = args.output_directory + "/" + "fills" + suffix  + ".csv"
    data.to_csv(output_file_name, index=False, columns=["fill_number", "start_stable_beam", "end_stable_beam"])
    print(f"{output_file_name} was written.")


if __name__ == "__main__":
   main()
