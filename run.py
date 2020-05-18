#!/usr/bin/env python3

import os
import json
import re
import subprocess
import nibabel
import csv
import math
import binascii
import numpy as np
from PIL import Image, ImageDraw

# Things that this script checks
# 
# * make sure mrinfo runs successfully on specified t1 file
# * make sure t1 is 3d
# * raise warning if t1 transformation matrix isn't unit matrix (identity matrix)

# display where this is running
# import socket
# print(socket.gethostname())

with open('config.json', encoding='utf-8') as config_json:
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

def fix_level(image):
    image = image - np.min(image)
    image_max = np.max(image)
    return (image / image_max)*500


def validate_func(path):
    with open(path, 'rb') as test_f:
        if binascii.hexlify(test_f.read(2)) != b'1f8b':
            results['errors'].append("file doesn't look like a gzip-ed nifti");
            return

    try:
        print('checking bold')
        img = nibabel.load(path)
        #results['meta'] = img.header

        results['meta'] = {'nifti_headers': {}}
        #results['meta']['nifti_headers'] = img.header #Object of type 'Nifti1Header' is not JSON serializable
        for key in img.header:
            value = img.header[key]
            results['meta']['nifti_headers'][key] = value

        results['meta']['nifti_headers']['base_affine'] = img.header.get_base_affine()

        # check dimensions
        dims = img.header['dim'][0]
        if dims != 4:
            results['errors'].append("bold should be 4D but has " + str(dims))

        check_affine(img.header.get_base_affine())

        #################################################################
        # save some mid slices
        #

        print("creating mid slice images")
        #img_data = img.get_fdata()
        slice_x_pos = int(img.header['dim'][1]/2)
        slice_y_pos = int(img.header['dim'][2]/2)
        slice_z_pos = int(img.header['dim'][3]/2)
        slice_x = img.dataobj[slice_x_pos, :, :, 0]
        slice_y = img.dataobj[:, slice_y_pos, :, 0]
        slice_z = img.dataobj[:, :, slice_z_pos, 0]

        slice_x = fix_level(slice_x).T
        slice_y = fix_level(slice_y).T
        slice_z = fix_level(slice_z).T

        image_x = Image.fromarray(np.flipud(slice_x)).convert('L')
        image_x.save('secondary/x.png')
        image_y = Image.fromarray(np.flipud(slice_y)).convert('L')
        image_y.save('secondary/y.png')
        image_z = Image.fromarray(np.flipud(slice_z)).convert('L')
        image_z.save('secondary/z.png')

    except Exception as e:
        results['errors'].append("failed to validate bold ..  error code: " + str(e))

if not os.path.exists("secondary"):
    os.mkdir("secondary")

validate_func(config['bold'])

if not os.path.exists("output"):
    os.mkdir("output")

# TODO - normalize (for now, let's just symlink)
# TODO - if it's not .gz'ed, I should?
if os.path.lexists("output/bold.nii.gz"):
    os.remove("output/bold.nii.gz")
os.symlink("../"+config['bold'], "output/bold.nii.gz")

#TODO - validate optional stuff
if 'events' in config and os.path.exists(config["events"]):
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

if 'sbref' in config and os.path.exists(config["sbref"]):
    try:
        #TODO - validate sbref?
        if os.path.lexists("output/sbref.nii.gz"):
            os.remove("output/sbref.nii.gz")
        os.symlink("../"+config['sbref'], "output/sbref.nii.gz")
    except Exception as e:
        results['errors'].append("failed to validate sbref ..  error code: " + str(e))

if 'physio' in config and os.path.exists(config["physio"]):
    try:
        #TODO - validate 
        if os.path.lexists("output/physio.tsv.gz"):
            os.remove("output/physio.tsv.gz")
        os.symlink("../"+config['physio'], "physio.tsv.gz")
    except Exception as e:
        results['errors'].append("failed to validate physio.tsv ..  error code: " + str(e))

if 'physio_json' in config and os.path.exists(config["physio_json"]):
    try:
        #TODO - validate 
        if os.path.lexists("output/physio.json"):
            os.remove("output/physio.json")
        os.symlink("../"+config['physio_json'], "physio.json")
    except Exception as e:
        results['errors'].append("failed to validate physio.json ..  error code: " + str(e))

if len(results['errors']) == 0:
    print("all good")
else:
    print(results['errors'])

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
            np.int16, np.int32, np.int64, np.uint8,
            np.uint16, np.uint32, np.uint64)):
            ret = int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            ret = float(obj)
        elif isinstance(obj, (np.ndarray,)): 
            ret = obj.tolist()
        else:
            ret = json.JSONEncoder.default(self, obj)

        if isinstance(ret, (float)):
            if math.isnan(ret):
                ret = None

        if isinstance(ret, (bytes, bytearray)):
            ret = ret.decode("utf-8")

        return ret

with open("product.json", "w") as fp:
    json.dump(results, fp, cls=NumpyEncoder)

print("done")
