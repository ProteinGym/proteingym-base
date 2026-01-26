"""
Authors: ProteinGym team
Version of original proteingym data: 1.3
Created for Python 3.12.10

All downloads obtained from: proteingym.org/downloads

This script downloads the original DMS and Clinical Variants from Proteingym.org
After downloading this converts them to a proteingym-base dataset which you can upload
to your storage repository off preference.

---------------- READ THIS BEFORE EXECUTING THE SCRIPT ----------------

################ DMS SUBS #############################################

DMS subs needed slight cleaning before you can fully process it. Currently
we have hardcoded these changes, but this will break upon changes in the
download format.

- The UniProt_ID stored are not the UniProt accession numbers. We've 
used uniprot.org/id-mapping to retrieve the accession numbers with some
manual cleaning. See `conversion_tables.py` for the mapping result.

- ANCSZ_Hobbs_2022 does not have an associated UniProt.

- CAR11_HUMAN_Meitlis_2020_gof and CAR11_HUMAN_Meitlis_2020_lof have a 
dot after their doi that breaks the parsing. The doi is
`10.1016/j.ajhg.2020.10.015.` but should be `10.1016/j.ajhg.2020.10.015`

- RASK_HUMAN_Weng_2022_abundance and RASK_HUMAN_Weng_2022_binding-DARPin_K55
point to 10.1101/2022.12.06.519122 and 10.1101/2022.12.06.519127 respectively.
They should both point to `.519122`. Even better is to point them to
`10.1038/s41586-023-06954-0` as this is the published version of the previous
pre-print DOI.

- F7YBW8_MESOW_Aakre_2015 contains only 4 splits for the Kfold splits. The same
goes for SPG1_STRSG_Wu_2016

NOTE: We only store the regular MSA weights, not the MSA Transformer weights
See issue #362

---------------- TODO LOG ----------------

"""
import requests
from tqdm import tqdm
from pathlib import Path
import zipfile
import logging
import polars as pl
import shutil
import tempfile
import argparse

from proteingym.base import Dataset, Manifest, Subsets
from proteingym.base.splits import PredefinedSplitter

from templates import (
    dms_sub_template,
    dms_sub_multiples_template,
    dms_indel_template, 
    clinvar_sub_template, 
    clinvar_indel_template
)
from conversion_tables import (
    conversion_dms_subs, 
    conversion_dms_indels,
)

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

################################
# Downloads are based on v1.3
# Using different versions might require significant overhaul to the scripts
################################

dms = {
    "dms_substitutions" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/cv_folds_singles_substitutions.zip",
    "dms_substitutions_multiples" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/cv_folds_multiples_substitutions.zip",
    "dms_indels" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/cv_folds_indels.zip",
    "dms_msa_alignment" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/DMS_msa_files.zip",
    "dms_msa_weights" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/DMS_msa_weights.zip",
    "dms_protein_structures" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/ProteinGym_AF2_structures.zip",
    "dms_subs_csv" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/DMS_substitutions.csv",
    "dms_indels_csv" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/DMS_indels.csv",
}

clinvar = {
    "clinvar_substitutions" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_ProteinGym_substitutions.zip",
    "clinvar_indels" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_ProteinGym_indels.zip",
    "clinvar_msa_alignment" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_msa_files.zip",
    "clinvar_msa_weights" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_msa_weights.zip",
    "clinvar_subs_csv" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_substitutions.csv",
    "clinvar_indels_csv" : "https://marks.hms.harvard.edu/proteingym/ProteinGym_v1.3/clinical_indels.csv",
}

def download_loop(mapping: dict) -> None:
    """Downloads the ProteinGym data using a URL dictionary.

    Args:
        mapping (dict): dictionary containing the names as keys, and the download URLs as values.
    """

    for key, url in mapping.items():
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))

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
    """Helper function to write a sequence to a fasta file
    
    Args:
        sequence (str): amino acid / dna / rna sequence of the object
        sequence_id (str): the identifier of the sequence
        path (str): location to save the fasta file to.
    """
    with open(path, 'w') as file:
        file.write(f'>{sequence_id}\n')
        file.write(f'{sequence}\n')

