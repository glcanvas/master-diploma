from itertools import islice
import os
import numpy as np
import pandas as pd
import pretrainedmodels as ptm
from sklearn.metrics import confusion_matrix, roc_auc_score, f1_score
import torch
import torch.nn as nn
import torchmetrics
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, sampler
from torchvision import models, datasets, transforms
from torchvision.utils import save_image
from tqdm import tqdm
from dataset_loader import CSVDatasetWithName
import params_loader as pl
import utils as utils
from sacred.observers import RunObserver
import logging
import math
import segmentation_models_pytorch as smp

from masks_saver import MasksSaver

np.set_printoptions(precision=4, suppress=True)
THRESHOLD = 0.5

# PyTroch version

SMOOTH = 1e-6


def iou_pytorch(outputs: torch.Tensor, labels: torch.Tensor):
    intersection = (outputs & labels).float().sum((1, 2, 3))  # Will be zero if Truth=0 or Prediction=0
    union = (outputs | labels).float().sum((1, 2, 3))  # Will be zzero if both are 0
    # iou = (intersection + SMOOTH) / (union + SMOOTH)  # We smooth our devision to avoid 0/0
    # thresholded = torch.clamp(20 * (iou - 0.5), 0, 10).ceil() / 10  # This is equal to comparing with thresolds
    # return thresholded.mean().item()  # Or thresholded.mean() if you are interested in average across the batch
    return intersection.to("cpu"), union.to("cpu")


def iou_pytorch_by_class(idx, outputs: torch.Tensor, labels: torch.Tensor):
    outputs = outputs[:, idx, :, :]
    labels = labels[:, idx, :, :]
    intersection = (outputs & labels).float().sum((1, 2))  # Will be zero if Truth=0 or Prediction=0
    union = (outputs | labels).float().sum((1, 2))  # Will be zzero if both are 0
    # iou = (intersection + SMOOTH) / (union + SMOOTH)  # We smooth our devision to avoid 0/0
    # thresholded = torch.clamp(20 * (iou - 0.5), 0, 10).ceil() / 10  # This is equal to comparing with thresolds
    # return thresholded.mean().item()  # Or thresholded.mean() if you are interested in average across the batch
    return intersection.to("cpu"), union.to("cpu")


def calculate_iou(list_intersections, list_unions):
    intersection = torch.cat(list_intersections)
    union = torch.cat(list_unions)
    iou = (intersection + SMOOTH) / (union + SMOOTH)  # We smooth our devision to avoid 0/0
    thresholded = torch.clamp(20 * (iou - 0.5), 0, 10).ceil() / 10  # This is equal to comparing with thresolds
    return thresholded.mean().item()  # Or thresholded.mean() if you are interested in average across the batch


class ModelWithSigmoidOut(nn.Module):

    def __init__(self, model):
        super(ModelWithSigmoidOut, self).__init__()
        self.model = model
        self.sigmoid = nn.Sigmoid()

    def forward(self, input):
        x = self.model(input)
        x = self.sigmoid(x)
        return x


