import argparse
import collections
import json
import os
import sys
import random

import numpy as np
from PIL import Image
from tqdm import tqdm

import mercantile
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from rasterio.features import rasterize
from rasterio.warp import transform
from supermercado import burntiles

from robosat.config import load_config
from robosat.colors import make_palette, randomrgb,make_palette_with_random, randomgrayscale
from robosat.tiles import tiles_from_csv


def add_parser(subparser):
    parser = subparser.add_parser(
        "rasterize", help="rasterize features to label masks", formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("features", type=str, help="path to GeoJSON features file")
    parser.add_argument("tiles", type=str, help="path to .csv tiles file")
    parser.add_argument("out", type=str, help="directory to write converted images")
    parser.add_argument("--dataset", type=str, required=True, help="path to dataset configuration file")
    parser.add_argument("--zoom", type=int, required=True, help="zoom level of tiles")
    parser.add_argument("--size", type=int, default=512, help="size of rasterized image tiles in pixels")
    parser.add_argument("--multicolors", type=bool, default=False, help="use grayscale multicolors")
 
    parser.set_defaults(func=main)


def feature_to_mercator(feature):
    """Normalize feature and converts coords to 3857.

    Args:
      feature: geojson feature to convert to mercator geometry.
    """
    # Ref: https://gist.github.com/dnomadb/5cbc116aacc352c7126e779c29ab7abe

    src_crs = CRS.from_epsg(4326)
    dst_crs = CRS.from_epsg(3857)

    geometry = feature["geometry"]
    if geometry["type"] == "Polygon":
        xys = (zip(*part) for part in geometry["coordinates"])
        xys = (list(zip(*transform(src_crs, dst_crs, *xy))) for xy in xys)

        yield {"coordinates": list(xys), "type": "Polygon"}

    elif geometry["type"] == "MultiPolygon":
        for component in geometry["coordinates"]:
            xys = (zip(*part) for part in component)
            xys = (list(zip(*transform(src_crs, dst_crs, *xy))) for xy in xys)

            yield {"coordinates": list(xys), "type": "Polygon"}


def burn(tile, features, size, multicolors):
    """Burn tile with features.

    Args:
      tile: the mercantile tile to burn.
      features: the geojson features to burn.
      size: the size of burned image.

    Returns:
      image: rasterized file of size with features burned.
    """
    
    if multicolors is True:
        geometry_list = []
        def add(geometry_list, geometry):
            geometry_list.append(geometry)
            return 1 + len(geometry_list)
        shapes = ((geometry, add(geometry_list, geometry)) for feature in features for geometry in feature_to_mercator(feature))

    else:
        burnval = 1
        shapes = ((geometry, burnval) for feature in features for geometry in feature_to_mercator(feature))

    bounds = mercantile.xy_bounds(tile)
    transform = from_bounds(*bounds, size, size)

    return rasterize(shapes, out_shape=(size, size), transform=transform)

def burn_single(tile, feature, size, multicolors):
    bounds = mercantile.xy_bounds(tile)
    transform = from_bounds(*bounds, size, size)

    return rasterize(feature_to_mercator(feature), out_shape=(size, size), transform=transform)


def multi_burning(args,feature_map, bg, fg):
        # Burn features to tiles and write to a slippy map directory.
    for tile in tqdm(list(tiles_from_csv(args.tiles)), ascii=True, unit="tile"):
        if tile in feature_map:
            out = burn(tile, feature_map[tile], args.size,args.multicolors)
        else:
            out = np.zeros(shape=(args.size, args.size), dtype=np.uint8)

        out_dir = os.path.join(args.out, str(tile.z), str(tile.x))
        os.makedirs(out_dir, exist_ok=True)

        out_path = os.path.join(out_dir, "{}.png".format(tile.y))

        if os.path.exists(out_path):
            prev = np.array(Image.open(out_path))
            out = np.maximum(out, prev)

        out = Image.fromarray(out, mode="P")

        if args.multicolors is True:
            random_colors = []
            for graycolor in randomgrayscale():
                random_colors.append(graycolor)
            palette = make_palette_with_random(bg, random_colors=random_colors)
        else:
            palette = make_palette(bg, fg)

        out.putpalette(palette)

        out.save(out_path, optimize=True)

def save_out(out, args, tile, bg, fg,index):
    out_dir = os.path.join(args.out, str(tile.z), str(tile.x))
    os.makedirs(out_dir, exist_ok=True)

    out_path = os.path.join(out_dir, "{}_{}.png".format(tile.y,index))

    if os.path.exists(out_path):
        prev = np.array(Image.open(out_path))
        out = np.maximum(out, prev)

    out = Image.fromarray(out, mode="P")

    if args.multicolors is True:
        random_colors = []
        for graycolor in randomgrayscale():
            random_colors.append(graycolor)
        palette = make_palette_with_random(bg, random_colors=random_colors)
    else:
        palette = make_palette(bg, fg)

    out.putpalette(palette)

    out.save(out_path, optimize=True)


def single_burning(args,feature_map, bg, fg):
        # Burn features to tiles and write to a slippy map directory.
    for tile in tqdm(list(tiles_from_csv(args.tiles)), ascii=True, unit="tile"):
        if tile in feature_map:
            index = 0
            for feature in feature_map[tile]:
                out = burn_single(tile, feature, args.size,args.multicolors)
                save_out(out, args, tile, bg, fg, index)
                index = index + 1
        else:
            out = np.zeros(shape=(args.size, args.size), dtype=np.uint8)        
            save_out(out, args, tile, bg, fg, 0)

def main(args):
    dataset = load_config(args.dataset)

    classes = dataset["common"]["classes"]
    colors = dataset["common"]["colors"]
    assert len(classes) == len(colors), "classes and colors coincide"

    assert len(colors) == 2, "only binary models supported right now"
    bg = colors[0]
    fg = colors[1]

    os.makedirs(args.out, exist_ok=True)

    # We can only rasterize all tiles at a single zoom.
    assert all(tile.z == args.zoom for tile in tiles_from_csv(args.tiles))

    with open(args.features) as f:
        fc = json.load(f)

    # Find all tiles the features cover and make a map object for quick lookup.
    feature_map = collections.defaultdict(list)
    for i, feature in enumerate(tqdm(fc["features"], ascii=True, unit="feature")):

        if feature["geometry"]["type"] != "Polygon":
            continue

        try:
            for tile in burntiles.burn([feature], zoom=args.zoom):
                feature_map[mercantile.Tile(*tile)].append(feature)
        except ValueError as e:
            print("Warning: invalid feature {}, skipping".format(i), file=sys.stderr)
            continue
    
    single_burning(args, feature_map, bg, fg)


