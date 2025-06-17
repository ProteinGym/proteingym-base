from importlib.util import find_spec
from pathlib import Path

import pytest

from pg2_dataset.backends.msa import (
    MSA,
    AbstractMSAManager,
    BackendSearchOrder,
    BiopythonMSAManager,
    BiotiteMSAManager,
)
from pg2_dataset.primitives.meta import MSAMeta

TEST_DATA_DIR = str(Path(__file__).parent.parent / "test_data" / "msa")


@pytest.mark.skipif(
    not find_spec("Bio") and not find_spec("biotite"), reason="no MSA backend"
)
class TestMSA:
    @pytest.fixture
    def msa_files(self, tmpdir):
        fasta_file = Path(tmpdir) / "test_alignment.fasta"
        fasta_content = ">seq1\nACGTACGT\n>seq2\nACGTA-GT\n>seq3\nACGT--GT\n"
        with open(fasta_file, "w") as f:
            f.write(fasta_content)
        return {"fasta": str(fasta_file)}

    def _check_backend(self, backend):
        if not find_spec(backend):
            pytest.skip(f"{backend} is not installed")

    def _create_msa_meta(self, msa_files):
        return MSAMeta(file_path=msa_files["fasta"], file_format="fasta")

    @pytest.mark.parametrize("backend", ["Bio", "biotite"])
    def test_msa_manager_initialization(self, msa_files, backend):
        self._check_backend(backend)
        with BackendSearchOrder([backend]):
            manager_cls = AbstractMSAManager.get_available_manager()
            assert manager_cls.name == backend

            manager = manager_cls(meta=self._create_msa_meta(msa_files))
            alignment = manager.load_msa(msa_files["fasta"])
            assert alignment is not None

    @pytest.mark.parametrize("backend", ["Bio", "biotite"])
    def test_msa_class_initialization(self, msa_files, backend):
        self._check_backend(backend)
        with BackendSearchOrder([backend]):
            dataset = MSA(meta=self._create_msa_meta(msa_files))
            assert dataset._manager.name == backend
            assert dataset.msa is not None

    @pytest.mark.parametrize("backend", ["Bio", "biotite"])
    def test_load_directory_of_msas(self, tmpdir, backend):
        self._check_backend(backend)

        test_dir = Path(tmpdir) / "msa_dir"
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

    @pytest.mark.parametrize("backend", ["Bio", "biotite"])
    def test_invalid_file_path(self, backend):
        self._check_backend(backend)
        with pytest.raises(ValueError):
            with BackendSearchOrder([backend]):
                dataset = MSA(
                    meta=MSAMeta(
                        file_path="nonexistent_file.fasta", file_format="fasta"
                    )
                )
                print(dataset)

    def test_unsupported_file_format(self, tmpdir):
        invalid_file = tmpdir / "test.xyz"
        with open(invalid_file, "w") as f:
            f.write("dummy content")

        for backend in ["Bio", "biotite"]:
            if find_spec(backend):
                with BackendSearchOrder([backend]):
                    with pytest.raises(ValueError):
                        dataset = MSA(
                            meta=MSAMeta(file_path=str(invalid_file), file_format="xyz")
                        )
                        print(dataset)

    def test_no_backend_available(self):
        with pytest.raises(KeyError):
            with BackendSearchOrder(["nonexistent_backend"]):
                AbstractMSAManager.get_available_manager()

    @pytest.mark.skipif(not find_spec("biotite"), reason="biotite not installed")
    def test_biotite_manager(self, msa_files):
        with BackendSearchOrder(["biotite"]):
            manager = BiotiteMSAManager(meta=self._create_msa_meta(msa_files))
            alignment = manager.load_msa(msa_files["fasta"])
            assert alignment is not None

            alignments = manager.load_msas([msa_files["fasta"]])
            assert len(alignments) == 1
            assert Path(msa_files["fasta"]).name in alignments

    @pytest.mark.skipif(not find_spec("Bio"), reason="biopython not installed")
    def test_biopython_manager(self, msa_files):
        with BackendSearchOrder(["Bio"]):
            manager = BiopythonMSAManager(meta=self._create_msa_meta(msa_files))
            alignment = manager.load_msa(msa_files["fasta"])
            assert alignment is not None

            alignments = manager.load_msas([msa_files["fasta"]])
            assert len(alignments) == 1
            assert Path(msa_files["fasta"]).name in alignments

            assert "fasta" in manager.allowed_formats

    @pytest.mark.skipif(not find_spec("Bio"), reason="biopython not installed")
    def test_biopython_unsupported_format(self, msa_files):
        with BackendSearchOrder(["Bio"]):
            manager = BiopythonMSAManager(
                meta=MSAMeta(file_path=msa_files["fasta"], file_format="invalid_format")
            )
            with pytest.raises(ValueError):
                manager.load_msa(msa_files["fasta"])

    @pytest.mark.skipif(not find_spec("biotite"), reason="biotite not installed")
    def test_biotite_unsupported_format(self, tmpdir):
        invalid_file = tmpdir / "test.xyz"
        with open(invalid_file, "w") as f:
            f.write("dummy content")

        with BackendSearchOrder(["biotite"]):
            manager = BiotiteMSAManager(
                meta=MSAMeta(file_path=str(invalid_file), file_format="xyz")
            )
            with pytest.raises(ValueError):
                manager.load_msa(str(invalid_file))
