import argparse

import numpy as np

from PIL import Image
from tqdm import tqdm

from robosat.tiles import tiles_from_slippy_map
from robosat.config import load_config

from robosat.features.parking import ParkingHandler
from robosat.features.building import BuildingHandler


# Register post-processing handlers here; they need to support a `apply(tile, mask)` function
# for handling one mask and a `save(path)` function for GeoJSON serialization to a file.
handlers = {"parking": ParkingHandler, 'building' : BuildingHandler}


def add_parser(subparser):
    parser = subparser.add_parser(
        "features-splitted",
        help="extracts simplified GeoJSON features from segmentation masks",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("masks", type=str, help="slippy map directory with segmentation masks")
    parser.add_argument("--type", type=str, required=True, choices=handlers.keys(), help="type of feature to extract")
    parser.add_argument("--dataset", type=str, required=True, help="path to dataset configuration file")
    parser.add_argument("out", type=str, help="path to GeoJSON file to store features in")

    parser.set_defaults(func=main)


def main(args):
    '''
    print ('Splitted')

    handler = handlers[args.type]()

    tiles = list(tiles_from_slippy_map(args.masks))
    #for tile in tiles:
    #    print (tile)
    

    for tile, path in tqdm(tiles, ascii=True, unit="mask"):
        image = np.array(Image.open(path).convert("L"), dtype=np.uint8)
        handler.apply(tile, image,path)

    handler.save(args.out)
'''
    features_splitted(args.masks, args.out, args.type, args.dataset)

def features_splitted(masks, out, type, dataset):
    print ('Splitted')
    handler = handlers[type]()

    tiles = list(tiles_from_slippy_map(masks))

    for tile, path in tqdm(tiles, ascii=True, unit="mask"):
        image = np.array(Image.open(path).convert("L"), dtype=np.uint8)
        handler.apply(tile, image, path)

    handler.save(out)
