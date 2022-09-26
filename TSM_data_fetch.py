import os
import urllib
import urllib.request
import ftplib
import logging
import csv
import subprocess
import ee
import sys
from google.cloud import storage
import glob
utils_path = os.path.join(os.path.abspath(os.getenv('PROCESSING_DIR')),'utils')
if utils_path not in sys.path:
    sys.path.append(utils_path)
import util_cloud


from dotenv import load_dotenv
load_dotenv('/home/chemmerly/cred/.env')

# url from which the data is downloaded 
SOURCE_URL = 'ftp://{}:{}@ftp.hermes.acri.fr{}'

# username and password for the ftp service to download data 
ftp_username = os.environ.get('GLOBCOLOUR_USERNAME')
ftp_password = os.environ.get('GLOBCOLOUR_PASSWORD')

#log in to API
ftp = ftplib.FTP('ftp.hermes.acri.fr')
ftp.login(ftp_username, ftp_password)

#set working directory
ftp.cwd('/GLOB/meris/month')

#import list of relevent files (csv downloaded from GlobColour: https://hermes.acri.fr/index.php?class=archive)
with open('high_level_panel/GlobColourList_All.csv', newline='') as f:
    reader = csv.reader(f)
    file_list = list(reader)

files = [x[0] for x in file_list]

#get files from API
for file in files:
    print(file)
    year = file[4:8]
    month = file[8:10]
    url = SOURCE_URL.format(ftp_username,ftp_password,'/'.join([ftp.pwd(), year, month, '01', file]))
    try:
        # try to download the data
        urllib.request.urlretrieve(url, file)
    except Exception as e:
        # if unsuccessful, log an error that the file was not downloaded
        logging.error('Unable to retrieve data from {}'.format(url))
        logging.debug(e)

#convert files from .nc to .tif
for file in files:
    sds_path = f'NETCDF:{file}:TSM_mean'
    sds_tif = f'TSM_{file[4:12]}.tif'
    cmd = ['gdal_translate','-q', '-a_srs', 'EPSG:4326',  sds_path, sds_tif]
    completed_process = subprocess.run(cmd, shell=False)

#get list of tif files
TSM_files = glob.glob('*.tif')

#Upload tif files to GEE
COLLECTION = '/projects/resource-watch-gee/ocn_011_nrt_total_suspended_matter'
GS_FOLDER = COLLECTION[1:]
auth = ee.ServiceAccountCredentials(os.getenv('GEE_SERVICE_ACCOUNT'), os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
ee.Initialize(auth)

gcsClient = storage.Client(os.environ.get("CLOUDSDK_CORE_PROJECT"))
gcsBucket = gcsClient.bucket(os.environ.get("GEE_STAGING_BUCKET"))

for i in range(24):
    # upload files to Google Cloud Storage
    gcs_uri= util_cloud.gcs_upload(TSM_files[i], 'ocn_011_nrt_total_suspended_matter', gcs_bucket=gcsBucket)
    # generate an asset name for the current file by using the filename (minus the file type extension)
    file_name=TSM_files[i].split('.')[0].split('/')[0]
    asset_name = f'projects/resource-watch-gee/ocn_011_nrt_total_suspended_matter/tsm_month/{file_name}' 
    # create the band manifest for this asset
    mf_bands = [{'id': 'b1', 'tileset_band_index': 0, 'tileset_id': file_name,'pyramidingPolicy': 'MEAN'}]  
    # create complete manifest for asset upload
    manifest = util_cloud.gee_manifest_complete(asset_name, gcs_uri[0], mf_bands)
    # upload the file from Google Cloud Storage to Google Earth Engine
    task = util_cloud.gee_ingest(manifest)
    print(asset_name + ' uploaded to GEE')