class AverageMeter(object):
    """Computes and stores the average and current value"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, items_size):
        self.val = val
        self.sum += val
        self.count += items_size
        self.avg = self.sum / self.count


def concat(old_tensor, new_tensor):
    new_tensor = new_tensor.to("cpu")
    if old_tensor is None:
        old_tensor = new_tensor
    else:
        old_tensor = torch.cat((old_tensor, new_tensor))
    return old_tensor


def train_epoch(device, model, dataloaders, metric_holder, criterion, optimizer, phase,
                epoch_number, total_epoch_count,
                label_names,
                batches_per_epoch,
                mask_saver):
    losses = AverageMeter()
    accuracies = AverageMeter()
    result_iou = {i: ([], []) for i in label_names}
    base_iou = ([], [])

    if phase == 'train':
        model.train()
        meters = metric_holder['train']
    else:
        model.eval()
        meters = metric_holder['val']

    if batches_per_epoch:
        tqdm_loader = tqdm(
            islice(dataloaders['train'], 0, batches_per_epoch),
            total=batches_per_epoch)
    else:
        tqdm_loader = tqdm(dataloaders[phase])

    # int_labels_cat = None
    # output_cat = None
    idx_ = 0
    for data in tqdm_loader:
        idx_ += 1
        (inputs, labels, int_labels), name = data

        inputs = inputs.to(device)
        labels = labels.to(device)
        int_labels = int_labels.to(device)

        if phase == 'train':
            optimizer.zero_grad()

        with torch.set_grad_enabled(phase == 'train'):
            outputs = model(inputs)

            output_copy = torch.zeros_like(outputs, dtype=torch.int)
            output_copy[outputs[:, :, :, :] <= THRESHOLD] = 0
            output_copy[outputs[:, :, :, :] > THRESHOLD] = 1

            loss = criterion(outputs, labels)

            if phase == 'train':
                loss.backward()
                optimizer.step()

        losses.update(loss.item(), inputs.size(0))
        accuracies.update(torch.sum(output_copy == labels).item(),
                          (output_copy.shape[0] * output_copy.shape[1] * output_copy.shape[2] * output_copy.shape[3]))

        # mask_saver.write_masks(idx, int_labels, output_copy)
        intersection, union = iou_pytorch(output_copy, int_labels)
        base_iou[0].append(intersection), base_iou[1].append(union)
        for idx, i in enumerate(label_names):
            intersection, union = iou_pytorch_by_class(idx, output_copy, int_labels)
            result_iou[i][0].append(intersection), result_iou[i][1].append(union)
        tqdm_loader.set_postfix(loss=losses.avg, acc=accuracies.avg, epoch=epoch_number)

    # mask_saver.end()
    result_iou['loss'] = losses.avg
    result_iou['accuracy'] = accuracies.avg
    result_iou['iou'] = calculate_iou(base_iou[0], base_iou[1])
    for idx, i in enumerate(label_names):
        intersection, union = result_iou[i]
        result_iou[i] = calculate_iou(intersection, union)

    meters.add_record(epoch_number, result_iou)


def save_images(dataset, to, n=32):
    for i in range(n):
        img_path = os.path.join(to, 'img_{}.png'.format(i))
        save_image(dataset[i][0], img_path)


def main(train_root, train_csv, val_root, val_csv, epochs: int, batch_size: int,
         num_workers,
         lr, experiment_path, experiment_name, start_from_begin, csv_image_field="images", n_classes=5):
    last_model_path = os.path.join(experiment_path, "last_model.pth")
    train_metrics = utils.Dumper(os.path.join(experiment_path, "train_metrics.json"))
    test_metrics = utils.Dumper(os.path.join(experiment_path, "test_metrics.json"))
    metric_holder = {
        'train': train_metrics,
        'val': test_metrics
    }

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = smp.Unet(
        encoder_name="resnet34",  # choose encoder, e.g. mobilenet_v2 or efficientnet-b7
        encoder_weights="imagenet",  # use `imagenet` pre-trained weights for encoder initialization
        in_channels=3,  # model input channels (1 for gray-scale images, 3 for RGB, etc.)
        classes=5,  # model output channels (number of classes in your dataset)
    )
    model = ModelWithSigmoidOut(model)

    latest_known_epoch = train_metrics.latest_key(-1)
    logging.info("detected epoch number: {} of: {}".format(latest_known_epoch, epochs))
    if latest_known_epoch == -1:
        epochs_list = [i for i in range(epochs)]
        logging.info("start from begining")
    else:
        epochs_list = [i for i in range(latest_known_epoch + 1, epochs)]
        logging.info("start from epoch number: {}".format(latest_known_epoch + 1))
        model = torch.load(last_model_path)

    model.to(device)

    total_params = sum(p.numel() for p in model.parameters())
    logging.debug('total params')
    logging.debug(total_params)
    logging.debug("model: {}".format(model))

    data_transforms = {
        'train': transforms.Compose([
            transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.5 * 0.1),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            transforms.Resize((512, 1024))
        ]),
        'val': transforms.Compose([
            transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.5 * 0.1),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            transforms.Resize((512, 1024))
        ]),
    }

    logging.debug('augmentation: ' + str(data_transforms))
    # image_name, target
    train_ds = CSVDatasetWithName(
        train_root, train_csv, csv_image_field,
        transform=data_transforms['train'])
    if val_root is not None:
        val_ds = CSVDatasetWithName(
            val_root, val_csv, csv_image_field,
            transform=data_transforms['val'])
    else:
        val_ds = None

    labels = train_ds.target_fields

    datasets = {
        'train': train_ds,
        'val': val_ds,
    }

    data_sampler = None
    shuffle = False
    dl_train = DataLoader(datasets['train'], batch_size=batch_size,
                          shuffle=shuffle, num_workers=num_workers,
                          sampler=data_sampler)
    if val_root is not None:
        dl_val = DataLoader(datasets['val'], batch_size=batch_size,
                            shuffle=shuffle, num_workers=num_workers,
                            sampler=None)
    else:
        dl_val = None

    dataloaders = {
        'train': dl_train,
        'val': dl_val,
    }

    criterion = nn.BCELoss()  # because on single image might be multiple classes

    optimizer = optim.SGD(model.parameters(), lr=lr,
                          momentum=0.9, weight_decay=0.001)

    scheduler = optim.lr_scheduler.MultiStepLR(optimizer,
                                               milestones=[25],
                                               gamma=0.1)
    batches_per_epoch = None

    for epoch in epochs_list:
        logging.debug('train epoch {}/{}'.format(epoch + 1, epochs))
        # train_mask_saver = MasksSaver(experiment_path, "train_{}".format(epoch))
        train_epoch(
            device, model, dataloaders, metric_holder, criterion, optimizer, 'train',
            epoch, epochs,
            labels,
            batches_per_epoch, None)

        if val_root is not None:
            # test_mask_saver = MasksSaver(experiment_path, "test_{}".format(epoch))

            logging.debug('val epoch {}/{}'.format(epoch + 1, epochs))
            train_epoch(
                device, model, dataloaders, metric_holder, criterion, optimizer, 'val',
                epoch, epochs,
                labels,
                batches_per_epoch, None)
            logging.debug('-' * 40)

        scheduler.step()

        torch.save(model, last_model_path)


if __name__ == "__main__":

    if os.path.exists("/Users/nduginets/Desktop"):
        params = pl.initialize([
            '--train_root', '/Users/nduginets/Desktop',
            '--train_csv', '/Users/nduginets/PycharmProjects/master-diploma/segmentation_splits/validation.csv',
            "--validate_root", "/Users/nduginets/Desktop",
            "--validate_csv", "/Users/nduginets/PycharmProjects/master-diploma/segmentation_splits/validation.csv",
            "--epochs", "100",
            "--learning_rate", "0.001",
            "--result_dir", "/Users/nduginets/Desktop",
            "--experiment_name", "tmp",
            "--num_workers", "0",  # stupid Mac os!!!!
            "--batch_size", "2"
        ])
    else:
        params = pl.initialize()

    ex_path = os.path.join(params.result_dir, params.experiment_name)
    main(
        params.train_root,
        params.train_csv,
        params.validate_root,
        params.validate_csv,
        params.epochs,
        params.batch_size,
        params.num_workers,
        params.learning_rate,
        ex_path,
        params.experiment_name,
        params.start_from_begin)
