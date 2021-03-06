from ctypes import Array

import pandas as pd
import numpy as np
import glob
from PIL import Image
from tqdm import tqdm
import os
from numpy.random import RandomState


def load_mask(path: str) -> int:
    img = Image.open(path)
    data = np.asarray(img)
    return 1 if np.any(data == 255) else 0


def data_to_csv(prefix: str, path: str, dataset_name: str, seeds):
    masks = glob.glob(path + "*.png")
    names = list(map(lambda x: x.split(path)[1], masks))
    items = list(map(lambda x: x.split("_"), names))
    codes = list(map(lambda x: os.path.join(prefix, "ISIC_" + x[1] + ".jpg"), items))
    types = list(map(lambda x: "_".join(x[3:]).split(".")[0], items))

    diseases = np.array(sorted(list(set(types))))
    print(diseases)
    print(types)
    print(codes)
    assert len(types) == len(codes)
    assert len(types) == len(masks)
    result_dict = {}
    for path, code, typ in tqdm(list(zip(masks, codes, types))):
        if code in result_dict:
            labels = result_dict[code]
        else:
            labels = np.zeros(len(diseases))
            result_dict[code] = labels
        idx = np.where(diseases == typ)
        labels[idx] = load_mask(path)

    use_format = True if len(seeds) > 1 else False
    for seed in seeds:
        rs = RandomState(seed)
        result = list(result_dict.items())
        result.sort(key=lambda x: x[0])
        result = rs.permutation(result)
        indices = list(map(lambda x: x[0], result))
        result = list(map(lambda x: x[1], result))

        frame = pd.DataFrame(result, index=indices, columns=diseases, dtype='int64')
        if use_format:
            frame.to_csv(dataset_name.format(seed), index_label="images")
        else:
            frame.to_csv(dataset_name, index_label="images")


if __name__ == "__main__":
    data_to_csv("ISIC2018_Task1-2_Validation_Input", "/Users/nduginets/Desktop/ISIC2018_Task2_Validation_GroundTruth/",
                "validation.csv", [0])
    ranges = [i for i in range(0, 10)]
    data_to_csv("ISIC2018_Task1-2_Training_Input", "/Users/nduginets/Desktop/ISIC2018_Task2_Training_GroundTruth_v3/",
                "baseline/train_{}.csv", ranges)
