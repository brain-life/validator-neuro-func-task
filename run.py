#!/usr/bin/env python3

import os
import json
import re
import subprocess
import nibabel
import csv

import numpy as np

# Things that this script checks
# 
# * make sure mrinfo runs successfully on specified t1 file
# * make sure t1 is 3d
# * raise warning if t1 transformation matrix isn't unit matrix (identity matrix)

# display where this is running
# import socket
# print(socket.gethostname())

with open('config.json') as config_json:
    config = json.load(config_json)

results = {"errors": [], "warnings": []}

directions = None

def check_affine(affine):
    if affine[0][0] != 1: results['warnings'].append("transform matrix 0.1 is not 1")
    if affine[0][1] != 0: results['warnings'].append("transform matrix 0.2 is not 0")
    if affine[0][2] != 0: results['warnings'].append("transform matrix 0.2 is not 0")
    if affine[1][0] != 0: results['warnings'].append("transform matrix 1.0 is not 0")
    if affine[1][1] != 1: results['warnings'].append("transform matrix 1.1 is not 1")
    if affine[1][2] != 0: results['warnings'].append("transform matrix 1.2 is non 0")
    if affine[2][0] != 0: results['warnings'].append("transform matrix 2.0 is not 0")
    if affine[2][1] != 0: results['warnings'].append("transform matrix 2.1 is not 0")
    if affine[2][2] != 1: results['warnings'].append("transform  matrix 2.2 is not 1")

try:
    print('checking bold')
    img = nibabel.load(config["bold"])
    #results['meta'] = img.header

    results['meta'] = {}
    for key in img.header:
        value = img.header[key]
        results['meta'][key] = value

    results['meta']['base_affine'] = img.header.get_base_affine()

    # check dimensions
    dims = img.header['dim'][0]
    if dims != 4:
        results['errors'].append("bold should be 4D but has " + str(dims))

    check_affine(img.header.get_base_affine())

except Exception as e:
    results['errors'].append("failed to validate bold ..  error code: " + str(e))

if not os.path.exists("output"):
    os.mkdir("output")

# TODO - normalize (for now, let's just symlink)
# TODO - if it's not .gz'ed, I should?
if os.path.lexists("output/bold.nii.gz"):
    os.remove("output/bold.nii.gz")
os.symlink("../"+config['bold'], "output/bold.nii.gz")

#TODO - validate optional stuff
if 'events' in config:
    try:
        with open(config['events']) as tsv:
            tsv_reader = csv.reader(tsv, delimiter='\t')
            for row in tsv_reader:
                #TODO - what should do with row now?
                print("TODO - events row:", row)
                
        if os.path.lexists("output/events.tsv"):
            os.remove("output/events.tsv")
        os.symlink("../"+config['events'], "output/events.tsv")
    except Exception as e:
        results['errors'].append("failed to validate events ..  error code: " + str(e))

if 'sbref' in config:
    try:
        #TODO - validate sbref?
        if os.path.lexists("output/sbref.nii.gz"):
            os.remove("output/sbref.nii.gz")
        os.symlink("../"+config['sbref'], "output/sbref.nii.gz")
    except Exception as e:
        results['errors'].append("failed to validate sbref ..  error code: " + str(e))

if 'physio' in config:
    try:
        #TODO - validate 
        if os.path.lexists("output/physio.tsv.gz"):
            os.remove("output/physio.tsv.gz")
        os.symlink("../"+config['physio'], "physio.tsv.gz")
    except Exception as e:
        results['errors'].append("failed to validate physio.tsv ..  error code: " + str(e))

if 'physio_json' in config:
    try:
        #TODO - validate 
        if os.path.lexists("output/physio.json"):
            os.remove("output/physio.json")
        os.symlink("../"+config['physio_json'], "physio.json")
    except Exception as e:
        results['errors'].append("failed to validate physio.json ..  error code: " + str(e))

print("all good")

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
            np.int16, np.int32, np.int64, np.uint8,
            np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32,
            np.float64)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)): 
            return obj.tolist()
        elif isinstance(obj, (bytes,)):
            return obj.decode("utf-8")
        return json.JSONEncoder.default(self, obj)

with open("product.json", "w") as fp:
    json.dump(results, fp, cls=NumpyEncoder)

print("done")
