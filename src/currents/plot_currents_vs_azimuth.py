from pathlib import Path

import pandas as pd
import ROOT

from utils import generalUtils as gUtl
import currents.helpers as currents_helper
import currents.plotting_helpers as plotting_helper
from utils.parserUtils import ArgumentParser, sanity_checks_leakage_current_flags
from utils.pythonUtils import dict_linear_combination
from utils.modules import ReadoutGroup
from utils.constants import CELSIUS_TO_KELVIN


ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(ROOT.kTRUE)
ROOT.gStyle.SetOptFit(0o001)
ROOT.gStyle.SetPadLeftMargin(0.15)
ROOT.gStyle.SetPadBottomMargin(0.15)


def __get_arguments():

    parser = ArgumentParser()
    parser.add_input_fills_flags(first_fill_required=True, last_fill_required=False)
    parser.add_leakage_current_flags()
    parser.add_layer_flag(default=1)
    parser.add_y_axis_range_flags(defaults=(0., 2000.))
    parser.add_argument(
        "-csv", "--produce_csv_files",
        help="Produce csv file with temperature and leakage current per sector",
        action="store_true",
    ) 
    parser.add_argument(
        "-csv_dir", "--csv_directory",
        help="Produce csv file with temperature and leakage current per sector",
        default="data/currents/per_sector"
    ) 

    args = parser.parse_args()
    sanity_checks_leakage_current_flags(args)
    return args


def __get_graph_vs_azimuth(quantity_per_readout_group, y_label, title, color,
                           marker_style, marker_size):

    x_label = "Azimuthal angle #Phi [rad]"

    azimuthal_angles = []
    y_values = []
    for readout_group_name, quantity in quantity_per_readout_group.items():
        readout_group = ReadoutGroup(readout_group_name)
        phi = readout_group.getAverageAzimuthalAngle()
        azimuthal_angles.append(phi)
        y_values.append(quantity)
        
    graph = gUtl.get_graph(azimuthal_angles, y_values, x_label, y_label, title)
    graph.SetLineColor(color)
    graph.SetMarkerColor(color)
    graph.SetMarkerStyle(marker_style)
    graph.SetMarkerSize(marker_size)
    return graph


def __plot_graphs(graph_minus_side, graph_plus_side, y_min, y_max,
                  text_top_left_corner, text_above_top_right_corner,
                  output_directory, figure_name, extensions):

    legend = ROOT.TLegend(0.8, 0.78, 0.9, 0.9)
    legend.SetNColumns(1)
    legend.SetFillColor(0)
    legend.SetFillStyle(0)
    legend.SetTextFont(42)
    legend.SetBorderSize(0)
    legend.SetTextSize(0.045)

    c = ROOT.TCanvas()
    c.cd()

    plotting_helper.set_font_size_and_offset(graph_plus_side)

    graph_plus_side.GetYaxis().SetRangeUser(y_min, y_max)
    graph_minus_side.GetYaxis().SetRangeUser(y_min, y_max)

    graph_plus_side.Draw("AP")
    graph_minus_side.Draw("Psame")

    legend.AddEntry(graph_plus_side, "+z", "P")
    legend.AddEntry(graph_minus_side, "-z", "P")
    legend.Draw("same")
 
    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextFont(61)
    latex.SetTextAlign(11)
    latex.DrawLatex(0.16, 0.92, "CMS");
    latex.SetTextFont(52)
    latex.DrawLatex(0.24, 0.92, "Preliminary");

    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextFont(42)
    latex.SetTextSize(0.045)
    latex.SetTextAlign(13)
    latex.DrawLatex(0.18, 0.88, text_top_left_corner);

    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextFont(42)
    latex.SetTextSize(0.04)
    latex.SetTextAlign(31)
    latex.DrawLatex(0.9, 0.92, text_above_top_right_corner);
   
    figure_base_name = output_directory + "/" + figure_name
    for extension in extensions:
        full_figure_name = figure_base_name + extension
        c.Print(full_figure_name)


def __build_output_file_name(
        sub_system,
        layer,
        normalize_to_number_of_rocs,
        normalize_to_volume,
        target_temperature,
        fill,
        fill2=None,
    ):

    if fill2 is None:
        output_name = "leakage_current_vs_azimuthal_angle_fill_%d" % (fill)
    else:
        output_name = "leakage_current_difference_vs_azimuthal_angle_fills_%d_%d" \
                      % (fill, fill2)

    output_name += "_%s" % sub_system
    output_name += "_layer_%s" % layer
    if normalize_to_number_of_rocs:
        output_name += "_perRoc"
    if normalize_to_volume:
        output_name += "_volumeNormalization"
    if target_temperature:
        output_name += "_correctedTo%dK" % target_temperature

    return output_name


