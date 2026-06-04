"""
ESS-DIVE Dataset Scraper

Fetches and filters environmental datasets from the ESS-DIVE API:
1. Downloads metadata for all public packages and Watershed Function SFA datasets
2. Extracts spatial coordinates from metadata
3. Filters by East River watershed bounding box
4. Identifies soil/subsurface datasets
5. Downloads selected data files

Requires: ESS-DIVE API token from https://ess-dive.lbl.gov/
"""

# %%[markdown]
## Load packages

# %%
import os
import json
import asyncio
from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd
import requests
import aiohttp
# %%[markdown]
## Environment and fetch setup
# %%
token = "[insert ess-dive api token here]"  # Get from https://ess-dive.lbl.gov/
base = "https://api.ess-dive.lbl.gov/"
header_authorization = "bearer {}".format(token)
endpoint = "packages"

# %%[markdown]
## Fetch all public package headers from ESS-DIVE

# %%
# Paginate through all public packages (batches of 100)
resp = []
i = 1
while i < 1500:
    get_packages_url = "{}{}?isPublic=true&pageSize=100&rowStart={}".format(base, endpoint, i)
    get_packages_response = requests.get(get_packages_url, headers={"Authorization": header_authorization})
    resp.append(get_packages_response.json())
    i = i + 100
    print(i)

# %%
# Extract package metadata from paginated responses
pkg_meta = []
for r in resp:
    p_meta = r.get('result')
    pkg_meta.extend(p_meta)

pkg_meta[0]

# %%
# Save package IDs and DOIs for later reference
ids = [p['id'] for p in pkg_meta]
dois = [p['dataset']['@id'] for p in pkg_meta]

with open('../data/external/ess-dive_dois.txt', 'w', newline='') as f:
    for line in dois:
        f.write(f'{line}\n')

with open('../data/external/ess-dive_ids.txt', 'w', newline='') as f:
    for line in ids:
        f.write(f'{line}\n')


# %%[markdown]
## Fetch Watershed Function SFA datasets specifically

# %%
providerName = "\"Watershed Function SFA\""

sfa_portal_pkg_meta = []
resp = []
i = 1
while i < 200:
    get_packages_url = "{}{}?isPublic=true&pageSize=100&rowStart={}&providerName={}".format(
        base, endpoint, i, providerName
    )
    get_packages_response = requests.get(get_packages_url, headers={"Authorization": header_authorization})
    resp.append(get_packages_response.json())
    i = i + 100
    print(i)

# %%
# Extract SFA package metadata
for r in resp:
    p_meta = r.get('result')
    sfa_portal_pkg_meta.extend(p_meta)

# %%
# Save SFA package IDs and DOIs
sfa_ids = [p['id'] for p in sfa_portal_pkg_meta]
sfa_dois = [p['dataset']['@id'] for p in sfa_portal_pkg_meta]

with open('../data/external/ess-dive_sfa_portal_dois.txt', 'w', newline='') as f:
    for line in sfa_dois:
        f.write(f'{line}\n')

with open('../data/external/ess-dive_sfa_portal_ids.txt', 'w', newline='') as f:
    for line in sfa_ids:
        f.write(f'{line}\n')

# %%[markdown]
## Pull full metadata for each package and save as JSON

# %%
# Serial version (slow, preserved for reference)
resp = []
i = 1
for id in sfa_ids:
    get_packages_url = "{}{}/{}?isPublic=true&pageSize=100&rowStart={}".format(base, endpoint, id, i)
    get_packages_response = requests.get(get_packages_url, headers={"Authorization": header_authorization})
    resp.append(get_packages_response.json())
    with open('../data/external/ess-dive_meta/ess-dive_meta_{}.json'.format(id), 'w') as f:
        json.dump(get_packages_response.json(), f, indent=2)
    print(id)

# %%
# Async version: 10x faster for bulk metadata downloads
async def fetch_and_save(session, semaphore, id, results):
    url = "{}{}/{}?isPublic=true&pageSize=100&rowStart=1".format(base, endpoint, id)
    async with semaphore:
        async with session.get(url, headers={"Authorization": header_authorization}) as response:
            data = await response.json()
        results.append(data)
        with open('../data/external/ess-dive_meta/ess-dive_meta_{}.json'.format(id), 'w') as f:
            json.dump(data, f, indent=2)
        print(id)


