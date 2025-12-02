import pytest
import requests
from Bio.Seq import Seq

from proteingym.base.dataset import Dataset
from proteingym.base.publication import Publication
from proteingym.base.sequence import Sequence, SequenceAlphabet, SequenceType


def test_publication_doi_retrieves_correct_metadata() -> None:
    """Test that DOI lookup returns expected publication metadata."""
    pub = Publication(doi="10.1038/s41586-021-03819-2")  # AF2 paper
    filled = pub.fill_from_database()

    assert filled.journal == "Nature"
    assert filled.year == "2021"
    assert "AlphaFold" in filled.title

def test_uniprot_retrieves_correct_organism_data() -> None:
    """Test that UniProt lookup returns expected organism metadata."""
    # human insulin, well-known protein
    seq = Sequence(
        name="insulin",
        value=Seq(
            "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN"
        ),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
        uniprot_id="P01308",
    )
    filled = seq.fill_from_database()

    assert filled.organism == "Homo sapiens"
    assert filled.taxon_root == "Eukaryota"
    assert "insulin" in filled.molecule_name.lower()

def test_dataset_fills_all_components() -> None:
    """Test that dataset fill_from_database works on all components."""
    pub = Publication(doi="10.1038/s41586-021-03819-2")
    seq = Sequence(
        name="insulin",
        value=Seq(
            "MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVELGGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN"
        ),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
        uniprot_id="P01308",
    )

    dataset = Dataset(name="test_dataset", publication=pub, sequences=[seq])

    filled_dataset = dataset.fill_from_database()

    assert filled_dataset.publication.title is not None
    assert filled_dataset.publication.journal == "Nature"
    assert filled_dataset.sequences[0].organism is not None
    assert filled_dataset.sequences[0].taxon_root is not None

def test_overwrite_behavior_consistency() -> None:
    """Test that overwrite behavior works consistently across components."""
    pub = Publication(
        doi="10.1038/s41586-021-03819-2",
        title="Wrong Title",
        journal="Wrong Journal",
    )

    filled_no_overwrite = pub.fill_from_database(overwrite=False)
    assert filled_no_overwrite.title == "Wrong Title"
    assert filled_no_overwrite.journal == "Wrong Journal"

    filled_overwrite = pub.fill_from_database(overwrite=True)
    assert filled_overwrite.title != "Wrong Title"
    assert filled_overwrite.journal == "Nature"

def test_api_error_behavior() -> None:
    """Test that system crashes appropriately on API errors."""
    pub = Publication(doi="10.1234/definitely-invalid-doi-12345")

    with pytest.raises(requests.exceptions.HTTPError):
        pub.fill_from_database()

    seq = Sequence(
        name="test",
        value=Seq("ACDE"),
        type=SequenceType.WILD_TYPE,
        alphabet=SequenceAlphabet.AA,
        uniprot_id="DEFINITELY_INVALID_ID_12345",
    )

    with pytest.raises(requests.exceptions.HTTPError):
        seq.fill_from_database()
