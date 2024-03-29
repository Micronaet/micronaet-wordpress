import os
import woocommerce
import pickle
import urllib
import sys
import erppeek
import ConfigParser
import shutil
import pdb
import requests


# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
# From config file:
cfg_file = os.path.expanduser('../wordpress.cfg')
config = ConfigParser.ConfigParser()

config.read([cfg_file])
image_path = config.get('wordpress', 'path')

double = []
pdb.set_trace()
for root, folders, files in os.walk(image_path):
    for filename in files:
        if not filename.endswith('jpg'):
            print('[ERROR] No JPG: %s' % filename)
            continue

        if '-' not in filename:
            print('[ERROR] Not -: %s' % filename)
            continue

        name_split = filename[:-4].split('-')
        if len(name_split) != 2:
            print('[ERROR] More -, jumped: %s' % filename)
            continue

        destination_file = '%s.jpg' % name_split[0]

        if destination_file not in double:
            origin = os.path.join(root, filename)
            destination = os.path.join(root, destination_file)
            print('[INFO] Move %s in %s' % (
                filename, destination_file
                ))
            double.append(destination_file)
            shutil.move(origin, destination)
