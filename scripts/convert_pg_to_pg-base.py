#!/usr/bin/env python3

"""
Authors: ProteinGym team
Version of original proteingym data: 1.3
Created for Python 3.12.10

All downloads obtained from: proteingym.org/downloads

This script downloads the original DMS and Clinical Variants from Proteingym.org
After downloading this converts them to a proteingym-base dataset which you can upload
to your storage repository off preference.

NOTE: We do not incorporate the raw data in this version of the script.
Raw could be added once we add measurements to the metrics and store raw as measurements.
Furthermore raw is not as standardized over the original PG data.

NOTE: Currently we store the reference sequence as the wild-type sequence.
Should change this to reference sequence (after that feature is done)

Double check this with original PG authors:
- We have a separation between two types, DMS Assays and ClinVars.
ClinVar only concerns zero-shot prediction, while DMS concerns both zero-shot and supervised

- ClinVars contains two types, Substitutions and Indels, 
both with associated:
    - MSA files
    - MSA weight files
    - reference files

- DMS Assays contain two types, Substitutions and Indels,
both with associated:
    - Supervised CV splits (Which also contains zero-shot data)
        - Singles
        - Multiples
        - Indels
    - MSA files
    - MSA weight files
    - PDB files
    - reference files


"""

import requests
from tqdm import tqdm
from pathlib import Path
import zipfile
from string import Template

import polars

from proteingym.base import Dataset, Manifest
from templates import clinvar_sub

#URLS to download
#
# dms = {
#     "substitutions" : 
#     "indels" : 
#     "msa alignment" : 
#     "msa weights" :
#     "protein structures" :
#     "reference_substitutions"
# }

clin_vars = {
    "substitutions" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_ProteinGym_substitutions.zip",
    "indels" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_ProteinGym_indels.zip",
    "msa alignment" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_msa_files.zip",
    "msa weights" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_msa_weights.zip",
    "reference_substitutions" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_substitutions.csv",
    "reference_indels" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_indels.csv",
}

def download_loop(mapping: dict) -> None:
    """Performs the download loop based on the dictionary of names and URLs

    Args:
        mapping (dict): dictionary containing the names as keys, and the download URLs as values.
    """

    for key, url in mapping.items():
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))

        # Determine file extension from URL
        file_ext = '.csv' if url.endswith('.csv') else '.zip'
        file_path = Path(f"{key}{file_ext}").resolve()
        
        print('-' * 50)
        print(f'starting file download for {key}:')

        if file_path.exists():
            print(f'{key}{file_ext} already exists at location {file_path}')
            print(f'Skipping download for {key}{file_ext}')
            continue

        with open(f"{key}{file_ext}", "wb") as f, tqdm(
            total=total_size, 
            unit='iB', 
            unit_scale=True
        ) as bar:
            for data in response.iter_content(chunk_size=4096):
                f.write(data)
                bar.update(len(data))

    print('-' * 50)
    print('file download complete')
    print(f'downloaded {len(mapping.items())} items')
    return

def extract_all(mapping: dict) -> None:
    """Extracts ZIP files and copies CSV files to appropriate directories

    Args:
        mapping (dict): dictionary containing the names as keys, and the download URLs as values.
    """
    import shutil
    
    for key, url in mapping.items():
        if url.endswith('.csv'):
            pass
        else:
            zip_file = Path(f"{key}.zip")
            if zip_file.exists():
                with zipfile.ZipFile(zip_file, "r") as zip_ref:
                    zip_ref.extractall(f"{key}_store")
    return

# download_loop(clin_vars)
# extract_all(clin_vars)

def create_datasets(reference_csv: str) -> Dataset:
    df = polars.read_csv(reference_csv)
    datasets_to_create = df['DMS_id'].to_list()

    for dataset in datasets_to_create:
        manifest_fp = create_manifest(dataset, df)
        validate_manifest(manifest_fp)

def write_sequence_to_fasta(sequence: str, sequence_id: str, path: Path) -> None:
    with open(path, 'w') as file:
        file.write(f'>{sequence_id}\n')
        file.write(f'{sequence}\n')

def create_manifest(DMS_id: str, references: polars.DataFrame):

    row = references.filter(polars.col('DMS_id') == DMS_id).select([
        'target_seq', 'file_length', 'DMS_filename', 'EVE_model_path', 
        'MSA_filename', 'alignment_source', 'weight_file_name', 
        'MSA_start', 'MSA_end', 'MSA_len'
    ]).row(0)
    
    ### For ClinVar substitutions

    target_seq, file_length, DMS_filename, EVE_model_path, MSA_filename, alignment_source, weight_file_name, MSA_start, MSA_end, MSA_len = row

    write_sequence_to_fasta(target_seq, DMS_id, Path(f"./fasta_store/{DMS_id}.fasta"))

    manifest_template = clinvar_sub.clinvar_substitutions

    manifest_content = manifest_template.substitute(
        dms_id = DMS_id,
        store = "substitutions_store",
        dms_filename = DMS_filename,
        msa_filename = MSA_filename,
        msa_start = MSA_start,
        msa_end = MSA_end,
        msa_length = MSA_len,
        msa_weight_path = weight_file_name,
        eve_model_path = EVE_model_path,
        alignment_source = alignment_source,
    )
    with open(f"{DMS_id}.toml", "w") as toml_file:
        toml_file.write(manifest_content)
        return toml_file.name

def validate_manifest(manifest: Manifest):
    """Validate the manifest by loading it"""

    try:
        manifest = Manifest.from_path(manifest)
        dataset = Dataset.from_manifest(dataset)
        dataset.dump()
    except Exception as e:
        print(e)

# manifest_fp = create_manifest('NP_000007.1', polars.read_csv('reference_substitutions.csv'))
# validate_manifest(manifest_fp)
reference_file = polars.read_csv('reference_substitutions.csv')
create_datasets('reference_substitutions.csv')