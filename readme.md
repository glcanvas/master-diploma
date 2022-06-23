# How to build and train
 
## Prepare dataset before passing into pix2pix
* At the first datasets must be downloaded, in this work we used [ISIC 2018 dataset](https://challenge.isic-archive.com/data/#2018)
* You must download 3 datasets:
  * Training data (10.4 G)
  * Training Ground Truth (26 MB)
  * Validation Data (228 MB)
  * Validation Ground Truth (742 KB)
* Create directory named `images`
* Then unpack these zips into `images` directory
* Out of the box already works baseline model, to support model with generated images pix2pix generator must be trained first

### Prepare dataset to train pix2pix network
* to pass original images into pix2pix model it must be processed into the correseponded format
* go to `dataset-to-pix2pix-data` folder
* execute bash script with arguments: `DIR=<full-path-to-folders> resize-images.sh -a <relative-parth-to-attribute-dir> -s <relative-parth-to-segmentation-dir> -i <relative-parth-to-images-dir>`

### Train pix2pix network
* `cd pix2pixHD` -- go to the GAN directory
* `python train.py --name <experiment-name> --dataroot <path-to-lesions-with-masks> --label_nc 8 --checkpoints_dir <directory-to-storage-temporary-results> --gpu_id <gpu-id> --batchSize 4` -- this command starts train
* `python train.py --name <experiment-name> --dataroot <path-to-lesions-with-masks> --label_nc 8 --checkpoints_dir <directory-to-storage-temporary-results> --gpu_id <gpu-id> --batchSize 4 --continue_train` -- this command continues train
* When the pix2pix model was trained, need to generate synthesized images 
* `python3 test.py --name <experiment-name> --dataroot <path-to-lesions-with-masks> --checkpoints_dir <directory-to-storage-temporary-results> --label_nc 8 --how_many 10000 --gpu_id  <gpu-id> --results_dir images/pix2pix_result/` -- this script will create generated images

### Prepare data to pass into classification model
* I already split datasets
* use `splits` folder to train model with usual data
* use `splits_boxed` folder to train model with bounding boxes 
* If you want to create custom splitting


### Train classification model
Model based on InceptionV4 network

* `cd classificator_network` -- go to the classificator directory
* `pythob train.py --train_root <full-path-to-train-images-folder>
  --train_csv <full-path-to-train-csv-image> --validate_root <full-path-to-validate-images-folder> --validate_csv <full-path-to-validate-csv-image> --epochs <epochs-count> --result_dir <base-result-directory> --experiment_name <launch-name>` -- execute this code

### Augmentation techniques