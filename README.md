# Ocean Watch
This repository contains the scripts for my projects as the ocean watch intern at World Resources Institute, summer 2022.

## EBSA Project
Ecologically and Biologically Significant Areas (EBSAs) are areas of the oceans that have been designated as critical for overall ocean health. Only a small percentage of these areas are currently protected as part of global marine protected areas (MPAs). The goal of this project was to use the shapefiles of EBSAs and MPAs to create a data visualization of the fraction of EBSAs that are protected.

The EBSA shapefiles were scraped from the [The Clearing-House Mechanism of the Convention on Biological Diversity](https://chm.cbd.int/database).

The MPA shapefiles were obtained from internal WRI data storage.

A python script using the geopandas library was created to clean the shapefiles and find the relevant intersections.

[EBSA_files_fetch.py](https://github.com/clairehemmerly/ocean_watch/blob/main/EBSA_files_fetch.py): Script to scrape data from CHM

[EBSA_interseactions.py](https://github.com/clairehemmerly/ocean_watch/blob/main/EBSA_intersections.py): Script to determine the intersecting shapefiles.

## Coastal Pollution Project
The goal of this project was to identify sensitive ecosystems exposed to increasing levels of pollution to inform priority areas for policy intervention. Coastal nutrient and total suspended matter (TSM) levels were analyzed with time over the location of seagrass beds. 

[TSM_data_fetch.py](https://github.com/clairehemmerly/ocean_watch/blob/main/TSM_data_fetch.py): Script to pull total suspended matter data from the [GlobColour](https://hermes.acri.fr/index.php?class=archive) API

[nutrient_data_fetch.py](https://github.com/clairehemmerly/ocean_watch/blob/main/nutrient_data_fetch.py): Script to pull nitrogen, phosphate, and oxygen data from the [Copernicus Marine Service](https://marine.copernicus.eu/) API
 
