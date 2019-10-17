import sys
import collections
import os
import geojson
import json
import shapely.geometry

from robosat.features.core import denoise, grow, contours, simplify, featurize, parents_in_hierarchy


class BuildingHandler:
    kernel_size_denoise = 20
    kernel_size_grow = 20
    simplify_threshold = 0.01

    def __init__(self):
        self.features = []

    def apply(self, tile, mask, mask_path):

        

        #if tile.z != 18:
        #    raise NotImplementedError("Parking lot post-processing thresholds are tuned for z18")

        # The post-processing pipeline removes noise and fills in smaller holes. We then
        # extract contours, simplify them and transform tile pixels into coordinates.

        denoised = denoise(mask, self.kernel_size_denoise)
        grown = grow(denoised, self.kernel_size_grow)

        # Contours have a hierarchy: for example an outer ring, and an inner ring for a polygon with a hole.
        #
        # The ith hierarchy entry is a tuple with (next, prev, fst child, parent) for the ith polygon with:
        #  - next is the index into the polygons for the next polygon on the same hierarchy level
        #  - prev is the index into the polygons for the previous polygon on the same hierarchy level
        #  - fst child is the index into the polygons for the ith polygon's first child polygon
        #  - parent is the index into the polygons for the ith polygon's single parent polygon
        #
        # In case of non-existend indices their index value is -1.

        multipolygons, hierarchy = contours(grown)


        if hierarchy is None:
            return

        

        # In the following we re-construct the hierarchy walking from polygons up to the top-most polygon.
        # We then crete a GeoJSON polygon with a single outer ring and potentially multiple inner rings.
        #
        # Note: we currently do not handle multipolygons which are nested even deeper.

        # This seems to be a bug in the OpenCV Python bindings; the C++ interface
        # returns a vector<vec4> but here it's always wrapped in an extra list.
        assert len(hierarchy) == 1, "always single hierarchy for all polygons in multipolygon"
        hierarchy = hierarchy[0]

        assert len(multipolygons) == len(hierarchy), "polygons and hierarchy in sync"

        polygons = [simplify(polygon, self.simplify_threshold) for polygon in multipolygons]

        # Todo: generalize and move to features.core

        # All child ids in hierarchy tree, keyed by root id.
        features = collections.defaultdict(set)

        for i, (polygon, node) in enumerate(zip(polygons, hierarchy)):
            if len(polygon) < 3:
                print("Warning: simplified feature no longer valid polygon, skipping", file=sys.stderr)
                continue

            _, _, _, parent_idx = node

            ancestors = list(parents_in_hierarchy(i, hierarchy))

            # Only handles polygons with a nesting of two levels for now => no multipolygons.
            if len(ancestors) > 1:
                print("Warning: polygon ring nesting level too deep, skipping", file=sys.stderr)
                continue

            # A single mapping: i => {i} implies single free-standing polygon, no inner rings.
            # Otherwise: i => {i, j, k, l} implies: outer ring i, inner rings j, k, l.
            root = ancestors[-1] if ancestors else i

            features[root].add(i)

        for outer, inner in features.items():
            rings = [featurize(tile, polygons[outer], mask.shape[:2])]

            # In mapping i => {i, ..} i is not a child.
            children = inner.difference(set([outer]))

            for child in children:
                rings.append(featurize(tile, polygons[child], mask.shape[:2]))

            assert 0 < len(rings), "at least one outer ring in a polygon"

            geometry = geojson.Polygon(rings)
            shape = shapely.geometry.shape(geometry)

            if shape.is_valid:
                
                feature = geojson.Feature(geometry=geometry)
                
                json_path = os.path.splitext(mask_path)[0].split('_')[0]
                json_path = json_path + '.json'
                if os.path.isfile(json_path):
                    json = self.parse_json(json_path)
                    tile_name =os.path.splitext(os.path.basename(mask_path))[0]
                    feature.properties['data'] = json[tile_name]

                self.features.append(feature)
            else:
                print("Warning: extracted feature is not valid, skipping", file=sys.stderr)


    def save(self, out):
        collection = geojson.FeatureCollection(self.features)

        with open(out, "w") as fp:
            geojson.dump(collection, fp)

    def parse_json(self, json_path):
        with open(json_path, "r") as read_file:
            return json.load(read_file)
