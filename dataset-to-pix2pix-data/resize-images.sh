#!/bin/bash

REPO_DIR=

if [ -z "${DIR}" ]
then
  echo "required DIR argument"
  exit 1
fi
BASE_DIR="${DIR}"
echo "Data root directory: $BASE_DIR"
echo ""

while getopts a:s:i: option
do
	case "${option}"
		in
		a) ATTRI_DIR=${BASE_DIR}/${OPTARG};;
		s) SEG_DIR=${BASE_DIR}/${OPTARG};;
		i) IMAGE_DIR=${BASE_DIR}/${OPTARG};;
	esac
done

echo "Attribute directory: $ATTRI_DIR"
echo "Segmentation directory: $SEG_DIR"
echo "Image directory: $IMAGE_DIR"
echo ""

attribute_resized="${BASE_DIR}/attribute_resized"
segmentation_resized="${BASE_DIR}/segmentation_resized"
image_resized="${BASE_DIR}/image_resized"
echo ""

echo "attribute_resized: $attribute_resized"
echo "segmentation_resized: $segmentation_resized"
echo "image_resized: $image_resized"
echo ""

mkdir "$attribute_resized"
cd "$attribute_resized"
find "$ATTRI_DIR" -name '*.png' -exec sh -c 'echo "{}"; convert "{}" -resize 1024x512\> -size 1024x512 xc:red +swap -gravity center -composite `basename "{}" .png`.png' \;
cd ..

mkdir "$segmentation_resized"
cd "$segmentation_resized"
find "$SEG_DIR" -name '*.png' -exec sh -c 'echo "{}"; convert "{}" -resize 1024x512\> -size 1024x512 xc:red +swap -gravity center -composite `basename "{}" .png`.png' \;
cd ..

mkdir "$image_resized"
cd "$image_resized"
find "$IMAGE_DIR" -name '*.jpg' -exec sh -c 'echo "{}"; convert "{}" -resize 1024x512\> -size 1024x512 xc:black +swap -gravity center -composite `basename "{}" .jpg`.png' \;
cd ..


if [ -z "${DIR}" ]
then
  echo "required DIR argument"
  exit 1
fi
BASE_DIR="${DIR}"
echo "$BASE_DIR"
echo ""

while getopts a:s:i: option
do
	case "${option}"
		in
		a) ATTRI_DIR=${BASE_DIR}/${OPTARG};;
		s) SEG_DIR=${BASE_DIR}/${OPTARG};;
		i) IMAGE_DIR=${BASE_DIR}/${OPTARG};;
	esac
done

echo "Attribute directory: $ATTRI_DIR"
echo "Segmentation directory: $SEG_DIR"
echo "Image directory: $IMAGE_DIR"
echo ""


python ${REPO_DIR}/assemble_data.py "$BASE_DIR"
mkdir "$BASE_DIR/images_512p"
cd "$BASE_DIR/images_512p"
find "$IMAGE_DIR" -name '*jpg' -exec sh -c 'echo "{}"; convert "{}" -resize 1024x512\> `basename "{}" .jpg`.png' \;


mkdir "$BASE_DIR/attribute_512p"
cd "$BASE_DIR/attribute_512p"
find "$ATTRI_DIR" -name '*.png' -exec sh -c 'echo "{}"; convert "{}" -resize 1024x512 `basename "{}" .png`.png' \;


mkdir "$BASE_DIR/seg_512p"
cd "$BASE_DIR/seg_512p"
find "$SEG_DIR" -name '*.png' -exec sh -c 'echo "{}"; convert "{}" -resize 1024x512 `basename "{}" .png`.png' \;


if [ -z "${DIR}" ]
then
  echo "required DIR argument"
  exit 1
fi
BASE_DIR="${DIR}"
echo "Data root directory: $BASE_DIR"
echo ""

python ${REPO_DIR}/instance_map.py "$BASE_DIR"
mkdir "$BASE_DIR/instance_map"
cd "$BASE_DIR/instance_map"
find "$BASE_DIR/instance_map_no_border" -name '*.png' -exec sh -c 'echo "{}"; convert "{}" -resize 1024x512\> -size 1024x512 xc:black +swap -gravity center -composite `basename "{}" .png`.png' \;

mkdir -p "$BASE_DIR/datasets/skin"
mv "$BASE_DIR/instance_map" "$BASE_DIR/datasets/skin/"
mv "$BASE_DIR/semantic_map" "$BASE_DIR/datasets/skin/"

mkdir -p "$BASE_DIR/datasets/skin/test_label"
mkdir -p "$BASE_DIR/datasets/skin/test_inst"
mkdir -p "$BASE_DIR/datasets/skin/test_img"
mv "$BASE_DIR/datasets/skin/instance_map" "$BASE_DIR/datasets/skin/train_inst"
mv "$BASE_DIR/datasets/skin/semantic_map" "$BASE_DIR/datasets/skin/train_label"
mv "$BASE_DIR/image_resized" "$BASE_DIR/datasets/skin/"
mv "$BASE_DIR/datasets/skin/image_resized" "$BASE_DIR/datasets/skin/train_img"

python ${REPO_DIR}/select_train_test.py "$BASE_DIR/datasets/skin"
