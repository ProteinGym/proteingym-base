#!/usr/bin/env python3

"""
Authors: ProteinGym team
Version of original proteingym data: 1.3
Created for Python 3.12.10

All downloads obtained from: proteingym.org/downloads

This script downloads the original DMS and Clinical Variants from Proteingym.org
After downloading this converts them to a proteingym-base dataset which you can upload
to your storage repository off preference.

---------------- TODO LOG ----------------

NOTE: We do not incorporate the raw data in this version of the script.
Raw could be added once we add measurements to the metrics and store raw as measurements.
Furthermore raw is not as standardized over the original PG data.

NOTE: Currently we store the reference sequence as the wild-type sequence.
Should change this to reference sequence (after that feature is done)

NOTE: ClinVar Indels are not set to datasets here as we require measurements

NOTE: We only store the regular MSA weights, not the MSA Transformer weights
See issue #362

NOTE: I still think e.g. taxon, organism, amount of mutations etc 
should be metadata properties of the dataset, not of the assay

---------------- TODO LOG ----------------

"""
import requests
from tqdm import tqdm
from pathlib import Path
import zipfile
import logging
import os
import polars as pl
import shutil

from proteingym.base import Dataset, Manifest
from templates import clinvar_subs, clinvar_indels, dms_subs, gene_to_uniprot

log_filename = f"proteingym_conversion.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

dms = {
    "dms_substitutions" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/cv_folds_singles_substitutions.zip",
    "dms_substitutions_multiples" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/cv_folds_multiples_substitutions.zip",
    "dms_indels" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/cv_folds_indels.zip",
    "dms_msa_alignment" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/DMS_msa_files.zip",
    "dms_msa_weights" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/DMS_msa_weights.zip",
    "dms_protein_structures" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/ProteinGym_AF2_structures.zip",
    "dms_subs" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/DMS_substitutions.csv",
    "dms_indels" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/DMS_indels.csv",
}

