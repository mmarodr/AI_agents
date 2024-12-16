from typing import Optional, Union
import numpy as np

class BasellmClient:
    # pass
    def __init__(self, model_text, model_emb):
        self.model_text         = model_text
        self.model_emb          = model_emb
    def update_model_parameters(self):
        pass
    def get_text(self):
        pass
    def get_embeddings(self) -> Optional[Union[list, np.ndarray]]:
        pass    