def __produce_csv_file(data_per_readout_group, column_names, file_name):
    dataframes = []
    index_label = "readout_group"
    for data, column_name in zip(data_per_readout_group, column_names):
        df = pd.Series(data).to_frame(column_name)
        dataframes.append(df)
    df = pd.concat(dataframes, axis=1)
    df = df.rename_axis(index_label, axis=1)
    df.to_csv(file_name, index_label=index_label)
    print(f"{file_name} has been written.")


def __plot_leakage_current_vs_phi(
        fill,
        integrated_lumi,
        sub_system,
        layer,
        y_min,
        y_max,
        input_currents_directory,
        input_temperatures_directory,
        target_temperature,
        normalize_to_volume,
        normalize_to_number_of_rocs,
        output_directory,
        produce_csv_files,
        csv_directory,
        extensions=(".png", ".pdf", ".root"),
    ):

    base_args = (
        sub_system,
        layer,
        input_currents_directory,
        input_temperatures_directory,
        target_temperature,
        normalize_to_volume,
        normalize_to_number_of_rocs,
    )
    f = currents_helper.get_leakage_currents_and_temperatures_per_readout_group
    leakage_current_per_sector_minus_side, temperatures_per_sector_minus_side = f(fill, "m", *base_args)
    leakage_current_per_sector_plus_side, temperatures_per_sector_plus_side  = f(fill, "p", *base_args)

    labels_args = {
        "title": "",
        "y_label": plotting_helper.make_y_axis_title(
            text="I_{leak}",
            unit="#muA",
            target_temperature=target_temperature,
            normalize_to_volume=normalize_to_volume,
            normalize_to_number_of_rocs=normalize_to_number_of_rocs,
        ), 
    }
    graph_minus_side = __get_graph_vs_azimuth(
        leakage_current_per_sector_minus_side,
        color=ROOT.kBlue,
        marker_style=20,
        marker_size=1,
        **labels_args
    )
    graph_plus_side = __get_graph_vs_azimuth(
        leakage_current_per_sector_plus_side,
        color=ROOT.kRed,
        marker_style=21,
        marker_size=1,
        **labels_args
    )

    sub_system_text = "BPix" if sub_system == "Barrel" else "FPix"
    output_name =  __build_output_file_name(
        sub_system_text,
        layer,
        normalize_to_number_of_rocs,
        normalize_to_volume,
        target_temperature,
        fill,
    )

    if produce_csv_files:
        leakage_current_per_readout_group = {
            **leakage_current_per_sector_minus_side,
            **leakage_current_per_sector_plus_side,
        }
        temperatures_per_readout_group = {
            **temperatures_per_sector_minus_side,
            **temperatures_per_sector_plus_side,
        }
        data = (leakage_current_per_readout_group, temperatures_per_readout_group)
        column_names = (labels_args["y_label"], "sensor_temperature [K]")
        file_name = "%s/%s_data.csv" % (csv_directory, output_name)
        __produce_csv_file(data, column_names, file_name)

    text_top_left_corner = "Fill %d, %s Layer %s" % (fill, sub_system_text, layer)
    text_above_top_right_corner = "(%s) %s TeV - %.1f fb^{-1}" % ("2022", "13.6", integrated_lumi)
    __plot_graphs(graph_minus_side, graph_plus_side, y_min, y_max,
                  text_top_left_corner, text_above_top_right_corner,
                  output_directory, output_name, extensions)


