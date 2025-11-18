from string import Template

template = Template(
    '''name = "$dms_id"
description = "Dataset for $dms_id from $first_author $year for $publication"
version = "1.0.0"

[[ assays ]]
sequence = "mutated_sequence"
path = "../../dms_substitutions_store/cv_folds_singles_substitutions/$dms_filename"
sequence_alphabet = "AA"

[[ assay_targets ]]
name = "$coarse_selection_type"
description = "$selection_assay measurement for $selection_type with $molecule_name"

[[ assay_variables ]]
name = "DMS binarization cutoff"
description = "Cutoff value for determinating the DMS bins"

[[ assay_variables ]]
name = "DMS binarization method"
description = "Method for generating the DMS bins"

[ assay.variables ]
"DMS binarization cutoff" = $dms_binarization_cutoff
"DMS binarization method" = $dms_binarization_method

[ assays.targets ]
"$coarse_selection_type" = "DMS_score"

[ assays.metadata ]
UniProt_ID = "$uniprot_id"
taxon = "$taxon"
organism = "$source_organism"
selection_assay = "$selection_assay"
selection_type = "$selection_type"

[[ sequences ]]
path = "../../fasta_store/$dms_id.fasta"
type = "wild_type"
alphabet = "AA"

[[ msas ]]
path = "../../dms_msa_alignment_store/DMS_msa_files/$msa_filename"
format = "fasta"
weights_path = "../../dms_msa_weights_store/DMS_msa_weights/$weight_file_name"

[ msas.metadata ]
bitscore = "$msa_bitscore"
theta = "$msa_theta"
sequence_start = "$msa_start"
sequence_end = "$msa_end"
length = "$msa_len"
num_seqs = "$msa_num_seqs"
N_eff = "$msa_n_eff"
N_eff_L = "$msa_n_eff_l"
N_eff_L_category = "$msa_n_eff_l_category"
num_significant = "$num_significant"
num_significant_L = "$num_significant_L"
perc_cov = "$msa_perc_cov"
num_cov = "$msa_num_cov"

[[ structures ]]
path = "../../dms_protein_structures_store/ProteinGym_AF2_structures/$pdb_file"

[ structures.metadata ]
pdb_range = "$pdb_range"
type = "computational"
'''
)