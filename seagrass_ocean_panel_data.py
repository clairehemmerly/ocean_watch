import geopandas as gpd
from cartoframes.auth import set_default_credentials
from cartoframes import to_carto
import os
import sys
import glob

from dotenv import load_dotenv
load_dotenv('/home/chemmerly/cred/.env')

CARTO_USER = os.getenv('CARTO_WRI_RW_USER')
CARTO_KEY = os.getenv('CARTO_WRI_RW_KEY')
set_default_credentials(username=CARTO_USER, base_url="https://{user}.carto.com/".format(user=CARTO_USER),api_key=CARTO_KEY)

#import seagrass data - seagrass data downloaded from carto
seagrass = gpd.read_file('high_level_panel/seagrass/bio_045_seagrass_polygons.gpkg')

#iso3 codes for countries in ocean panel
country_list = ['IDN', 'GBR', 'CAN', 'USA', 'CHL', 'NOR', 'FRA', 'PRT', 'GHA', 'NAM', 'KEN', 'MEX', 'AUS', 'JPN', 'FJI', 'JAM', 'PLW']
#countries that had no seagrass: NAM, PRT, CHL

#modify dataset for only countries of interest so that each polygon is its own row
#loop doesn't really work because you need to reduce the number of polygons for most countries by dissolving in QGIS
seagrass_polygons = gpd.GeoDataFrame()
for iso3 in country_list:
    #filter for country of interest
    country = seagrass[seagrass['iso3'] == iso3]
    #get number of unique polygons (dataset has redundant shapes with different metadata)
    unique_polygons = country['gis_area_k'].value_counts()
    #create df of just unique polygons
    country_seagrass = gpd.GeoDataFrame()
    for i in range(len(unique_polygons)):
        polygon = country[country['gis_area_k'] == unique_polygons.index[i]].iloc[0]
        country_seagrass = country_seagrass.append(polygon)
    #split multipolygons into individual polygons and create list of all polygons
    country_seagrass_polygons = []
    for i in range(len(country_seagrass)):
        polygons = list(country_seagrass['geometry'].iloc[i])
        country_seagrass_polygons += polygons
    #create df from list of polygon and create an index to be shown in GEE
    country_seagrass_df = gpd.GeoDataFrame(country_seagrass_polygons, columns = ['geometry'])
    country_seagrass_df['country'] = iso3
    #append country to seagrass df
    seagrass_polygons = seagrass_polygons.append(country_seagrass_df)


##CODE BLOCK FOR DISSOLVING IN QGIS##

for iso3 in country_list:
    #filter for country of interest
    print(iso3)
    country = seagrass[seagrass['iso3'] == iso3]
    print(len(country))
    #get number of unique polygons (dataset has redundant shapes with different metadata)
    unique_polygons = country['gis_area_k'].value_counts()
    print(len(unique_polygons))
    #create df of just unique polygons
    country_seagrass = gpd.GeoDataFrame()
    for i in range(len(unique_polygons)):
        polygon = country[country['gis_area_k'] == unique_polygons.index[i]].iloc[0]
        country_seagrass = country_seagrass.append(polygon)
    print(len(country_seagrass))

    #split multipolygons into individual polygons and create list of all polygons
    country_seagrass_polygons = []
    for i in range(len(country_seagrass)):
        polygons = list(country_seagrass['geometry'].iloc[i].geoms)
        country_seagrass_polygons += polygons
    print(len(country_seagrass_polygons))

    #create df from list of polygon 
    country_seagrass_df = gpd.GeoDataFrame(country_seagrass_polygons, columns = ['geometry'])
    country_seagrass_df['iso3'] = iso3
    country_seagrass_df = country_seagrass_df[['iso3', 'geometry']]

    #create shapefile to dissolve in QGIS
    try:
        country_seagrass_df.to_file(f'high_level_panel/seagrass/to_dissolve/seagrass_{iso3}_polygons.shp',driver='ESRI Shapefile')
    except:
        print(f'{iso3} has no seagrass polygons')

#load shapefile into QGIS and dissolve polygons by location (manually selected) and save layers to gpkg
#countries that did not require merging: GHA, JAM
#countries that had no seagrass: NAM, PRT, CHL

#load dissloved files
diss_files = glob.glob('*.gpkg')

