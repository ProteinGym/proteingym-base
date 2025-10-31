from string import Template

## Template for ClinVar substitutions
template = Template(
    '''name = "$dms_id"
description = "Dataset for $dms_id"
version = "1.0.0"

[[ assays ]]
sequence = "mutated_sequence"
path = "$store/$dms_filename"
sequence_alphabet = "AA"

[[ assay_targets ]]
name = "DMS Score"
description = "Classification of ClinVar into Pathogenic or Benign"

[ assays.targets ]
"DMS Score" = "DMS_bin_score"

[[ sequences ]]
path = "fasta_store/$dms_id.fasta"
type = "wild_type"
alphabet = "AA"

[[ msas ]]
path = "msa alignment_store/subs/$msa_filename"
format = "fasta"
sequence_start = "$msa_start"
sequence_end = "$msa_end"
weights_path = "$msa_weight_path"

[ msas.metadata ]
EVE_model_path = "$eve_model_path"
Alignment_source = "$alignment_source"
MSA_length = "$msa_length"
'''
)