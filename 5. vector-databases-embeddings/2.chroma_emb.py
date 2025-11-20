from chromadb.utils import embedding_functions 

default_ef = embedding_functions.DefaultEmbeddingFunction()

name = "Hi my name is Tornike"

emb = default_ef(name)

print(emb)