clin_vars = {
    "clinvar_substitutions" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_ProteinGym_substitutions.zip",
    "clinvar_indels" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_ProteinGym_indels.zip",
    "clinvar_msa_alignment" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_msa_files.zip",
    "clinvar_msa_weights" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_msa_weights.zip",
    "clinvar_subs" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_substitutions.csv",
    "clinvar_indels" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_indels.csv",
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
        
        log.info(f'starting file download for {key}:')

        if file_path.exists():
            log.warning(f'{key}{file_ext} already exists at location {file_path}')
            log.warning(f'Skipping download for {key}{file_ext}')
            continue

        with open(f"{key}{file_ext}", "wb") as f, tqdm(
            total=total_size, 
            unit='iB', 
            unit_scale=True
        ) as bar:
            for data in response.iter_content(chunk_size=4096):
                f.write(data)
                bar.update(len(data))

    log.info('file download complete')
    return

def extract_all(mapping: dict) -> None:
    """Extracts ZIP files and copies CSV files to appropriate directories

    Args:
        mapping (dict): dictionary containing the names as keys, and the download URLs as values.
    """    
    for key, url in mapping.items():
        if url.endswith('.csv'):
            pass
        else:
            zip_file = Path(f"{key}.zip")
            if zip_file.exists():
                with zipfile.ZipFile(zip_file, "r") as zip_ref:
                    zip_ref.extractall(f"{key}_store")
                    log.info(f"Extracted {key}.zip to {key}_store/")
    return

def write_sequence_to_fasta(sequence: str, sequence_id: str, path: Path) -> None:
    with open(path, 'w') as file:
        file.write(f'>{sequence_id}\n')
        file.write(f'{sequence}\n')

def create_manifest(DMS_id: str, references: pl.DataFrame, regime: str) -> str:
    """Creates a manifest based on DMS id, reference frame containing paths
    and regime for which dataset we are covering. We use the regime to select
    between specifics for each regime.

    Args:
        DMS_id (str): DMS_id of the dataset
        references (polars.DataFrame): DataFrame containing all reference information
        regime (str): 'clinvar_subs', 'clinvar_indels', 'dms_subs', 'dms_indels' 

    Returns:
        filename (str): file name of the created manifest
    """

    # Each reference file has information slightly different encoded
    # But we run it only once so why not be lazy with if/elif 
    # DRY: DO repeat yourself :)

    if regime == 'clinvar_subs':
        row_dict = references.filter(pl.col('DMS_id') == DMS_id).to_dicts()[0]

        write_sequence_to_fasta(row_dict['target_seq'], DMS_id, Path(f"./fasta_store/{DMS_id}.fasta"))

        manifest_template = clinvar_subs.template

        manifest_content = manifest_template.substitute(
            dms_id=DMS_id,
            store="substitutions_store",
            dms_filename=row_dict['DMS_filename'],
            msa_filename=row_dict['MSA_filename'],
            msa_start=row_dict['MSA_start'],
            msa_end=row_dict['MSA_end'],
            msa_length=row_dict['MSA_len'],
            msa_weight_path=row_dict['weight_file_name'],
            eve_model_path=row_dict['EVE_model_path'],
            alignment_source=row_dict['alignment_source'],
        )
    elif regime == 'dms_subs':
        row_dict = references.filter(pl.col('DMS_id') == DMS_id).to_dicts()[0]
        
        write_sequence_to_fasta(row_dict['target_seq'], DMS_id, Path(f"./fasta_store/{DMS_id}.fasta"))

        manifest_template = dms_subs.template

        # need to convert the uniprot ID/AC to uniprotKB for lookup
        # created an conversion table in templates/gene_to_uniprot

        gene_mapping = gene_to_uniprot.gene_mapping

        if row_dict['UniProt_ID'] in gene_mapping:
            uniprot_id = gene_mapping[row_dict['UniProt_ID']]

        manifest_content = manifest_template.substitute(
            dms_id=DMS_id,
            dms_filename=row_dict['DMS_filename'],
            first_author=row_dict['first_author'],
            year=row_dict['year'],
            publication=row_dict['title'],
            doi=row_dict['jo'],
            coarse_selection_type=row_dict['coarse_selection_type'],
            selection_assay=row_dict['selection_assay'],
            selection_type=row_dict['selection_type'],
            molecule_name=row_dict['molecule_name'],
            uniprot_id=uniprot_id,
            taxon=row_dict['taxon'],
            source_organism=row_dict['source_organism'],
            total_mutations=row_dict['DMS_total_number_mutants'],
            single_mutants=row_dict['DMS_number_single_mutants'],
            multiple_mutants=row_dict['DMS_number_multiple_mutants'],
            dms_binarization_cutoff=row_dict['DMS_binarization_cutoff'],
            dms_binarization_method=row_dict['DMS_binarization_method'],
            raw_dms_phenotype=row_dict['raw_DMS_phenotype_name'],
            raw_dms_directionality=row_dict['raw_DMS_directionality'],
            msa_filename=row_dict['MSA_filename'],
            weight_file_name=row_dict['weight_file_name'],
            msa_bitscore=row_dict['MSA_bitscore'],
            msa_theta=row_dict['MSA_theta'],
            msa_start=row_dict['MSA_start'],
            msa_end=row_dict['MSA_end'],
            msa_len=row_dict['MSA_len'],
            msa_num_seqs=row_dict['MSA_num_seqs'],
            msa_n_eff=row_dict['MSA_N_eff'],
            msa_n_eff_l=row_dict['MSA_Neff_L'],
            msa_n_eff_l_category=row_dict['MSA_Neff_L_category'],
            num_significant=row_dict['MSA_num_significant'],
            num_significant_L=row_dict['MSA_num_significant_L'],
            msa_perc_cov=row_dict['MSA_perc_cov'],
            msa_num_cov=row_dict['MSA_num_cov'],
            pdb_file=row_dict['pdb_file'],
            pdb_range=row_dict['pdb_range']
        )
    elif regime == 'clinvar_indels':
        ### Clinvar Indels contain so much more information to track
        ### Should discuss with Marks Lab
        ### Think most of this can be stored as measurements. 
        pass
    elif regime == 'dms_indels':
        pass
    else:
        log.error("Selected a regime that is not present in ProteinGym")

    with open(f"./output/manifests/{DMS_id}.toml", "w") as toml_file:
        toml_file.write(manifest_content)
        return toml_file.name

def validate_manifest(manifest: Manifest) -> Dataset:
    """Validate the manifest by loading it into a dataset"""

    try:
        manifest = Manifest.from_path(manifest)
        dataset = Dataset.from_manifest(manifest)
    except Exception as e:
        log.error(e)
    return dataset

def dump_dataset(dataset):
    """dump the dataset to pgdata sets"""
    try:
        filepath = dataset.dump()
    except Exception as e:
        log.error(e)
    return filepath

if __name__ == "__main__":
    # make some directories for storing
    # mb tmp dirs?
    os.makedirs('fasta_store', exist_ok=True)
    os.makedirs('output/manifests', exist_ok=True)
    os.makedirs('output/datasets', exist_ok=True)

    # for mapping in [dms, clin_vars]:
    #     download_loop(mapping)
    #     extract_all(mapping)

    n_datasets = 0
    for regime in ['dms_subs']: #, 'clinvar_indels', 'clinvar_subs']:
        reference = pl.read_csv(f"{regime}.csv")

        datasets_to_create = reference['DMS_id'].to_list()
        for dataset in datasets_to_create:
            manifest = create_manifest(dataset, reference, regime)
            dataset = validate_manifest(manifest)
            dataset_filepath = dump_dataset(dataset)
            shutil.move(dataset_filepath, Path(Path(dataset_filepath).parents[0] / 'output' / 'datasets' ))
            n_datasets += 1
            if n_datasets % 50 == 0:
                log.info(f"Parsed {n_datasets} datasets")
        
    log.info(f"Parsed {n_datasets} datasets in total")