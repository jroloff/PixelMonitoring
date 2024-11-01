# Run 3 monitoring commands

first_fill=8474
last_fill=9319

suffix=run3
sub_system=Barrel
#sub_system=EndCap

# This needs to be run from first till last fill in Run3
python src/fills_info/get_fills.py -suffix ${suffix} -ff ${first_fill} -lf ${last_fill}
python src/luminosity/get_integrated_luminosity.py -suffix ${suffix} -ff ${first_fill} -lf ${last_fill} -from oms

# This can be run for all fills, a small range of fills or just one
python src/currents/get_currents_from_database.py -i data/fills_info/fills_${suffix}.csv -ff ${first_fill} -lf ${last_fill} -s ${sub_system}
python src/currents/get_currents.py -ff ${first_fill} -lf ${last_fill} -s ${sub_system}
python src/temperatures/get_readout_group_temperatures.py -ff ${first_fill} -lf ${last_fill} -f data/fills_info/fills_${suffix}.csv -s Barrel

# This should be run for an era, a small range of fills or just one
era=run3
layers=1
base_args="-s ${sub_system} -era ${era} -f data/fills_info/fills_run3.csv -l data/luminosity/integrated_luminosity_per_fill_run3.csv"
python src/currents/plot_currents.py ${base_args} -layers ${layers} -ymin 0 -ymax 30 -x_axes lumi,fill -current leakage

# This can be run for all fills, a small range of fills or just one
fill=8395
base_args="-s ${sub_system} -ff ${fill} -f data/fills_info/fills_run3.csv -l data/luminosity/integrated_luminosity_per_fill_run3.csv"
python src/currents/plot_currents_vs_azimuth.py ${base_args} -ymin 0 -ymax 40 --layer 1
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ymin 0 -ymax 10 -normroc --layer 4
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ymin 0 -ymax 2000 -normvol
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ymin 0 -ymax 100 -tref 0
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ymin 0 -ymax 5000 -normvol -tref 0
