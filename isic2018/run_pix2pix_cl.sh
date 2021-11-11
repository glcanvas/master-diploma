#!/bin/bash
  
train_root="/mnt/tank/scratch/nduginets"
validate_root="/mnt/tank/scratch/nduginets"
result_dir="/mnt/tank/scratch/nduginets/classifiers"
validate_csv="/nfs/home/nduginets/master-diploma/splits/validation.csv"

DEVICES=$1
SPLITS=$(echo $2 | tr ";" "\n")

for split in $SPLITS; do

train_csv="/nfs/home/nduginets/master-diploma/splits/generated/train_${split}.csv"

CUDA_VISIBLE_DEVICES=$DEVICES python3 train.py \
                                --train_root ${train_root} --train_csv=${train_csv} --epochs=100\
                                --validate_root=${validate_root} --validate_csv=${validate_csv} --learning_rate 0.001\
                                --result_dir ${result_dir} --experiment_name "classifier_${split}"
done


#CUDA_VISIBLE_DEVICES=0 python3 train_comet_csv.py with train_root="/mnt/tank/scratch/nduginets"\
#  train_csv="/nfs/home/nduginets/gan-aug-analysis/splits/different_gans/real-pix2pixhd/train.csv"\
#  epochs=100 val_root="/mnt/tank/scratch/nduginets" val_csv="/nfs/home/nduginets/gan-aug-analysis/splits/isic2019-val.csv"\
#  model_name="inceptionv4" exp_desc="pix2pix" exp_name="gans.train_pix2pix.inceptionv4.split0"