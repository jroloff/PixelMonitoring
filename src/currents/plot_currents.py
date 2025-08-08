from pathlib import Path

import numpy as np
import ROOT

from utils import generalUtils as gUtl
import currents.helpers as currents_helper
import currents.plotting_helpers as plotting_helper
from utils.parserUtils import ArgumentParser, sanity_checks_leakage_current_flags
from utils import eraUtils as eraUtl
from utils.constants import *
import utils.DrawingFunctions as df


def __get_arguments():
    parser = ArgumentParser()
    parser.add_input_fills_flags(first_fill_required=False, last_fill_required=False)
    parser.add_leakage_current_flags()
    parser.add_layers_flag(default="1,2,3,4")
    parser.add_argument(
        "-era", "--era",
        help="Era to analyse",
    ),
    parser.add_argument(
        "-current", "--current_type",
        help="Current type to plot, default=%(default)s",
        default="leakage",
        choices=["leakage", "digital", "analog", "analog_per_roc"],
    ),
    parser.add_argument(
        "-x_axes", "--x_axes",
        help="x-axis to plot against, default=%(default)s. "
             "Can be a comma-separated list of the following keywords: "
             "lumi, fill, fluence",
        default="lumi",
    ),
    parser.add_y_axis_range_flags(defaults=(0., 40.))

    args = parser.parse_args()
    sanity_checks_leakage_current_flags(args)
    return args


def __do_sanity_checks(args):
    assert (args.first_fill and args.last_fill) or args.era
    assert (args.first_fill and args.last_fill) != args.era


def __get_average_leakage_current_per_fill_per_layer(
        fills,
        z_side,
        layers,
        sub_system,
        input_currents_directory,
        input_temperatures_directory,
        target_temperature,
        normalize_to_volume,
        normalize_to_number_of_rocs,
    ):

    f = currents_helper.get_average_leakage_current_per_layer
    base_args = {
        "z_side": z_side,
        "sub_system": sub_system,
        "currents_directory": input_currents_directory,
        "temperatures_directory": input_temperatures_directory,
        "target_temperature": target_temperature,
        "normalize_to_unit_volume": normalize_to_volume,
        "normalize_to_number_of_rocs": normalize_to_number_of_rocs,
    }

    average_leakage_currents = {}
    for fill in fills:
        average_leakage_currents[fill] = {}
        for layer in layers:
            average_leakage_current = f(fill, layer=layer, **base_args)
            average_leakage_currents[fill][layer] = average_leakage_current

    return average_leakage_currents


def __get_multi_graph(
        currents,
        fills,
        integrated_lumi_per_fill,
        average_fluence_per_layer,
        plotType, 
        Xaxis,
    ):

    x_label = "Fill Number"
    y_label = "Leakage current I [#mu A / cm^{3}]"

    lumi = np.array([integrated_lumi_per_fill[fill] for fill in fills])
    layers = list(currents[fills[0]].keys())

    colors = [ROOT.kBlue+2, ROOT.kCyan+1, ROOT.kTeal+4, ROOT.kRed+1]
    marker_styles = [20, 21, 22, 23]

    x = {}
    y = {}

    if Xaxis == "lumi":
        for layer in layers:
            x[layer] = lumi

    elif Xaxis == "fluence": 
        for layer in layers:
            x[layer] = lumi * average_fluence_per_layer[layer]

    elif Xaxis == "fill": 
        for layer in layers:
            x[layer] = np.array(fills)

    if plotType == "leakage":
        for layer in layers:
            y[layer] = np.array([currents[f][layer] for f in fills]) if layer in currents[fills[0]].keys() else None

    i_leak_lumi = ROOT.TMultiGraph("mg", "")
    
    for idx, layer in enumerate(y.keys()):
        graph = gUtl.get_graph(x[layer], y[layer], x_label, y_label, "Layer " + layer)
        plotting_helper.set_font_size_and_offset(graph)
        graph.SetLineColor(colors[idx])
        graph.SetMarkerColor(colors[idx])
        graph.SetMarkerStyle(marker_styles[idx])
        graph.SetMarkerSize(0.8)
        i_leak_lumi.Add(graph)
 

    return i_leak_lumi


