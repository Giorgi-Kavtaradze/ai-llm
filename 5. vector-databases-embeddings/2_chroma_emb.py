from chromadb.utils import embedding_functions 
import numpy as np

default_ef = embedding_functions.DefaultEmbeddingFunction()

name = "Hi my name is Tornike"

emb = default_ef([name]) # type: ignore

print(np.array(emb).shape)  