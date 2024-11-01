# Pixel monitoring tools

## Installation
To simplify the environment setting, we advise to install the code on `lxplus` or anywhere else where you have access to `cvmfs` (see Section `Setup environment`)
```bash
git clone git@github.com:fleble/PixelMonitoring.git
source setup.sh
```


## Setup environment
After every new login, if you do not use `brilcalc`, do:
```bash
source setenv.sh
```
This can be unset only with a new login. 
This will only work if you have access to `cvmfs`.

The following commands are not strictly needed, but may be helpful to setup the environment in the future.    
For using `brilcalc`, do:
```bash
source brilwsenv.sh
```
This is automatically done in `setenv.sh`.
You can unset this setup by doing:
```bash
source unset_brilwsenv.sh
```


## Overview and decription of all scripts

This repo has three objectives:
1- The monitoring of the Pixel Tracker detector (temperatures, currents etc...): "monitoring tools"    
2- The analysis of the leakage current: "leakage current analysis"    
3- The preparation of the radiation profile for the radiation damage simulation: "radiation profile"    

Here is a description of the different directories in this repo (some are created after running `source setup.sh` or running the code):
* `src/` contains all the source code
* `config/` contains several configuration information: detector geometry, cooling loops names, temperature sensor names etc...needed as input of the code.
* `data/` contains some input for the code (e.g. bad fills information, FLUKA ASSCI file should also be put there) and all output data: luminosity, temperatures, currents, fluence, radiation profiles...
* `plots/` contains all the produced plots
* `external/` contains external libraries, for now only the CMS OMS API
* `credentials/` contains the necessary credentials to access the `cms_omds_adg` Oracle database (not comitted to this directory, ask for the credentials).


## Running the monitoring tools and leakage current analysis

Commands for Run 3 are available in `run3.sh`. The following scripts must be run:
* `src/fills_info/get_fills.py`
* `src/luminosity/get_integrated_luminosity.py`
* `src/currents/get_currents_from_database.py`
* `src/currents/get_currents.py`
* `src/temperatures/get_readout_group_temperatures.py`
* `src/currents/plot_currents.py`
* `src/currents/plot_currents_vs_azimuth.py`

An extensive description of the different scripts can be found below.


## Producing radiation profile

Commands for the different data-taking periods can be found in
`produceRadSimProfileFragments.sh`, `mergeRadSimProfileFragments.sh`, and `mergeRadSimProfileYears.sh`.

They use the following scripts:
* `src/radiation_simulation/prepare_profile.py`
* `src/radiation_simulation/merged_profile.py`

As producing the radiation profile is a long process, the idea of the scripts above is to prepare profiles for different subsets of the data-taking period in parallel and them stitched together.


## Detailed description of the scripts

For all scripts, learn about its usage with `python script.py -h`.

| Script      | Description |
| :---------- | :---------- |
| `src/fills_info/get_fills.py`                 | Reads stable beam start and stop timestamps using CMS OMS API for requested fills, listing only good fills, and writes to an output file (default in `data/fills_info/fills.csv`). |
| `src/luminosity/get_integrated_luminosity.py` | Reads instantaneous and integrated lumi from either `brilcalc` or OMS and writes it to an output file (default `data/luminosity/integrated_luminosity_per_fill.csv`). |
| `src/currents/get_currents_from_database.py`  | Reads the currents from the `cms_omds_adg` Oracle database and write one file per fill in `data/currents/from_database/`. |
| `src/currents/get_currents.py`                | Reads currents from database and writes digital, analog, analog per ROC and HV per ROC currents (default in `data/currents/processed/`). |
| `src/temperatures/get_readout_group_temperatures.py`| Reads temperatures per readout group from the `cms_omds_adg` Oracle database, correcting for self-heating and fluence, and writes one file per fill (default in `data/temperatures/readout_group/`). |
| `src/temperatures/getPLCAirTemperatures.py`   | Reads temperatures from the `cms_omds_adg` Oracle database and writes one file per fill (default in `data/temperatures/air/`). |
| `src/annealing_temperatures/getAnnealingTemperatures.py`| Reads temperatures from the `cms_omds_adg` Oracle database and writes one file per temperature sensor, each row with the average temperature of one day (default in `data/temperatures/annealing/`). |
| `src/temperatures/plotTemperatures.py`        | Plot temperatures from output of `getPLCAirTemperatures.py`. |
| `src/fluence/getFluenceField.py`              | Reads ASCII FLUKA file, creates txt files with equivalent information (default in `data/fluence/txt_files/`) and creates a ROOT file with the 2D fluence field histogram `F(r, z)` for different particles (default `data/fluence/*.root`). Units are stored in a txt file (default `data/fluence/*_units.txt`). |
| `src/fluence/getFluence.py`                   | Reads all particles fluence field from ROOT file for given coordinates `r` and `z` and outputs the fluence. |
| `src/fluence/fitFluenceField.py`              | Fit the all particles fluence field from output of `getFluenceField.py`. Example usage in `src/fluence/fitFluenceField.sh`. Original code from Dannyl's, never tested, probably broken. |
| `src/current/plot_currents.py`                | Plot digital, analog, analog per ROC and leakage current from output of `getCurrents.py` versus integrated lumi, fill number or fluence. Default output: `data/plots/currents`. Different normalizations of the leakage current are available: per ROC, per sensor volume or both. The leakage current can be corrected to a reference temperature. |
| `src/current/plot_currents_vs_azimuth.py`     | Plot leakage current from output of `getCurrents.py` as a function of the azimuthal angle. Default output: `data/plots/currents`. Different normalizations of the leakage current are available: per ROC, per sensor volume or both. The leakage current can be corrected to a reference temperature. Example usage in `make_azimuthal_angle_plots.sh`. |
| `src/radiation_simulation/prepare_profile.py` | Prepare radiation profile with `Fill`, `Timestamp [s]`, `Duration [s]`, `Temperature [K]`, `Fluence [n_eq/cm2/s]`, and `Leakage_current [mA/cm2]`. Temperature, fluence and leakage current data are not read from the `cms_omds_adg` Oracle database, lumi is read from `brilcalc`. Example usage in `produceRadSimProfileFragments.sh`. |
| `src/radiation_simulation/merged_profile.py` | Merge radiation profiles. This is particularly useful as making a profile takes a long time, so one can make several profiles in parallel in merge them at the end. Example usage in `mergeRadSimProfileFragments.sh` and `mergeRadSimProfileYears.sh`. |