def create_dms_manifest(DMS_id: str, references: pl.DataFrame, variant_type: str, temp_dir: Path) -> str:
    """Creates a ProteinGym manifest for DMS datasets.

    Args:
        DMS_id (str): DMS_id of the dataset
        references (pl.DataFrame): DataFrame containing all reference information
        variant_type (str): 'subs' or 'indels'
        temp_dir (Path): Temporary directory path

    Returns:
        str: filename of the created manifest
    """
    row_dict = references.filter(pl.col('DMS_id') == DMS_id).to_dicts()[0]
    fasta_dir = Path("fasta_store")
    write_sequence_to_fasta(row_dict['target_seq'], DMS_id, fasta_dir / f"{DMS_id}.fasta")
    
    if variant_type == 'subs':
        gene_mapping = conversion_dms_subs
    elif variant_type == 'indels':
        gene_mapping = conversion_dms_indels

    uniprot_id = gene_mapping.get(row_dict['UniProt_ID'], row_dict['UniProt_ID'])
    
    common_params = {
        'dms_id': DMS_id,
        'dms_filename': row_dict['DMS_filename'],
        'first_author': row_dict['first_author'],
        'year': row_dict['year'],
        'publication': row_dict['title'],
        'doi': row_dict['jo'],
        'coarse_selection_type': row_dict['coarse_selection_type'],
        'selection_assay': row_dict['selection_assay'],
        'selection_type': row_dict['selection_type'],
        'molecule_name': row_dict['molecule_name'],
        'uniprot_id': uniprot_id,
        'taxon': row_dict['taxon'],
        'source_organism': row_dict['source_organism'],
        'total_mutations': row_dict['DMS_total_number_mutants'],
        'dms_binarization_cutoff': row_dict['DMS_binarization_cutoff'],
        'dms_binarization_method': row_dict['DMS_binarization_method'],
        'raw_dms_phenotype': row_dict['raw_DMS_phenotype_name'],
        'raw_dms_directionality': row_dict['raw_DMS_directionality'],
        'msa_filename': row_dict['MSA_filename'],
        'weight_file_name': row_dict['weight_file_name'],
        'msa_bitscore': row_dict['MSA_bitscore'],
        'msa_theta': row_dict['MSA_theta'],
        'msa_start': row_dict['MSA_start'],
        'msa_end': row_dict['MSA_end'],
        'msa_len': row_dict['MSA_len'],
        'msa_num_seqs': row_dict['MSA_num_seqs'],
        'msa_n_eff': row_dict['MSA_N_eff'],
        'msa_n_eff_l': row_dict['MSA_Neff_L'],
        'msa_n_eff_l_category': row_dict['MSA_Neff_L_category'],
        'num_significant': row_dict['MSA_num_significant'],
        'num_significant_L': row_dict['MSA_num_significant_L'],
        'msa_perc_cov': row_dict['MSA_perc_cov'],
        'msa_num_cov': row_dict['MSA_num_cov'],
    }
    
    if variant_type == 'subs':
        manifest_template = dms_sub_template
        common_params.update({
            'pdb_file': row_dict['pdb_file'],
            'pdb_range': row_dict['pdb_range']
        })
    elif variant_type == 'indels':
        manifest_template = dms_indel_template
    
    manifest_content = manifest_template.substitute(**common_params)
    
    manifest_dir = temp_dir / "manifests"
    manifest_dir.mkdir(exist_ok=True)
    manifest_path = manifest_dir / f"{DMS_id}.toml"
    with open(manifest_path, "w") as toml_file:
        toml_file.write(manifest_content)
        return str(manifest_path)

def create_clinvar_manifest(DMS_id: str, references: pl.DataFrame, variant_type: str, temp_dir: Path) -> str:
    """Creates a ProteinGym manifest for ClinVar datasets.

    Args:
        DMS_id (str): DMS_id of the dataset
        references (pl.DataFrame): DataFrame containing all reference information
        variant_type (str): 'subs' or 'indels'
        temp_dir (Path): Temporary directory path

    Returns:
        str: filename of the created manifest
    """
    row_dict = references.filter(pl.col('DMS_id') == DMS_id).to_dicts()[0]
    fasta_dir = Path("fasta_store")
    write_sequence_to_fasta(row_dict['target_seq'], DMS_id, fasta_dir / f"{DMS_id}.fasta")
    
    common_params = {
        'dms_id': DMS_id,
        'dms_filename': row_dict['DMS_filename'],
        'msa_filename': row_dict['MSA_filename'],
        'msa_start': row_dict['MSA_start'],
        'msa_end': row_dict['MSA_end'],
        'eve_model_path': row_dict['EVE_model_path'],
        'alignment_source': row_dict['alignment_source'],
    }
    
    if variant_type == 'subs':
        manifest_template = clinvar_subs.template
        common_params.update({
            'store': "clinvar_substitutions_store",
            'msa_weight_path': row_dict['weight_file_name'],
            'msa_length': row_dict['MSA_len'],
        })
    elif variant_type == 'indels':
        manifest_template = clinvar_indels.template
        common_params.update({
            'store': "clinvar_indels_store",
            'msa_weight_path': row_dict['weight_file_name'],
            'msa_length': row_dict.get('MSA_len', ''),
        })
    else:
        log.error(f"Unknown ClinVar variant type: {variant_type}")
        return ""
    
    manifest_content = manifest_template.substitute(**common_params)
    
    manifest_dir = temp_dir / "manifests"
    manifest_dir.mkdir(exist_ok=True)
    manifest_path = manifest_dir / f"{DMS_id}.toml"
    with open(manifest_path, "w") as toml_file:
        toml_file.write(manifest_content)
        return str(manifest_path)

