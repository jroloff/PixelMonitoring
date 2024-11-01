from pathlib import Path
import io
import functools
import argparse

import numpy as np
import pandas as pd

from omsapi import OMSAPI
from utils import pythonUtils as pyUtl


def __get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o", "--output_directory",
        help="Output directory name. Default=%(default)s",
        required=False,
        default="data/luminosity/",
    )
    parser.add_argument(
        "-suffix", "--output_file_name_suffix",
        help="Output file name. Default=\"\"",
        required=False,
        default="",
    )
    parser.add_argument(
        "-ff", "--first_fill",
        help="First fill number to analyse. Must be greater than 1005.",
        type=int,
        required=False,
        default=1005,
    )
    parser.add_argument(
        "-lf", "--last_fill",
        help="Last fill number to analyse",
        type=int,
        required=True,
    )
    parser.add_argument(
        "-from", "--from",
        dest="source",
        help="Luminosity source. Choices=%(choices)s. Default=%(default)s.",
        choices=["oms", "brilcalc"],
        default="oms",
        required=False,
    )

    return parser.parse_args()


def __run_sanity_checks(args):
    assert args.first_fill >= 1005
    assert args.first_fill <= args.last_fill


def get_lumi_from_brilcalc(fill_begin, fill_end):
    bash_command = ("brilcalc lumi --begin {begin} --end {end} " \
                   + "-u /ub --output-style csv ").format(
            begin=fill_begin,
            end=fill_end,
        )
    output = pyUtl.run_bash_command(bash_command).split("\n")[1:-3]
    output[0] = output[0][1:]
    output = functools.reduce(lambda x, y: x + "\n" + y, output)

    df = pd.read_csv(io.StringIO(output))
    df["fill"] = df["run:fill"].apply(lambda x: x.split(":")[1])
    df.drop(labels=["run:fill", "time", "nls", "ncms"], axis=1, inplace=True)
    df = df.groupby("fill").sum()
    df.reset_index(inplace=True)

    return df


def get_lumi_from_oms(first_fill, last_fill):
    omsapi = OMSAPI("https://cmsoms.cern.ch/agg/api", "v1", cert_verify=False)
    omsapi.auth_krb()
    
    # Create a query.
    query = omsapi.query("fills")
    query.set_verbose(False)

    attributes = [
        "recorded_lumi",
        "delivered_lumi",
        "fill_number",
        "start_stable_beam",
        "end_stable_beam",
    ]
    query.attrs(attributes)
    query.include("meta")
    query.filter("fill_number", first_fill, "GE")
    query.filter("fill_number", last_fill, "LE")
    query.filter("delivered_lumi", "null", "NEQ")
    query.filter("delivered_lumi", 0, "GT")

    query.paginate(1, per_page=last_fill-first_fill+1)
    
    data = pd.json_normalize(query.data().json()["data"])

    mapping = {}
    for column_name in data.columns:
        if column_name == "attributes.fill_number":
            mapping[column_name] = "fill"
        elif column_name.startswith("attributes."):
            mapping[column_name] = column_name.replace("attributes.", "")
        elif column_name.startswith("meta.row."):
            _, _, attribute_name, meta_info = column_name.split(".")
            if meta_info == "units" and attribute_name in attributes:
                mapping[column_name] = attribute_name + "_unit"

    data.rename(columns=mapping, inplace=True)
    data = data[mapping.values()]

    return data


def unit_to_factor(unit_name):
    dict_ = {
        "fb^{-1}": 1e+15,
        "pb^{-1}": 1e+12,
        "{\\mu}b^{-1}": 1e+6,
        "mb^{-1}": 1e+3,
        "b^{-1}": 1,
    }
    return dict_[unit_name]


def cast_lumi_to_inverse_fb(df):
    # From brilcalc:
    if "delivered(/ub)" in df.columns:
        lumi_column_names = ["delivered(/ub)", "recorded(/ub)"]
        df["delivered (/fb)"] = df["delivered(/ub)"] * 1e-9
        df["recorded (/fb)"] = df["recorded(/ub)"] * 1e-9

    # From OMS:
    else:
        lumi_column_names = ["delivered_lumi", "recorded_lumi"]
        for lumi_column_name in lumi_column_names:
            unit_column_name = lumi_column_name + "_unit"
            unit_factor = df[unit_column_name].apply(unit_to_factor)
            lumi_in_inverse_fb = df[lumi_column_name] * unit_factor * 1e-15
            new_lumi_column_name = lumi_column_name.replace("_lumi", "") + " (/fb)"
            df[new_lumi_column_name] = lumi_in_inverse_fb

    df.drop(labels=lumi_column_names, axis=1, inplace=True)

    return df


def add_integrated_lumi(df):
    df["integrated delivered (/fb)"] = np.cumsum(df["delivered (/fb)"])
    df["integrated recorded (/fb)"] = np.cumsum(df["recorded (/fb)"])
    return df


def main(args):

    __run_sanity_checks(args)
    Path(args.output_directory).mkdir(parents=True, exist_ok=True)
    
    if args.source == "oms":
        df = get_lumi_from_oms(args.first_fill, args.last_fill)
    else:
        df = get_lumi_from_brilcalc(args.first_fill, args.last_fill)

    df = cast_lumi_to_inverse_fb(df)
    df = add_integrated_lumi(df)

    suffix = (len(args.output_file_name_suffix) > 0) * "_" + args.output_file_name_suffix
    output_file_name = args.output_directory + "/" + "integrated_luminosity_per_fill" + suffix + ".csv"
    columns_to_save = [
        "fill",
        "delivered (/fb)",
        "recorded (/fb)",
        "integrated delivered (/fb)",
        "integrated recorded (/fb)",
    ]
    df.to_csv(output_file_name, columns=columns_to_save, index=False)
    print("%s was written" % output_file_name)


if __name__ == "__main__":

    args = __get_arguments()
    main(args)
