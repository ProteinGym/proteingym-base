import io
import random
import pandas as pd
from sklearn.model_selection import train_test_split
from pg2_dataset.datasets.dataset import Dataset
from pg2_dataset.io.bytes import read_bytes


class CSVDataset(Dataset):
    def __init__(
        self,
        file_path: str,
        input_keys: list[str],
        seed: int = 0,
        train_size: int | None = None,
        test_size: int | None = None,
        index_col: int | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.file_path = file_path
        self.input_keys = input_keys
        self.seed = seed

        self.train_size = train_size
        self.test_size = test_size
        self.index_col = index_col

        data_str = read_bytes(file_path).decode("utf-8")
        data = pd.read_csv(io.StringIO(data_str), index_col=index_col)

        # shuffle by input_keys
        if not set(input_keys).issubset(set(data.columns)):
            raise ValueError(f"expected features {input_keys} missing.")
        
        random.seed(seed)

        groups = [df for _, df in data.groupby(input_keys)]
        random.shuffle(groups)

        self._dataset = pd.concat(groups).reset_index(drop=True).to_dict(orient="records")

        self._train = self._dataset[:train_size]
        self._test = self._dataset[train_size: train_size+test_size]