def create_multiples_manifest(DMS_id: str, references: pl.DataFrame, temp_dir: Path) -> str:
    """Creates a ProteinGym manifest for DMS multiples datasets."""
    row_dict = references.filter(pl.col('DMS_id') == DMS_id).to_dicts()[0]
    
    gene_mapping = conversion_dms_subs
    uniprot_id = gene_mapping.get(row_dict['UniProt_ID'], row_dict['UniProt_ID'])
    
    common_params = {
        'dms_id': DMS_id,
        'dms_filename': row_dict['DMS_filename'],
        'first_author': row_dict['first_author'],
        'year': row_dict['year'],
        'publication': row_dict['title'],
        'doi': row_dict['jo'],
        'coarse_selection_type': row_dict['coarse_selection_type'],
        'selection_assay': row_dict['selection_assay'],
        'selection_type': row_dict['selection_type'],
        'molecule_name': row_dict['molecule_name'],
        'uniprot_id': uniprot_id,
        'taxon': row_dict['taxon'],
        'source_organism': row_dict['source_organism'],
        'total_mutations': row_dict['DMS_total_number_mutants'],
        'dms_binarization_cutoff': row_dict['DMS_binarization_cutoff'],
        'dms_binarization_method': row_dict['DMS_binarization_method'],
        'raw_dms_phenotype': row_dict['raw_DMS_phenotype_name'],
        'raw_dms_directionality': row_dict['raw_DMS_directionality'],
        'msa_filename': row_dict['MSA_filename'],
        'weight_file_name': row_dict['weight_file_name'],
        'msa_bitscore': row_dict['MSA_bitscore'],
        'msa_theta': row_dict['MSA_theta'],
        'msa_start': row_dict['MSA_start'],
        'msa_end': row_dict['MSA_end'],
        'msa_len': row_dict['MSA_len'],
        'msa_num_seqs': row_dict['MSA_num_seqs'],
        'msa_n_eff': row_dict['MSA_N_eff'],
        'msa_n_eff_l': row_dict['MSA_Neff_L'],
        'msa_n_eff_l_category': row_dict['MSA_Neff_L_category'],
        'num_significant': row_dict['MSA_num_significant'],
        'num_significant_L': row_dict['MSA_num_significant_L'],
        'msa_perc_cov': row_dict['MSA_perc_cov'],
        'msa_num_cov': row_dict['MSA_num_cov'],
        'pdb_file': row_dict['pdb_file'],
        'pdb_range': row_dict['pdb_range']
    }
    
    manifest_content = dms_sub_multiples_template.substitute(**common_params)
    
    manifest_dir = temp_dir / "manifests"
    manifest_dir.mkdir(exist_ok=True)
    manifest_path = manifest_dir / f"{DMS_id}_multiples.toml"
    with open(manifest_path, "w") as toml_file:
        toml_file.write(manifest_content)
        return str(manifest_path)

