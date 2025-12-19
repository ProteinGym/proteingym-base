import dataclasses

import pytest
import requests

from proteingym.base.publication import Publication


@pytest.fixture
def af2_doi() -> str:
    return "10.1038/s41586-021-03819-2"


def test_publication_doi_retrieves_correct_metadata(af2_doi) -> None:
    """Test that DOI lookup returns expected publication metadata."""
    pub = Publication(doi=af2_doi)
    assert dataclasses.asdict(pub) == {
        "title": "Highly accurate protein structure prediction with AlphaFold",
        "author": "Jumper, John and Evans, Richard and Pritzel, Alexander and "
        "Green, Tim and Figurnov, Michael and Ronneberger, Olaf and "
        "Tunyasuvunakool, Kathryn and Bates, Russ and Žídek, Augustin "
        "and Potapenko, Anna and Bridgland, Alex and Meyer, Clemens "
        "and Kohl, Simon A. A. and Ballard, Andrew J. and Cowie, "
        "Andrew and Romera-Paredes, Bernardino and Nikolov, Stanislav"
        " and Jain, Rishub and Adler, Jonas and Back, Trevor and"
        " Petersen, Stig and Reiman, David and Clancy, Ellen and "
        "Zielinski, Michal and Steinegger, Martin and Pacholska, "
        "Michalina and Berghammer, Tamas and Bodenstein, Sebastian "
        "and Silver, David and Vinyals, Oriol and Senior,"
        " Andrew W. and Kavukcuoglu, Koray and Kohli, "
        "Pushmeet and Hassabis, Demis",
        "journal": "Nature",
        "volume": "596",
        "number": "7873",
        "year": "2021",
        "pages": "583–589",
        "doi": "10.1038/s41586-021-03819-2",
    }


def test_publication_default_not_overwritten(af2_doi) -> None:
    """Test that overwrite behavior works consistently across components."""
    pub = Publication(doi=af2_doi, title="Manual Title")
    assert pub.title == "Manual Title"


def test_api_error_behavior() -> None:
    """Test that system crashes appropriately on API errors."""
    pub = Publication(doi="10.1234/definitely-invalid-doi-12345")

    with pytest.raises(requests.exceptions.HTTPError):
        _ = pub.title
