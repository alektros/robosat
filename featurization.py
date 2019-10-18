import os
from threading import Thread
from robosat.tiles import tiles_from_slippy_map
from robosat.tools.features_splitted


def _vectorize_dir(masks_dir, result_dir, result_name):
    command_base = 'sudo docker run -it --rm -v $PWD:/data --ipc=host --network=host alektros/robosat:latest-gpu features-splitted '
    command = command_base + \
        '/data/{} --type building --dataset /data/dataset-building.toml /data/{}/{}.geojson'.format(
            masks_dir, result_dir, result_name)
    os.system(command)


def vectorize_displaced_tiles(tiles, biased_tiles_directory):
    directions = {'ne': 45, 'nw': 135, 'se': 225, 'sw': 315}
    for direction in directions:
        biased_dir_template = biased_tiles_directory + '/{}_{}_{}_{}'
        for tile in tiles:
            biased_directory = biased_dir_template.format(
                tile.z, tile.x, tile.y, direction)
            if os.path.isdir(biased_directory):
                geojson_name = '{}_{}_{}'.format(tile.x, tile.y, direction)
                _vectorize_dir(biased_directory, biased_directory, geojson_name)


class VectorizationThread(Thread):
    def __init__(self, source_images_directory, biased_tiles_directory):
        Thread.__init__(self)
        self.source_images_directory = source_images_directory
        self.biased_tiles_directory = biased_tiles_directory

    def run(self):
        tiles = list(tile for tile in tiles_from_slippy_map(self.source_images_directory))
        vectorize_displaced_tiles(tiles, self.biased_tiles_directory)