#load dissolved polygons into df
seagrass_polygons = gpd.GeoDataFrame()
for file in diss_files:
    print(file)
    country_seagrass_df = gpd.read_file(file)
    if 'layer' in country_seagrass_df:
        country_seagrass_df.drop(['layer', 'path'], axis=1, inplace=True)
    country_seagrass_df.reset_index(inplace=True)
    country_seagrass_df.rename(columns = {'index': 'GEE_index'}, inplace=True)
    seagrass_polygons = seagrass_polygons.append(country_seagrass_df)

#add data for GHA and JAM that were not worked with in QGIS
GHA = seagrass[seagrass['iso3'] == 'GHA']
GHA_seagrass_polygons = []
for i in range(len(GHA)):
    polygons = list(GHA['geometry'].iloc[i].geoms)
    GHA_seagrass_polygons += polygons
GHA_seagrass_df = gpd.GeoDataFrame(GHA_seagrass_polygons, columns = ['geometry'])
GHA_seagrass_df['iso3'] = "GHA"
GHA_seagrass_df = GHA_seagrass_df[['iso3', 'geometry']]
GHA_seagrass_df.reset_index(inplace=True)
GHA_seagrass_df.rename(columns = {'index': 'GEE_index'}, inplace=True)

seagrass_polygons = seagrass_polygons.append(GHA_seagrass_df)

JAM = seagrass[seagrass['iso3'] == 'JAM']
JAM_seagrass_polygons = []
for i in range(len(JAM)):
    polygons = list(JAM['geometry'].iloc[i].geoms)
    JAM_seagrass_polygons += polygons
JAM_seagrass_df = gpd.GeoDataFrame(JAM_seagrass_polygons, columns = ['geometry'])
JAM_seagrass_df['iso3'] = "JAM"
JAM_seagrass_df = JAM_seagrass_df[['iso3', 'geometry']]
JAM_seagrass_df.reset_index(inplace=True)
JAM_seagrass_df.rename(columns = {'index': 'GEE_index'}, inplace=True)

seagrass_polygons = seagrass_polygons.append(JAM_seagrass_df)
    
seagrass_polygons.to_file('high_level_panel/seagrass/seagrass_ocean_panel.shp',driver='ESRI Shapefile') #upload this file to GEE

#GEE would not upload because feature #81 had too many vertices
#reduce number vertices with following code block
seagrass_polygons = gpd.read_file('high_level_panel/seagrass/seagrass_ocean_panel.shp')

#check number of exterior coordinates at index position 81
num_coords = 0
for i in range(len(seagrass_polygons['geometry'].iloc[81].geoms)):
    num_coords += len(seagrass_polygons['geometry'].iloc[81].geoms[i].exterior.coords)

#simplify geometry at index position 81
seagrass_polygons.at[81, 'geometry'] = seagrass_polygons['geometry'].iloc[81].simplify(1)

#check new number of exterior coordinates at index position 81
num_coords = 0
for i in range(len(seagrass_polygons['geometry'].iloc[81].geoms)):
    num_coords += len(seagrass_polygons['geometry'].iloc[81].geoms[i].exterior.coords)

#resave file and upload to GEE
seagrass_polygons.to_file('high_level_panel/seagrass/seagrass_ocean_panel.shp',driver='ESRI Shapefile')

#upload seagrass df to carto
to_carto(seagrass_polygons, 'bio_045_seagrass_ocean_panel', if_exists='replace')

#USA and FRA would not run in GEE - work with shapefile for these countries individually
seagrass_USA = gpd.read_file('high_level_panel/seagrass/seagrass_country/seagrass_USA.gpkg')
seagrass_USA.drop(['layer', 'path'], axis=1, inplace=True)
seagrass_USA.reset_index(inplace=True)
seagrass_USA.rename(columns = {'index': 'GEE_index'}, inplace=True)
seagrass_USA['geometry'] = seagrass_USA['geometry'].simplify(1)
seagrass_USA.to_file('high_level_panel/seagrass/seagrass_USA.shp',driver='ESRI Shapefile')

seagrass_FRA = gpd.read_file('high_level_panel/seagrass/seagrass_country/seagrass_FRA.gpkg')
seagrass_FRA.drop(['layer', 'path'], axis=1, inplace=True)
seagrass_FRA.reset_index(inplace=True)
seagrass_FRA.rename(columns = {'index': 'GEE_index'}, inplace=True)
seagrass_FRA['geometry'] = seagrass_FRA['geometry'].simplify(1)
seagrass_FRA.to_file('high_level_panel/seagrass/seagrass_FRA.shp',driver='ESRI Shapefile')
