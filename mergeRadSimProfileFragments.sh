#!/bin/bash

year=2022
rog=BPix_BmI_SEC1_LYR1

input_profile_directory=data/radiation_simulation/profiles/fragments
output_profile_directory=data/radiation_simulation/profiles/per_year
input_directory=${input_profile_directory}/${year}/${rog}
output_directory=${output_profile_directory}/${rog}
output_profile_name=${output_directory}/profile_${rog}_${year}.txt

if [ ! -d ${output_directory} ]; then
    mkdir -p ${output_directory}
fi

python src/radiation_simulation/merge_profiles.py -i ${input_directory} -o ${output_profile_name}