def __plot_currents(output_directory, settings, currents, fluence, 
                    fills, integrated_lumi_per_fill, curTypeObj, Xaxis,
                    text):

    text_size = 0.043

    c = df.setup_canvas(name="")
    c.cd()
    legEdges = settings["legend_coordinates"]
    leg = ROOT.TLegend(legEdges[0], legEdges[1], legEdges[2], legEdges[3])
    ROOT.SetOwnership(leg,0)
     
    graph = __get_multi_graph(currents, fills, integrated_lumi_per_fill, fluence, curTypeObj, Xaxis)
    ROOT.SetOwnership(graph, 0)

    if Xaxis=="lumi":
        x_label = "Integrated luminosity [fb^{-1}]"
    elif Xaxis=="fill":
        x_label = "Fill number"
    elif Xaxis=="fluence":
        x_label = "Total fluence #Phi [1 MeV Neutron Equivalent]"

    graph.GetXaxis().SetTitle(x_label)
    graph.GetYaxis().SetTitle(settings["y_label"])
    graph.GetYaxis().SetRangeUser(settings["y_range"][0], settings["y_range"][1])
    plotting_helper.set_font_size_and_offset(graph)

    graph.Draw("AP")
  
    df.draw_cms_details(labels=["(%s) %s TeV" % ("2022", "13.6"), settings["sub_system_text"], settings["current_text"], text],x_pos= 0.53,y_pos = 0.87, dy = 0.04, text_size = 0.035, sampleName="", cmsLabel = "Internal", padHeight = 1.0)

    leg.SetNColumns(1)
    leg.SetFillColor(0)
    leg.SetFillStyle(0)
    leg.SetTextFont(42)
    leg.SetBorderSize(0)
    leg.SetTextSize(text_size)

    leg.AddEntry(graph.GetListOfGraphs()[0], "Layer 1","P")

    leg.Draw("same")

    figure_name = output_directory + "/" + settings["base_output_file_name"]
    if Xaxis == "lumi":
        figure_name += "_vs_integrated_lumi"
    elif Xaxis == "fill":
        figure_name += "_vs_fill_number"
    elif Xaxis=="fluence":
        figure_name += "_vs_fluence"

    extensions = [".pdf"]
    for extension in extensions:
        c.Print(figure_name + extension)


def main(args):

    __do_sanity_checks(args)
    Path(args.output_directory).mkdir(parents=True, exist_ok=True)

    sub_system = args.sub_system
    era = args.era or str(args.first_fill) + "_" + str(args.last_fill)
    layers = args.layers.split(",")
    n_layers = len(layers)
    x_axes = args.x_axes.split(",")

    bad_fills = gUtl.get_bad_fills(args.bad_fills_file_name)

    # TODO: Where are these hard-coded numbers come from?
    # TODO: Add unit in comment
    fluence = {
        "1": 3.850588e+12,
        "2": 1.634252e+12,
        "3": 1.023023e+12,
    }

    fills_info = gUtl.get_fill_info(args.input_fills_file_name)
    fills = gUtl.get_fills(fills_info, bad_fills, args.first_fill, args.last_fill, args.era)
    integrated_lumi_per_fill = gUtl.get_integrated_lumi_per_fill(args.input_lumi_file_name)

    if args.current_type == "leakage":
        current = __get_average_leakage_current_per_fill_per_layer(
            fills,
            None,
            layers,
            sub_system,
            args.input_currents_directory,
            args.input_temperatures_directory,
            args.target_temperature,
            args.normalize_to_volume,
            args.normalize_to_number_of_rocs,
        )
    else:
        #TODO: Implement other currents
        raise NotImplementedError
    
    y_range = (args.ymin, args.ymax)
    legend_coordinates = (0.17, 0.87-0.05*n_layers, 0.35, 0.87)

    plotting_settings = {
        "digital": {
            "y_label": plotting_helper.make_y_axis_title(
                text="I_{digital}",
                unit="A",
            ), 
            "base_output_file_name": "I_dig_" + era,
            "legend_coordinates": legend_coordinates,
            "y_range": y_range,
            "sub_system_text": "CMS " + args.sub_system + " Pixel Detector",
            "current_text": "Digital Current",
        },
        "analog": {
            "y_label": plotting_helper.make_y_axis_title(
                text="I_{analog}",
                unit="A",
            ), 
            "base_output_file_name": "I_ana_" + era,
            "legend_coordinates": legend_coordinates,
            "y_range": y_range,
            "sub_system_text": "CMS " + args.sub_system + " Pixel Detector",
            "current_text": "Analog Current",
        },
        "analog_per_roc": {
            "y_label": plotting_helper.make_y_axis_title(
                text="I_{analog}/ROC",
                unit="A",
            ), 
            "base_output_file_name": "I_ana_perRoc_" + era,
            "legend_coordinates": legend_coordinates,
            "y_range": y_range,
            "sub_system_text": "CMS " + args.sub_system + " Pixel Detector",
            "current_text": "Analog Current",
        },
        "leakage": {
            "y_label": plotting_helper.make_y_axis_title(
                text="I_{leak}",
                unit="#muA",
                target_temperature= args.target_temperature,
                normalize_to_volume= args.normalize_to_volume,
            ), 
            "base_output_file_name": "i_leak_" + era,
            "legend_coordinates": legend_coordinates,
            "y_range": y_range,
            "sub_system_text": "CMS " + args.sub_system + " Pixel Detector",
            "current_text": "Leakage Current",
        },
    }

    text = eraUtl.get_date_from_era(args.era) if args.era else ""

    for x_axis in x_axes:
        settings = plotting_settings[args.current_type]
        __plot_currents(
            args.output_directory, settings, current, fluence, fills,
            integrated_lumi_per_fill, args.current_type, x_axis, text,
        )


if __name__ == "__main__":

    args = __get_arguments()
    main(args)
