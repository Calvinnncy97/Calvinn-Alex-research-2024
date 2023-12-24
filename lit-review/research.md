### Fine-tuning + RAG
- [FLARE](https://arxiv.org/abs/2305.06983)
  
### Proposed Experiment
_Hypothesis_  
Training document embeddings with graph structure would yield better results compared to Transformer models.

Typically, embedding models are derived from a base language models. Fine-tuning techniques are applied to these base language models to separate linguisitcaly similar sentences but different semantically. These models rely on a set of [high quality, curated big dataset](https://arxiv.org/abs/2307.11224) to achieve superior performance. As the model is contrastively trained, it can be expected that it would not work well for out of distribution cases.   
  
The hypothesis is that by modelling chunks of documents as a graph node relative to other documents, and the model would be able to better learn the relation of different embeddings. Each document is represented with a node, and its relative document embedding is derived from the node embedding. 
  
_Model Comparisons_  
- GraphSage
- GraphSage + Graph Transformer
- GraphSage + BERT (This is proprietary. We will need to design the architecture ourselves. But essentially we are just adding the attention mechanism to the node embeddings.)
<br>

_Dataset Preparation_  
To create the edges that link the nodes, we can first tokenize each documents. The resulting tokens can then be transformed into a TF-IDF vector, where its features are the tokens.   

By clustering TF-IDF vectors, we can obtain clusters of relevant documents. Edges between nodes can be weighted by the inverse of the normalized distance between the nodes. Each cluster can then be modelled as a graph.
  
Alternatively, we can also use existing embedding models to achive the clustering. Multiple experiments can be done to compare the results.