def create_manifest(DMS_id: str, references: pl.DataFrame, dataset_type: str, variant_type: str, temp_dir: Path) -> str:
    """Creates a manifest based on dataset and variant type.

    Args:
        DMS_id (str): DMS_id of the dataset
        references (pl.DataFrame): DataFrame containing all reference information
        dataset_type (str): 'dms' or 'clinvar'
        variant_type (str): 'subs' or 'indels'
        temp_dir (Path): Temporary directory path

    Returns:
        str: filename of the created manifest
    """
    if dataset_type == 'dms':
        return create_dms_manifest(DMS_id, references, variant_type, temp_dir)
    elif dataset_type == 'clinvar':
        return create_clinvar_manifest(DMS_id, references, variant_type, temp_dir)
    else:
        log.error(f"Unknown dataset type: {dataset_type}")
        return ""

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
    parser = argparse.ArgumentParser(description='Convert ProteinGym data to proteingym-base format')
    parser.add_argument('--dataset-type', choices=['dms', 'clinvar'], help='Dataset type to process')
    parser.add_argument('--variant-type', choices=['subs', 'indels'], help='Variant type to process')
    parser.add_argument('--all', action='store_true', help='Process all dataset and variant types')
    args = parser.parse_args()
    
    datasets_output_dir = Path("output/datasets")
    manifests_output_dir = Path("output/manifests")
    splits_output_dir = Path("output/splits")

    fasta_store_dir = Path("fasta_store")
    datasets_output_dir.mkdir(parents=True, exist_ok=True)
    manifests_output_dir.mkdir(parents=True, exist_ok=True)
    splits_output_dir.mkdir(parents=True, exist_ok=True)
    fasta_store_dir.mkdir(exist_ok=True)

    if not args.all and (not args.dataset_type or not args.variant_type):
        parser.error("Either --all or both --dataset-type and --variant-type must be specified")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # for mapping in [dms, clinvar]:
        #     download_loop(mapping)
        #     extract_all(mapping)
        
        if args.all:
            combinations = [('dms', 'subs'), ('dms', 'indels'), ('clinvar', 'subs'), ('clinvar', 'indels')]
        else:
            combinations = [(args.dataset_type, args.variant_type)]
        
        n_datasets = 0
        for dataset_type, variant_type in combinations:
            csv_name = f"{dataset_type}_{variant_type}_csv.csv"
            if not Path(csv_name).exists():
                log.warning(f"Skipping {csv_name} - file not found")
                continue
                
            reference = pl.read_csv(csv_name)

            # Fix for DOI errors:
            if csv_name == "dms_subs_csv.csv":
                # . after doi
                reference = reference.with_columns(pl.col("jo").str.replace("10.1016/j.ajhg.2020.10.015.", "10.1016/j.ajhg.2020.10.015"))
                
                # wrong papers
                reference = reference.with_columns(pl.col("jo").str.replace("10.1101/2022.12.06.519122", "10.1038/s41586-023-06954-0"))
                reference = reference.with_columns(pl.col("jo").str.replace("10.1101/2022.12.06.519127", "10.1038/s41586-023-06954-0"))

            datasets_to_create = reference['DMS_id'].to_list()
            
            for dataset_id in datasets_to_create:
                if (datasets_output_dir / (dataset_id + '.pgdata')).exists():
                    continue
                
                manifest_path = create_manifest(dataset_id, reference, dataset_type, variant_type, temp_path)
                
                # Handle multiples if they exist
                # This creates a separate .pgdata for the multiples assay.
                multiple_mutations = reference.filter(pl.col('DMS_id') == dataset_id)['DMS_number_multiple_mutants']
                if dataset_type == 'dms' and variant_type == 'subs' and multiple_mutations[0] > 0:
                    multiples_manifest_path = create_multiples_manifest(dataset_id, reference, temp_path)
                    if multiples_manifest_path:
                        final_multiples_path = manifests_output_dir / f"{dataset_id}_multiples.toml"
                        shutil.move(multiples_manifest_path, final_multiples_path)
                        
                        multiples_dataset = validate_manifest(final_multiples_path)
                        multiples_dataset_filepath = dump_dataset(multiples_dataset)

                        subsets = Subsets(dataset=multiples_dataset)
                        random = PredefinedSplitter(split_column="fold_rand_multiples", split_order=range(5))
                        subsets.update(random=random.split(dataset=multiples_dataset))

                        multiples_splits_filepath = subsets.dump()

                        shutil.move(multiples_dataset_filepath, datasets_output_dir)
                        shutil.move(multiples_splits_filepath, splits_output_dir)

                if manifest_path:
                    final_manifest_path = manifests_output_dir / f"{dataset_id}.toml"
                    shutil.move(manifest_path, final_manifest_path)

                    #Fix for no UniProt in ANCSZ_Hobbs:
                    if dataset_id == 'ANCSZ_Hobbs_2022':
                        with open(final_manifest_path, 'r') as file:
                            content = file.read()
                        content = content.replace('uniprot_id = "None"', '')
                        with open(final_manifest_path, 'w') as file:
                            file.write(content)
                    

                    dataset = validate_manifest(final_manifest_path)
                    dataset_filepath = dump_dataset(dataset)

                    subsets = Subsets(dataset=dataset)

                    if dataset_type == "dms":
                        
                        if variant_type == "subs":
                            split_order = range(5)
                            # These only got an kfold=4 split.
                            if dataset_id in [
                                'F7YBW8_MESOW_Aakre_2015',
                                'SPG1_STRSG_Wu_2016',
                            ]:
                                split_order = range(4)

                            modulo = PredefinedSplitter(split_column="fold_modulo_5", split_order=split_order)
                            contiguous = PredefinedSplitter(split_column="fold_contiguous_5", split_order=split_order)
                            random = PredefinedSplitter(split_column="fold_random_5", split_order=split_order)
                            
                            subsets.update(modulo=modulo.split(dataset=dataset))
                            subsets.update(contiguous=contiguous.split(dataset=dataset))
                            subsets.update(random=random.split(dataset=dataset))
                        
                        if variant_type == "indels":
                            random = PredefinedSplitter(split_column="fold_random_5")

                    splits_filepath = subsets.dump()

                    shutil.move(dataset_filepath, datasets_output_dir)
                    shutil.move(splits_filepath, splits_output_dir)

                    n_datasets += 1
                    if n_datasets % 50 == 0:
                        log.info(f"Parsed {n_datasets} datasets")
        
        log.info(f"Parsed {n_datasets} datasets in total")