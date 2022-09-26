import geopandas as gpd
import pandas as pd
from cartoframes.auth import set_default_credentials
from cartoframes import to_carto
import os
from shapely.validation import make_valid

CARTO_USER = os.getenv('CARTO_WRI_RW_USER')
CARTO_KEY = os.getenv('CARTO_WRI_RW_KEY')
set_default_credentials(username=CARTO_USER, base_url="https://{user}.carto.com/".format(user=CARTO_USER),api_key=CARTO_KEY)

#export exclusive economic zone (EEZ) and marine protected area (MPA) data from Carto as gpkg and load
#EEZ Carto table: com_011_rw1_maritime_boundaries_edit
eez = gpd.read_file('com_011_rw1_maritime_boundaries_edit.gpkg')
#MPA Carto table: bio_007b_rw0_marine_protected_area_polygon_edit
mpa = gpd.read_file('bio_007b_rw0_marine_protected_area_polygon_edit.gpkg')

#clean mpa polygons and store valid files locally
for i, row in mpa.iterrows():
    if not row['geometry'].is_valid:
        mpa.at[i, 'geometry'] = make_valid(mpa.loc[i]['geometry'])
mpa.to_file("mpa_valid.gpkg", driver="GPKG")
mpa = gpd.read_file('mpa_valid.gpkg')

#load data ebsa data from local file or export from Carto (Carto table: Ecologically and Biologically Significant Areas)
gdf_ebsa = gpd.read_file('merged_ebsa.shp')

#dissolve EBSAs
gdf_ebsa['dissolve'] = 1
ebsa_dis = gdf_ebsa.dissolve('dissolve')

#find index positions of eezs that intersect with ebsa
eez_indexes = []
for i, row in eez.iterrows():
    if row['the_geom'].intersects(ebsa_dis['geometry'][1]):
        eez_indexes.append(i)

#create dataframe of just eezs that intersect with ebsas and save locally
eez_ebsa_intersect = eez.loc[eez_indexes].copy()
eez_ebsa_intersect.to_file('eez_ebsa.shp',driver='ESRI Shapefile') 
eez_ebsa_intersect = gpd.read_file('EBSA/eez_ebsa.shp')

#filter df with intersections between eez and ebsa for pol_type 200NM
eez_ebsa_intersect_200NM = eez_ebsa_intersect[eez_ebsa_intersect['pol_type'] == '200NM'].copy()

#get eez/ebsa intersection polygon and set as geopandas dateframe geometry
eez_ebsa_intersect_200NM['ebsa_polygon'] = eez_ebsa_intersect_200NM['geometry'].intersection(ebsa_dis['geometry'][0])
eez_ebsa_200NM = eez_ebsa_intersect_200NM.drop('geometry', axis = 1)
eez_ebsa_200NM = eez_ebsa_200NM.rename(columns={'ebsa_polygon': 'geometry'})
eez_ebsa_200NM.set_geometry(col='geometry', inplace=True)

#drop countries where ebsas only borders eez
countries = ['United States Exclusive Economic Zone', 
    'Tristan Da Cunha Exclusive Economic Zone', 
    'United States Exclusive Economic Zone (Hawaii)', 
    'Canadian Exclusive Economic Zone', 
    'Greenlandic Exclusive Economic Zone', 
    'United States Exclusive Economic Zone (Alaska)']
eez_index = [eez_ebsa_200NM[eez_ebsa_200NM['geoname'] == name].index for name in countries]
eez_ebsa_200NM = eez_ebsa_200NM.drop(eez_index)

#dissolve eez_ebsa df by country to check for intersections with mpa
eez_ebsa_dis = eez_ebsa_200NM.dissolve('iso_ter1')
eez_ebsa_dis = eez_ebsa_dis.reset_index()

#store dissolved eez_ebsa intersection locally and backup to Carto
eez_ebsa_dis.to_file('EBSA/eez_ebsa_dis.gpkg',driver='GPKG')
to_carto(eez_ebsa_dis, 'ebsa_in_eez_dissolved', if_exists='replace')

#identify territories to check for mpas
territories = eez_ebsa_200NM['iso_ter1'].unique()
territories = list(filter(lambda item: item is not None, territories))

#set dissolve to separate fully protected areas (no_take) and partially protected
mpa['dissolve'] = 1
mpa.loc[mpa['no_take'] == 'All', 'dissolve'] = 2

