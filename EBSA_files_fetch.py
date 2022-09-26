from cartoframes.auth import set_default_credentials
from cartoframes import read_carto, to_carto
import geopandas as gpd
import pandas as pd
import os
from shapely.validation import make_valid
import requests
import re
from bs4 import BeautifulSoup
import glob
import json

from dotenv import load_dotenv
load_dotenv('/home/chemmerly/cred/.env')

data_dir = "data"

#download list of EBSA data urls from https://chm.cbd.int/database
raw_data_file = 'Aichi-Targets-data.csv'

# read in the csv with the urls for the EBSA jsons
url_df = pd.read_csv(raw_data_file,encoding='latin-1')
url_list = url_df['CHM Url']

# regex pattern for the finding a geojson 
match_st = re.compile(r'geojson') 
for url in url_list:
    # scrape the page for the geojson
    r = requests.get(url)  
    c = r.content 
    soup = BeautifulSoup(c)
    for link in soup.findAll('a', attrs={'href': re.compile("geojson$")}):
        href  = link.get('href')
        url = 'https://chm.cbd.int' + href
        # download raw data
        r = requests.get(url)
        j = json.loads(r.content)
        #store data as geojson files
        raw_data_file = os.path.join(data_dir, os.path.basename(url))
        with open(raw_data_file, "w") as file:
            json.dump(j, file)

#create list of geojson data for each ebsa from stored geojson file
ebsa_files = glob.glob(os.path.join(data_dir, '*geojson'))
gdf_list = []
for file in ebsa_files:
    try:
        gdf = gpd.read_file(file)
        gdf_list.append(gdf)
    except Exception:
        print("Could not read " + file)

#create geopandas dataframe of EBSA data from list
gdf_ebsa = gpd.GeoDataFrame(pd.concat(gdf_list))

#store EBSA data locally as shapefiles
gdf_ebsa.to_file('merged_ebsa.shp',driver='ESRI Shapefile')

#upload EBSA data to Carto
gdf_ebsa.columns = [x.lower().replace(' ', '_') for x in gdf_ebsa.columns]
dataset_name = "Ecologically and Biologically Significant Areas"
CARTO_USER = os.getenv('CARTO_WRI_RW_USER')
CARTO_KEY = os.getenv('CARTO_WRI_RW_KEY')
set_default_credentials(username=CARTO_USER, base_url="https://{user}.carto.com/".format(user=CARTO_USER),api_key=CARTO_KEY)
to_carto(gdf_ebsa, dataset_name + '_edit', if_exists='replace')