from importlib.util import find_spec
from pathlib import Path

import pytest

from pg2_dataset.backends.msa import (
    MSA,
    AbstractMSAManager,
    BiopythonMSAManager,
    BiotiteMSAManager,
)
from pg2_dataset.primitives.managers import BackendSearchOrder
from pg2_dataset.primitives.meta import MSAMeta

TEST_DATA_DIR = str(Path(__file__).parent.parent / "test_data" / "msa")
backends = []
if find_spec("Bio"):
    backends.append("Bio")
if find_spec("biotite"):
    backends.append("biotite")


@pytest.mark.skipif(
    not find_spec("Bio") and not find_spec("biotite"), reason="no MSA backend"
)
class TestMSA:
    @pytest.fixture
    def msa_file(self, tmp_path) -> list[Path]:
        fasta_file = tmp_path / "test_alignment.fasta"
        fasta_content = ">seq1\nACGTACGT\n>seq2\nACGTA-GT\n>seq3\nACGT--GT\n"
        with open(fasta_file, "w") as f:
            f.write(fasta_content)
        return fasta_file.as_posix()

    def _create_msa_meta(self, msa_file):
        return MSAMeta(file_path=msa_file, file_format="fasta")

    @pytest.mark.parametrize("backend", backends)
    def test_msa_class_initialization(self, msa_file, backend):
        with BackendSearchOrder([backend]):
            dataset = MSA(meta=self._create_msa_meta(msa_file))
            assert dataset._manager.name == backend
            assert dataset.msa is not None

    @pytest.mark.parametrize("backend", backends)
    def test_load_directory_of_msas(self, tmpdir, backend):
        test_dir = tmpdir / "msa_dir"
        test_dir.mkdir()

        msa_files = [
            (test_dir / "alignment1.fasta", ">seq1\nACGTACGT\n>seq2\nACGTA-GT\n"),
            (test_dir / "alignment2.fasta", ">seq3\nTGCATGCA\n>seq4\nTGCA-GCA\n"),
        ]
        for file_path, content in msa_files:
            with open(file_path, "w") as f:
                f.write(content)

        with BackendSearchOrder([backend]):
            dataset = MSA(meta=MSAMeta(file_path=str(test_dir), file_format="fasta"))
            assert len(dataset.msa) == 2

    @pytest.mark.parametrize("backend", backends)
    def test_invalid_file_path(self, backend):
        with pytest.raises(ValueError, match=r"No \(correct\) MSA file path provided"):
            with BackendSearchOrder([backend]):
                dataset = MSA(
                    meta=MSAMeta(
                        file_path="nonexistent_file.fasta", file_format="fasta"
                    )
                )
                print(dataset)

    @pytest.mark.parametrize("backend", backends)
    def test_unsupported_file_format(self, tmpdir, backend):
        invalid_file = tmpdir / "test.xyz"
        with open(invalid_file, "w") as f:
            f.write("dummy content")

        with BackendSearchOrder([backend]):
            with pytest.raises(ValueError, match="Biotite contains limited support|Unexpected format"):
                MSA(
                    meta=MSAMeta(file_path=str(invalid_file), file_format="xyz")
                )

    def test_no_backend_available(self):
        with pytest.raises(KeyError, match="nonexistent_backend"):
            with BackendSearchOrder(["nonexistent_backend"]):
                AbstractMSAManager.get_available_manager()

    @pytest.mark.skipif(not find_spec("biotite"), reason="biotite not installed")
    def test_biotite_manager(self, msa_file):
        with BackendSearchOrder(["biotite"]):
            manager = BiotiteMSAManager(meta=self._create_msa_meta(msa_file))
            alignment = manager.load_msa(msa_file)
            assert alignment

            alignments = manager.load_msas([msa_file])
            assert len(alignments) == 1
            assert Path(msa_file).name in alignments

    @pytest.mark.skipif(not find_spec("Bio"), reason="biopython not installed")
    def test_biopython_manager(self, msa_file):
        with BackendSearchOrder(["Bio"]):
            manager = BiopythonMSAManager(meta=self._create_msa_meta(msa_file))
            alignment = manager.load_msa(msa_file)
            assert alignment

            alignments = manager.load_msas([msa_file])
            assert len(alignments) == 1
            assert Path(msa_file).name in alignments

            assert "fasta" in manager.allowed_formats

    @pytest.mark.skipif(not find_spec("Bio"), reason="biopython not installed")
    def test_biopython_unsupported_format(self, msa_file):
        with BackendSearchOrder(["Bio"]):
            manager = BiopythonMSAManager(
                meta=MSAMeta(file_path=msa_file, file_format="invalid_format")
            )
            with pytest.raises(ValueError, match="Unexpected format.*Biopython only allows"):
                manager.load_msa(msa_file)

    @pytest.mark.skipif(not find_spec("biotite"), reason="biotite not installed")
    def test_biotite_unsupported_format(self, tmpdir):
        invalid_file = tmpdir / "test.xyz"
        with open(invalid_file, "w") as f:
            f.write("dummy content")

        with BackendSearchOrder(["biotite"]):
            manager = BiotiteMSAManager(
                meta=MSAMeta(file_path=str(invalid_file), file_format="xyz")
            )
            with pytest.raises(ValueError, match="Biotite contains limited support"):
                manager.load_msa(str(invalid_file))