async def fetch_all(ids_subset):
    semaphore = asyncio.Semaphore(10)  # Rate limit: max 10 concurrent requests
    results = []
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_and_save(session, semaphore, id, results) for id in ids_subset]
        await asyncio.gather(*tasks)
    return results


# %%
# Fetch metadata for all packages (or SFA-only subset)
resp_all = asyncio.run(fetch_all(ids))
resp_sfa = asyncio.run(fetch_all(sfa_ids))

# %%
def read_json_directory_pathlib(directory_path):
    """Load all JSON files from a directory."""
    all_json_data = []
    p = Path(directory_path)

    for file_path in p.glob('*.json'):
        with open(file_path, 'r') as f:
            data = json.load(f)
            print(data)
            all_json_data.append(data)

    return all_json_data


# %%
essd_meta_jsons = read_json_directory_pathlib('../data/external/ess-dive_meta')


# %%[markdown]
## Build spatial dataframe from metadata
# %%
def build_spatial_dataframe(data_list):
    """
    Build a DataFrame of geospatial points from ESS-DIVE metadata.

    Recursively searches for spatialCoverage fields in metadata and extracts
    coordinates. Returns DataFrame with columns: id, doi, geo_name, latitude, longitude.
    Drops rows with missing coordinates and removes duplicates.
    """
    rows = []

    def _process_geo(geo_obj, top_id, top_dataset_at_id):
        if geo_obj is None:
            return
        if isinstance(geo_obj, list):
            for g in geo_obj:
                _process_geo(g, top_id, top_dataset_at_id)
            return
        if not isinstance(geo_obj, dict):
            return

        name = geo_obj.get('name') or geo_obj.get('label')
        lat = geo_obj.get('latitude') or geo_obj.get('lat')
        lon = geo_obj.get('longitude') or geo_obj.get('lon')

        rows.append({
            'id': top_id,
            'dataset@id': top_dataset_at_id,
            'geo_name': name,
            'latitude': lat,
            'longitude': lon,
        })

    def _process_spatial(spatial_obj, top_id, top_dataset_at_id):
        if spatial_obj is None:
            return
        if isinstance(spatial_obj, list):
            for s in spatial_obj:
                _process_spatial(s, top_id, top_dataset_at_id)
            return
        if isinstance(spatial_obj, dict):
            # Prefer explicit `geo` key, but if absent treat the object itself
            # as a geo-like object (some metadata structures do this).
            geo = spatial_obj.get('geo') or spatial_obj.get('Geo')
            if geo is not None:
                _process_geo(geo, top_id, top_dataset_at_id)
            else:
                _process_geo(spatial_obj, top_id, top_dataset_at_id)

    def _recurse(obj, top_id, top_dataset_at_id):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == 'spatialCoverage':
                    _process_spatial(v, top_id, top_dataset_at_id)
                else:
                    _recurse(v, top_id, top_dataset_at_id)
        elif isinstance(obj, list):
            for item in obj:
                _recurse(item, top_id, top_dataset_at_id)

    for entry in data_list:
        top_id = entry.get('id') if isinstance(entry, dict) else None
        dataset_at_id = None
        if isinstance(entry, dict):
            ds = entry.get('dataset')
            if isinstance(ds, dict):
                dataset_at_id = ds.get('@id')

        _recurse(entry, top_id, dataset_at_id)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df = df.dropna(subset=['latitude', 'longitude'])
    df = df.drop_duplicates(subset=['id', 'dataset@id', 'geo_name', 'latitude', 'longitude'])
    df = df.rename(columns={'dataset@id': 'doi'})
    df = df[['id', 'doi', 'geo_name', 'latitude', 'longitude']]

    return df

# %%
df_spatial = build_spatial_dataframe(essd_meta_jsons)


# %%[markdown]
## Filter datasets by geographic bounding box

# %%
def subset_df_by_bbox(df, nw, se):
    """Filter spatial dataframe to points within a bounding box."""
    lat_min = min(nw[0], se[0])
    lat_max = max(nw[0], se[0])
    lon_min = min(nw[1], se[1])
    lon_max = max(nw[1], se[1])

    mask = (
        (df['latitude'] >= lat_min) & (df['latitude'] <= lat_max) &
        (df['longitude'] >= lon_min) & (df['longitude'] <= lon_max)
    )
    return df[mask].copy()


