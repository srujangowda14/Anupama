import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence
import numpy as np

EMBED_DIM = 300

class WordEmbedding(nn.Module):
    """
    Wraps a pre-trained Word2Vec embedding matrix.
    By default frozen; set freeze=False to fine-tune.
    """
    def __init__(self, embedding_matrix: np.ndarray, freeze: bool = True):
        super().__init__()
        vocab_size, embed_dim = embedding_matrix.shape
        self.embedding = nn.Embedding(vocab_size, embed_dim, padding_idx=0)
        self.embedding.weight = nn.Parameter(
            torch.tensor(embedding_matrix, dtype=torch.float32),
            requires_grad=not freeze,
        )
        self.embed_dim = embed_dim

    def forward(self, x):
        return self.embedding(x)
    
class SharedBiLSTMEncoder(nn.Module):
    """
    BiLSTM that encodes a padded token sequence into:
      - last hidden state (for classification)
      - all hidden states (for attention / seq2seq)
    """
    def __init__(
        self,
        embed_dim: int = EMBED_DIM,
        hidden_dim: int = 256,
        num_layers: int = 2,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            embed_dim,
            hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0,
        )
        self.dropout = nn.Dropout(dropout)
        self.output_dim = hidden_dim * 2  # bidirectional

    def forward(self, embedded, lengths):
        """
        Args:
            embedded: (B, T, embed_dim)
            lengths:  (B,) actual sequence lengths (CPU tensor)
        Returns:
            all_hidden:  (B, T, hidden_dim*2)
            final_hidden: (B, hidden_dim*2)  — last valid timestep
        """
        embedded = self.dropout(embedded)
        packed = pack_padded_sequence(
            embedded, lengths.cpu(), batch_first=True, enforce_sorted=False
        )
        packed_out, (h_n, _) = self.lstm(packed)
        all_hidden, _ = pad_packed_sequence(packed_out, batch_first=True)

        # Concatenate last forward + last backward hidden states
        # h_n shape: (num_layers * 2, B, hidden_dim)
        fwd = h_n[-2]  # last layer, forward
        bwd = h_n[-1]  # last layer, backward
        final_hidden = torch.cat([fwd, bwd], dim=-1)  # (B, hidden_dim*2)

        return all_hidden, final_hidden