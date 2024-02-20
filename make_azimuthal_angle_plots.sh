#!/bin/bash

sub_system=Barrel
base_args="-s ${sub_system} -f data/fills_info/fills_run3.csv -l data/luminosity/integrated_luminosity_per_fill_run3.csv"

#fill=8395
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ff ${fill} -ymin 0 -ymax 100 -normroc -tref 0 --layer 1
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ff ${fill} -ymin 0 -ymax 40 -normroc --layer 1
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ff ${fill} -ymin 0 -ymax 40 -normroc --layer 2
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ff ${fill} -ymin 0 -ymax 15 -normroc --layer 3
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ff ${fill} -ymin 0 -ymax 10 -normroc --layer 4

fill=7920
python src/currents/plot_currents_vs_azimuth.py ${base_args} -ff ${fill} -ymin -10 -ymax 2 -normroc --layer 1
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ff ${fill} -ymin 0 -ymax 40 -normroc --layer 1
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ff ${fill} -ymin 0 -ymax 40 -normroc --layer 2
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ff ${fill} -ymin 0 -ymax 15 -normroc --layer 3
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ff ${fill} -ymin 0 -ymax 10 -normroc --layer 4

#fill1=7920
#fill=8395
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ff ${fill1} -lf ${fill} -ymin 0 -ymax 40 -normroc --layer 1
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ff ${fill1} -lf ${fill} -ymin 0 -ymax 20 -normroc --layer 2
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ff ${fill1} -lf ${fill} -ymin 0 -ymax 8 -normroc --layer 3
#python src/currents/plot_currents_vs_azimuth.py ${base_args} -ff ${fill1} -lf ${fill} -ymin 0 -ymax 5 -normroc --layer 4