def __plot_leakage_current_difference_vs_phi(
        first_fill,
        last_fill,
        sub_system,
        layer,
        y_min,
        y_max,
        input_currents_directory,
        input_temperatures_directory,
        target_temperature,
        normalize_to_volume,
        normalize_to_number_of_rocs,
        output_directory,
        produce_csv_files,
        csv_directory,
        extensions=(".png", ".pdf"),
    ):

    base_args = (
        sub_system,
        layer,
        input_currents_directory,
        input_temperatures_directory,
        target_temperature,
        normalize_to_volume,
        normalize_to_number_of_rocs,
    )

    f = currents_helper.get_leakage_currents_and_temperatures_per_readout_group
    leakage_current_reference_per_sector_minus_side, temperatures_ref_per_sector_minus_side = f(first_fill, "m", *base_args)
    leakage_current_reference_per_sector_plus_side, temperatures_ref_per_sector_plus_side  = f(first_fill, "p", *base_args)

    leakage_current_per_sector_minus_side, temperatures_per_sector_minus_side = f(last_fill, "m", *base_args)
    leakage_current_per_sector_plus_side, temperatures_per_sector_plus_side  = f(last_fill, "p", *base_args)

    leakage_current_difference_per_sector_minus_side = dict_linear_combination(
        leakage_current_per_sector_minus_side,
        leakage_current_reference_per_sector_minus_side,
        1,
        -1,
        reduce_to_common_keys=True,
    )
    leakage_current_difference_per_sector_plus_side = dict_linear_combination(
        leakage_current_per_sector_plus_side,
        leakage_current_reference_per_sector_plus_side,
        1,
        -1,
        reduce_to_common_keys=True,
    )

    labels_args = {
        "title": "",
        "y_label": plotting_helper.make_y_axis_title(
            text="#DeltaI_{leak}",
            unit="#muA",
            target_temperature=target_temperature,
            normalize_to_volume=normalize_to_volume,
            normalize_to_number_of_rocs=normalize_to_number_of_rocs,
        ), 
    }
    graph_minus_side = __get_graph_vs_azimuth(
        leakage_current_difference_per_sector_minus_side,
        color=ROOT.kBlue,
        marker_style=20,
        marker_size=1,
        **labels_args,
    )
    graph_plus_side = __get_graph_vs_azimuth(
        leakage_current_difference_per_sector_plus_side,
        color=ROOT.kRed,
        marker_style=21,
        marker_size=1,
        **labels_args,
    )

    sub_system_text = "BPix" if sub_system == "Barrel" else "FPix"
    output_name =  __build_output_file_name(
        sub_system_text,
        layer,
        normalize_to_number_of_rocs,
        normalize_to_volume,
        target_temperature,
        first_fill,
        last_fill,
    )
    
    if produce_csv_files:
        leakage_current_difference_per_readout_group = {
            **leakage_current_difference_per_sector_minus_side,
            **leakage_current_difference_per_sector_plus_side,
        }
        temperatures_ref_per_readout_group = {
            **temperatures_ref_per_sector_minus_side,
            **temperatures_ref_per_sector_plus_side,
        }
        temperatures_per_readout_group = {
            **temperatures_per_sector_minus_side,
            **temperatures_per_sector_plus_side,
        }
        data = (
            leakage_current_difference_per_readout_group,
            temperatures_ref_per_readout_group,
            temperatures_per_readout_group
        )
        column_names = (
            labels_args["y_label"],
            "sensor_temperature_fill_{first_fill} [K]",
            "sensor_temperature_fill_{last_fill} [K]"
        )
        file_name = "%s/%s_data.csv" % (csv_directory, output_name)
        __produce_csv_file(data, column_names, file_name)

    text_top_left_corner = f"Fills difference {last_fill}/{first_fill}, Layer {layer}"
    text_above_top_right_corner = "(%s) %s TeV" % ("2022", "13.6")
    __plot_graphs(graph_minus_side, graph_plus_side, y_min, y_max,
                  text_top_left_corner, text_above_top_right_corner,
                  output_directory, output_name, extensions)


def main(args):

    Path(args.output_directory).mkdir(parents=True, exist_ok=True)
    Path(args.csv_directory).mkdir(parents=True, exist_ok=True)

    bad_fills = gUtl.get_bad_fills(args.bad_fills_file_name)
    fills_info = gUtl.get_fill_info(args.input_fills_file_name)
    
    if args.last_fill is None:
        last_fill = args.first_fill
    else:
        last_fill = args.last_fill
    fills = gUtl.get_fills(fills_info, bad_fills, args.first_fill, last_fill)

    for fill in (args.first_fill, last_fill):
        if fill not in fills:
            print("Error: Fill %d is not in list of valid fills!" % fill)

    if args.target_temperature:
        target_temperature = float(args.target_temperature) + CELSIUS_TO_KELVIN
    else:
        target_temperature = None

    base_args = (
        args.sub_system,
        args.layer,
        args.ymin,
        args.ymax,
        args.input_currents_directory,
        args.input_temperatures_directory,
        target_temperature,
        args.normalize_to_volume,
        args.normalize_to_number_of_rocs,
        args.output_directory,
        args.produce_csv_files,
        args.csv_directory,
    )
    if args.last_fill is None:
        integrated_lumi = gUtl.get_integrated_lumi_per_fill(args.input_lumi_file_name)[args.first_fill]
        __plot_leakage_current_vs_phi(
            args.first_fill,
            integrated_lumi,
            *base_args,
        )
    else:
        __plot_leakage_current_difference_vs_phi(
            args.first_fill,
            args.last_fill,
            *base_args,
        )


if __name__ == "__main__":

    args = __get_arguments()
    main(args)