# %%
# East River watershed bounding box
er_nw = [39.308639, -107.478222]
er_se = [38.185027, -105.939319]

df_er = subset_df_by_bbox(df_spatial, er_nw, er_se)
list(df_er['doi'].unique())

# %%
# Save East River DOIs
with open('../data/processed/ess-dive_eastriver_dois.txt', 'w', newline='') as f:
    for line in list(df_er['doi'].unique()):
        f.write(f'{line}\n')

# %%
with open('../data/processed/ess-dive_eastriver_dois.txt', 'r') as f:
    er_dois = [line.strip() for line in f]

# %%
# Combine East River spatial + SFA portal datasets
er_sfa_dois = list(set(er_dois + sfa_dois))

with open('../data/processed/ess-dive_eastriver_sfa_dois.txt', 'w', newline='') as f:
    for line in er_sfa_dois:
        f.write(f'{line}\n')

# %%
er_meta = [j for j in essd_meta_jsons if j.get('dataset')['@id'] in er_sfa_dois]


# %%[markdown]
## Filter for soil-related datasets
def find_soil_observations(data_list):
    """
    Find datasets containing soil or subsurface keywords.

    Searches name, description, keywords, and variableMeasured fields for
    'soil' or 'subsurface' terms (case-insensitive). Returns DataFrame with
    columns: id, doi, name, matched_fields.
    """
    TERMS = {'soil', 'subsurface'}

    def _contains_term(value):
        if isinstance(value, str):
            lower = value.lower()
            return any(t in lower for t in TERMS)
        return False

    def _check_field(value):
        if isinstance(value, str):
            return _contains_term(value)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and _contains_term(item):
                    return True
                if isinstance(item, dict):
                    for sub_val in item.values():
                        if isinstance(sub_val, str) and _contains_term(sub_val):
                            return True
        return False

    rows = []

    for entry in data_list:
        if not isinstance(entry, dict):
            continue

        top_id = entry.get('id')
        dataset = entry.get('dataset') if isinstance(entry.get('dataset'), dict) else {}
        doi = dataset.get('@id')

        name = dataset.get('name')
        description = dataset.get('description')
        keywords = dataset.get('keywords')
        variable_measured = dataset.get('variableMeasured')

        matched = []
        if _check_field(name):
            matched.append('name')
        if _check_field(description):
            matched.append('description')
        if _check_field(keywords):
            matched.append('keywords')
        if _check_field(variable_measured):
            matched.append('variableMeasured')

        if matched:
            rows.append({
                'id': top_id,
                'doi': doi,
                'name': name,
                'matched_fields': ', '.join(matched),
            })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=['id', 'doi'])

    return df

# %%
er_soil = find_soil_observations(er_meta)
er_soil_ids = list(er_soil['id'].unique())

# %%
er_soil_meta = [j for j in er_meta if j.get('id') in er_soil_ids]

# %%
# Save soil dataset catalog and metadata
er_soil.to_csv('../data/processed/ess-dive_eastriver_soildatasets.tsv', sep='\t', index=False)

with open('../data/processed/er_soil_meta.json', 'w') as f:
    json.dump(er_soil_meta, f, indent=2)


# %%[markdown]
## Download data files from ESS-DIVE

# %%
# Filter to datasets marked for download (requires 'include' column in er_soil)
dl_data_dois = list(er_soil[er_soil['include'] == 'T']['doi'])
dl_data_meta = [m for m in er_soil_meta if m.get('dataset')['@id'] in dl_data_dois]

# %%
# Download all files for each selected dataset
for obj in dl_data_meta:
    dirname = obj.get('id')
    distro = obj.get('dataset').get('distribution')
    urls = [u['contentUrl'] for u in distro]
    fns = [u['name'] for u in distro]

    for url, fn in zip(urls, fns):
        file_path = '../data/external/soil_datasets/{}/{}'.format(dirname, fn)
        print(file_path)
        os.makedirs('../data/external/soil_datasets/{}'.format(dirname), exist_ok=True)

        with requests.get(url, headers={"Authorization": header_authorization}) as resp:
            resp.raise_for_status()
            with open(file_path, 'wb') as f:
                f.write(resp.content)
