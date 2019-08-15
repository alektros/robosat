import os
import sys
import argparse
import collections
from contextlib import contextmanager

from PIL import Image

import torch
import torch.backends.cudnn
from torch.nn import DataParallel
from torch.optim import Adam
from torch.utils.data import DataLoader
from torchvision.transforms import Resize, CenterCrop, Normalize

from tqdm import tqdm

from robosat.transforms import (
    JointCompose,
    JointTransform,
    JointRandomHorizontalFlip,
    JointRandomRotation,
    ConvertImageMode,
    ImageToTensor,
    MaskToTensor,
)
from robosat.datasets import SlippyMapTilesConcatenation
from robosat.metrics import Metrics
from robosat.losses import CrossEntropyLoss2d, mIoULoss2d, FocalLoss2d, LovaszLoss2d
from robosat.unet import UNet
from robosat.utils import plot
from robosat.config import load_config
from robosat.log import Log


@contextmanager
def no_grad():
    with torch.no_grad():
        yield


def add_parser(subparser):
    parser = subparser.add_parser(
        "checkgpu", help="trains model on dataset", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )


    parser.set_defaults(func=main)


def main(args):
    print(torch.cuda.device_count())
    

