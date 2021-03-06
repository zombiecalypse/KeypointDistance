#!/usr/bin/python

# Copyright 2014 Aaron Karper
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script can help you finding a good location for your appartment:
#
# Say you don't live with your partner (they live in A), you got a job in B, and
# your friends live in C and D. Now you don't want to spend all your life on the
# road, so you want to minimize the commuting-distance to all places. This tool
# takes two files, the options and the keypoints, and sorts the options by
# feasibility (it prints the commuting score in hours).
#
# The options file contains one address per line.
#
# The keypoints file contains lines containing a double in the first column,
# that signifies the relative importance of the point (higher is more important)
# and the address of the point after a single space.

# usage: key-distance.py [-h] [--options OPTIONS] [--keypoints KEYPOINTS]
#                        [--mode MODE]
#
# Give weighted distances of options to important locations.
#
# optional arguments:
#   -h, --help            show this help message and exit
#   --options OPTIONS     File with one possible location per line
#   --keypoints KEYPOINTS
#                         File with the priority in first column and the key
#                         point in the rest
#   --mode MODE           mode of transportation (driving, transit, bicycle,
#                         walking)

import time
import random
import os
import urllib
import simplejson
import pprint
import numpy
import argparse
import logging
import functools

request_log = logging.getLogger('request')

def retry(times, sleep):
    def wrap(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            for i in range(times-1):
                try:
                    return f(*args, **kwargs)
                except BaseException as e:
                    request_log.warn(e)
                    up_to = 2**i * sleep
                    actual = random.uniform(0, up_to)
                    time.sleep(actual)
            return f(*args, **kwargs)
        return wrapper
    return wrap

@retry(3, 2.0)
def transit_distance(orig, dest):
    url = "https://maps.googleapis.com/maps/api/directions/json?" \
        "mode=transit&departure_time=1418983000" \
        "&origin={0}&destination={1}".format(orig, dest)

    request_log.info('GET %s', url)
    r = urllib.urlopen(url).read()
    result = simplejson.loads(r)
    leg = result['routes'][0]['legs'][0]
    return leg['duration']['value']


# Distance matrix api doesn't offer transit. The directions api does however.
def load_distances_transit(origins, destinations):
    """The distance matrix for transit."""

    distances = numpy.zeros((len(origins), len(destinations)), dtype=float)
    for i, orig in enumerate(origins):
        for j, dest in enumerate(destinations):
            distances[i,j] = transit_distance(orig, dest)

    return distances


def load_pairwise_distances(origins, destinations, mode='driving'):
    if mode == 'transit':
        return load_distances_transit(origins, destinations)

    @retry(3, 2.0)
    def get_response():
        url = "http://maps.googleapis.com/maps/api/distancematrix/json?" \
            "origins={0}&destinations={1}&mode={2}&sensor=false" \
            "departure_time=1418809537".format(
                "|".join(urllib.quote_plus(e) for e in origins),
                "|".join(urllib.quote_plus(e) for e in destinations),
                mode)
        request_log.info('GET %s', url)
        r = urllib.urlopen(url).read()
        return simplejson.loads(r)

    result = get_response()

    try:
        distances = numpy.zeros((len(origins), len(destinations)), dtype=float)
        for i, row in enumerate(result['rows']):
            for j, el in enumerate(row['elements']):
                distances[i,j] = el['duration']['value']
        return distances
    except:
        pprint.pprint(result)
        raise

def keypoint_optimize(options, keyspots, weights, mode):
    """Returns the location based scoring of the options."""
    durations = load_pairwise_distances(options, keyspots, mode)
    weighted = durations.dot(weights)
    return dict(zip(options, weighted/60/60/weights.sum()))

def read_option_file(fp):
    fp = os.path.expanduser(fp)
    with open(fp) as f:
        return map(str.strip, f.readlines())

def read_keypoint_file(fp):
    fp = os.path.expanduser(fp)
    with open(fp) as f:
        keypoints = []
        for l in f:
            priority_p, _, name = l.strip().partition(' ')
            keypoints.append((float(priority_p), name))
        return zip(*keypoints)

parser = argparse.ArgumentParser(
    description='Give weighted distances of options to important locations.')
parser.add_argument(
    '--options', type=read_option_file,
    help="File with one possible location per line")
parser.add_argument(
    '--keypoints', type=read_keypoint_file,
    help='File with the priority in first column and the key point in the rest')
parser.add_argument(
    '--mode',
    help='mode of transportation (driving, transit, bicycle, walking)')
parser.add_argument(
    '--verbose', action='store_true',
    help='mode of transportation (driving, transit, bicycle, walking)')

if __name__ == '__main__':
    args= parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig()

    options = args.options
    weights, keypoints = args.keypoints

    optimized = keypoint_optimize(
        options, keypoints, numpy.array(weights), args.mode)

    for k in sorted(optimized, key=lambda x: optimized[x]):
        print "%.3f%20s" % (optimized[k], k)
