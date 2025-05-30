from dataclasses import dataclass

import pandas as pd


@dataclass
class XAndY:
    x: pd.DataFrame
    y: pd.DataFrame

    def __len__(self) -> int:
        return len(self.x)

    def __iter__(self):
        return iter((self.x, self.y))