#find intersections between ebsa, eez, and mpa
mpa_list_iso3 = []
for t in territories:
    print(t)
    #filter mpa df for current territory
    sub_mpa = mpa[mpa['iso3'] == t].copy()
    #check if mpa polygons for territory intersect with polygons of eez/ebsa intersections
    sub_mpa['intersects'] = sub_mpa['geometry'].intersects(eez_ebsa_dis['geometry'][t])
    #dissolve mpas that intersect into single polygon
    mpa_dis = sub_mpa[sub_mpa['intersects'] == True].dissolve('dissolve')
    #add df of dissolved mpa to list
    mpa_list_iso3.append(mpa_dis)

#create df of intersections and clean
mpa_by_iso3 = gpd.GeoDataFrame(pd.concat(mpa_list_iso3))
mpa_by_iso3 = mpa_by_iso3.reset_index()

#add intersections with eez_ebsa areas without iso_ter1 value that were missed above
print(eez_ebsa_200NM[eez_ebsa_200NM['iso_ter1'].isna()]['geoname'])
rows = eez_ebsa_200NM[eez_ebsa_200NM['iso_ter1'].isna()]['geoname'].index
iso_assignments = {1: 'PYF', 111: 'CHL', 126: 'ZAF', 179: 'ECU'}
for i in rows:
    eez_ebsa_200NM.at[i, 'iso_ter1'] = iso_assignments[i]

additional_mpas = []
for key, value in iso_assignments.items():
    sub_mpa = mpa[mpa['iso3'] == value].copy()
    sub_mpa['intersects'] = sub_mpa['geometry'].intersects(eez_ebsa_200NM['geometry'].loc[key])
    mpa_dis = sub_mpa[sub_mpa['intersects'] == True].dissolve('dissolve')
    additional_mpas.append(mpa_dis)

tot_mpas = mpa_list_iso3 + additional_mpas
mpa_intersects = gpd.GeoDataFrame(pd.concat(tot_mpas))
mpa_intersects = mpa_intersects.reset_index()

#separate into types of mpa
fully_protected = mpa_intersects[mpa_intersects['dissolve'] == 2].copy()
part_protected = mpa_intersects[mpa_intersects['dissolve'] == 1].copy()

#dissolve to find intersection polygons
fully_protected = fully_protected.dissolve('dissolve')
part_protected = part_protected.dissolve('dissolve')

#find intersection polygons
eez_ebsa_dis['full_prot'] = eez_ebsa_dis['geometry'].intersection(fully_protected['geometry'][2])
eez_ebsa_dis['part_prot'] = eez_ebsa_dis['geometry'].intersection(part_protected['geometry'][1])

#create df of just intersecting polygons to upload to carto
cols_to_drop = ['geometry', 'cartodb_id', 'mrgid', 'geoname', 'mrgid_ter1', 
        'pol_type', 'mrgid_sov1', 'territory1', 'sovereign1', 'mrgid_ter2',
        'mrgid_sov2', 'territory2', 'iso_ter2', 'sovereign2', 'mrgid_ter3',
        'mrgid_sov3', 'territory3', 'iso_ter3', 'sovereign3', 'x_1', 'y_1',
        'mrgid_eez', 'area_km2', 'iso_sov1', 'iso_sov2', 'iso_sov3', 'un_sov1',
        'un_sov2', 'un_sov3', 'un_ter1', 'un_ter2', 'un_ter3']

fully_prot_areas = eez_ebsa_dis.copy()
fully_prot_areas = fully_prot_areas.drop(cols_to_drop, axis=1)
fully_prot_areas = fully_prot_areas.drop('part_prot', axis=1)
empty_index  = fully_prot_areas[fully_prot_areas['full_prot'].is_empty].index
fully_prot_areas = fully_prot_areas.drop(empty_index)
fully_prot_areas = fully_prot_areas.rename(columns={'full_prot': 'geometry'})
fully_prot_areas.set_geometry(col='geometry', inplace=True)

to_carto(fully_prot_areas, 'mpa_intersect_fully', if_exists='replace')
fully_prot_areas.to_file('EBSA/fully_protected.gpkg',driver='GPKG')

partly_prot_areas = eez_ebsa_dis.copy()
partly_prot_areas = partly_prot_areas.drop(cols_to_drop, axis=1)
partly_prot_areas = partly_prot_areas.drop('full_prot', axis=1)
empty_index  = partly_prot_areas[partly_prot_areas['part_prot'].is_empty].index
partly_prot_areas = partly_prot_areas.drop(empty_index)
partly_prot_areas = partly_prot_areas.rename(columns={'part_prot': 'geometry'})
partly_prot_areas.set_geometry(col='geometry', inplace=True)

to_carto(partly_prot_areas, 'mpa_intersect_partly', if_exists='replace')
partly_prot_areas.to_file('EBSA/partly_protected.gpkg',driver='GPKG')



