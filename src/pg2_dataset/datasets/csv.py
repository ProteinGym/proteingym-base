import io
import random
import pandas as pd
from pg2_dataset.datasets.dataset import Dataset
from pg2_dataset.io.bytes import read_bytes


class CSVDataset(Dataset):
    def __init__(
        self,
        file_path: str,
        input_keys: list[str],
        train_size: int,
        test_size: int,
        seed: int = 0,
        index_col: int | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.file_path = file_path
        self.input_keys = input_keys
        self.seed = seed

        self.index_col = index_col

        self.train_size = train_size
        self.test_size = test_size

        data_str = read_bytes(file_path).decode("utf-8")
        data = pd.read_csv(io.StringIO(data_str), index_col=index_col)

        # shuffle by input_keys
        if not set(input_keys).issubset(set(data.columns)):
            raise ValueError(f"expected features {input_keys} missing.")
        
        random.seed(seed)

        groups = [df for _, df in data.groupby(input_keys)]
        random.shuffle(groups)

        self._dataset = pd.concat(groups).reset_index(drop=True).to_dict(orient="records")
