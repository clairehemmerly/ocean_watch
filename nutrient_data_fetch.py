import os
import sys
import subprocess
import urllib
import urllib.request
import ftplib
import shlex
import ee
from google.cloud import storage
utils_path = os.path.join(os.path.abspath(os.getenv('PROCESSING_DIR')),'utils')
if utils_path not in sys.path:
    sys.path.append(utils_path)
import util_cloud
import glob

from dotenv import load_dotenv
load_dotenv('/home/chemmerly/cred/.env')

ftp_username = os.environ.get('CMEMS_USERNAME')
ftp_password = os.environ.get('CMEMS_PASSWORD')

#login to access forecast data - currently accessing 2022 data, update year as necessary
ftp = ftplib.FTP('nrt.cmems-du.eu')
ftp.login(ftp_username, ftp_password)
ftp.cwd('/Core/GLOBAL_ANALYSIS_FORECAST_BIO_001_028/global-analysis-forecast-bio-001-028-{}/{}'.format('monthly', '2022'))
SOURCE_URL = 'ftp://{}:{}@nrt.cmems-du.eu{}'

#login to access hindcast data - currently accessing 2002 data, update year as necessary
ftp = ftplib.FTP('my.cmems-du.eu')
ftp.login(ftp_username, ftp_password)
ftp.cwd('/Core/GLOBAL_MULTIYEAR_BGC_001_029/cmems_mod_glo_bgc_my_0.25_P1M-m/2002')
SOURCE_URL = 'ftp://{}:{}@my.cmems-du.eu{}'

nutrient_files = list(ftp.nlst())

for file in nutrient_files:
    #login to API during loop to prevent time out, change to appropriate log in for forecast or hindcast
    year = file[-9:-5]
    ftp = ftplib.FTP('my.cmems-du.eu')
    ftp.login(ftp_username, ftp_password)
    ftp.cwd(f'/Core/GLOBAL_MULTIYEAR_BGC_001_029/cmems_mod_glo_bgc_my_0.25_P1M-m/{year}')
    url = SOURCE_URL.format(ftp_username,ftp_password,'/'.join([ftp.pwd(), file]))
    raw_data_file = os.path.join(os.path.basename(url))
    try:
        urllib.request.urlretrieve(url, raw_data_file)
    except:
        print(f'did not get {file}')

#Convert data to tif files and upload to GEE
auth = ee.ServiceAccountCredentials(os.getenv('GEE_SERVICE_ACCOUNT'), os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
ee.Initialize(auth)
gcsClient = storage.Client(os.environ.get("CLOUDSDK_CORE_PROJECT"))
gcsBucket = gcsClient.bucket(os.environ.get("GEE_STAGING_BUCKET"))

sds = ['no3', 'po4','o2']
files_to_upload = glob.glob('*.nc')

for file in files_to_upload:
    for nutrient in sds:
        # should be of the format 'NETCDF:"filename.nc":variable'
        sds_path = f'NETCDF:{file}:{nutrient}'
        # generate a name to save the raw tif file we will translate the netcdf file's subdataset into
        raw_sds_tif = '{}_{}.tif'.format(os.path.splitext(file)[0], sds_path.split(':')[-1])
        # create the gdal command and run it to convert the netcdf to tif
        cmd = ['gdal_translate','-q', '-a_srs', 'EPSG:4326',  sds_path, raw_sds_tif, '-b', '1', '-b','2', '-b','3', '-b', '4', '-b', '5']
        completed_process = subprocess.run(cmd, shell=False)
        # generate a name to save the processed tif file
        processed_sds_tif = '{}_{}_edit.tif'.format(os.path.splitext(file)[0], sds_path.split(':')[-1])
        # create the gdal command and run it to average pixel values
        cmd = 'gdal_calc.py -A ' + raw_sds_tif +' -B ' + raw_sds_tif + ' -C ' + raw_sds_tif + ' -D ' + raw_sds_tif +' -E ' + raw_sds_tif + ' --A_band=1 --B_band=2 --C_band=3 --D_band=4 --E_band=5 --outfile=' + processed_sds_tif + ' --calc="numpy.average((A,B,C,D,E), axis = 0)" --NoDataValue=-9.96920996838686905e+36 --overwrite'
        # format to command line
        posix_cmd = shlex.split(cmd, posix=True)
        completed_process= subprocess.check_call(posix_cmd)

        # upload files to Google Cloud Storage
        gcs_uri= util_cloud.gcs_upload(processed_sds_tif, 'ocn_020_nrt_rw0_nutrient_concentration', gcs_bucket=gcsBucket)
    
        # generate an asset name for the current file by using the filename (minus the file type extension)
        file_name=processed_sds_tif.split('.')[0].split('/')[0]
        asset_name = f'projects/resource-watch-gee/ocn_020_nrt_rw0_nutrient_concentration/{nutrient}_concentration/{file_name}'
    
        # create the band manifest for this asset
        #tileset_id= data_dict['processed_data_file'][i].split('.')[0]
        mf_bands = [{'id': 'b1', 'tileset_band_index': 0, 'tileset_id': file_name,'pyramidingPolicy': 'MEAN'}]
  
        # create complete manifest for asset upload
        manifest = util_cloud.gee_manifest_complete(asset_name, gcs_uri[0], mf_bands)
    
        # upload the file from Google Cloud Storage to Google Earth Engine
        task = util_cloud.gee_ingest(manifest)
        print(asset_name + ' uploaded to GEE')


