#!/bin/bash

year=2022
rog=BPix_BmI_SEC1_LYR1

time_flags='-di 1200 -df 1200 -tsi 3600 -tsf 3600'

profile_directory=data/radiation_simulation/profiles/fragments


if [ "$year" == "2015" ]; then
    fill_info=data/fills_info/all_fills.csv
    ranges=(
        3819 3850 3900 3950 4000 4050
        4100 4150 4200 4250 4300 4350
        4400 4450 4500 4550 4600 4647
    )

elif [ "$year" == "2016" ]; then
    fill_info=data/fills_info/all_fills.csv
    ranges=(
        4851 4900 4950 5000 5050 5100
        5150 5200 5250 5300 5350 5400
        5456
    )
    
elif [ "$year" == "2017" ]; then
    fill_info=data/fills_info/all_fills.csv
    ranges=(
        5659 5700 5750 5830 5900
        5950 5600 5650 5700 5750 5800
        5850 5890 5940 5980 6030 6070 6100
        6150 6200 6250 6300 6350 6400
        6467
    )
    
elif [ "$year" == "YETS20172018" ]; then
    fill_info=data/fills_info/all_fills.csv
    # 10 days: 864000
    # 1 day: 86400
    time_flags='-di 1200 -df 1200 -tsi 86400 -tsf 3600'
    ranges=(6432 6570)

elif [ "$year" == "2018" ]; then
    fill_info=data/fills_info/all_fills.csv
    ranges=(
        6550 6600 6650 6600 6650 6700
        6740 6780 6850 6880 6920 6950
        7010 7050 7080 7110 7140 7215
        7240 7270 7300 7330 7410 7450
        7492
    )

elif [ "$year" == "2022" ]; then
    fill_info=data/fills_info/fills_run3.csv
    ranges=(
        7920 7950 7980 8010 8040 8070
        7920 8010 8040 8070 8100 8130
        8160 8190 8220 8250 8280 8310
        8340 8400 8430 8460 8497 7920
        8010 8340 8400 8400 8480 8497
    )

fi


n_ranges=$((${#ranges[@]}-1))

output_directory=${profile_directory}/${year}/${rog}
log_directory=${output_directory}/logs

if [ ! -d ${log_directory} ]; then
    mkdir -p ${log_directory}
fi

for ((i_range=0; i_range<${n_ranges}; i_range++)); do
    i=${i_range}
    j=$((${i_range}+1))
    first_fill=$((${ranges[$i]}-15))
    last_fill=${ranges[$j]}
    #echo $(($last_fill-$first_fill))  # to check if number of fills looks reasonnable
    profile_name=profile_${rog}_${first_fill}_${last_fill}
    profile=${profile_name}.txt
    log_file=${log_directory}/${profile_name}.log
    python src/radiation_simulation/prepare_profile.py -ff ${first_fill} -lf ${last_fill} -rog ${rog} ${time_flags} -o ${output_directory} -p ${profile} -i ${fill_info} -skip > ${log_file} 2>&1 &
done

