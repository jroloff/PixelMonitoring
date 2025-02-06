#!/bin/bash

phase=1_newL1
rog=BPix_BmI_SEC1_LYR1

if [ "$phase" == "0" ]; then
    years=(2015 2016)
elif [ "$phase" == "1" ]; then
    years=(2017 2018)
    yets=(20172018)
elif [ "$phase" == "1_newL1" ]; then
    years=(2022)
    yets=(2022)
fi

# Define input and output
input_profile_directory=data/radiation_simulation/profiles/per_year
output_profile_directory=data/radiation_simulation/profiles/per_phase
input_directory_tmp=${output_profile_directory}/input_tmp
input_directory=${input_profile_directory}/${rog}
output_directory=${output_profile_directory}/${rog}
output_profile_name=${output_directory}/profile_${rog}_phase${phase}.txt

# Make output and tmp directories
if [ ! -d ${output_directory} ]; then
    mkdir -p ${output_directory}
fi
if [ ! -d ${input_directory_tmp} ]; then
    mkdir -p ${input_directory_tmp}
fi

# Copy relevant files to tmp input directory
cp ${input_directory}/* ${input_directory_tmp}

for yets_period in ${yets[@]}; do
  input_yets_directory=data/radiation_simulation/profiles/fragments/${yets_period}/${rog}
  n_files=$(ls ${input_yets_directory} | grep -E "\.txt$" | wc -l)
  if [ "${n_files}" != "1" ]; then
    echo "ERROR! More than 1 file in YETS ${yets_period}"
    echo $(ls ${input_yets_directory} | grep -E "\.txt$")
    #exit 1
  fi
  file=$(ls ${input_yets_directory} | grep -E "\.txt$")
  cp ${input_yets_directory}/${file} ${input_directory_tmp}
done

# Merge files
python src/radiation_simulation/merge_profiles.py -i ${input_directory_tmp} -o ${output_profile_name}
rm -r ${input_directory_tmp}

