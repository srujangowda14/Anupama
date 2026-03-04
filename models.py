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

class ClassifierHead(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, dropout: float = 0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(input_dim, input_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(input_dim // 2, num_classes),
        )

    def forward(self, x):
        return self.net(x)
    
class CrisisClassifier(nn.Module):
    """
    3-class: 0=safe, 1=at_risk, 2=crisis
    Uses weighted cross-entropy to handle class imbalance
    (crisis examples are rare but critical).
    """
    NUM_CLASSES = 3
    CLASS_NAMES = ["safe", "at_risk", "crisis"]
    # Weight crisis class 5x, at_risk 3x to counteract imbalance
    CLASS_WEIGHTS = [1.0, 3.0, 5.0]

    def __init__(self, embedding: WordEmbedding, encoder: SharedBiLSTMEncoder):
        super().__init__()
        self.embedding = embedding
        self.encoder = encoder
        self.head = ClassifierHead(encoder.output_dim, self.NUM_CLASSES)

    def forward(self, token_ids, lengths):
        embedded = self.embedding(token_ids)
        _, final = self.encoder(embedded, lengths)
        logits = self.head(final)
        return logits

    def predict(self, token_ids, lengths):
        logits = self.forward(token_ids, lengths)
        probs = F.softmax(logits, dim=-1)
        labels = torch.argmax(probs, dim=-1)
        return labels, probs
    
class SentimentDetector(nn.Module):
    """
    5-class mood score (1=very negative, 5=very positive).
    Also returns a continuous valence score via regression head.
    """
    NUM_CLASSES = 5

    def __init__(self, embedding: WordEmbedding, encoder: SharedBiLSTMEncoder):
        super().__init__()
        self.embedding = embedding
        self.encoder = encoder
        self.class_head = ClassifierHead(encoder.output_dim, self.NUM_CLASSES)
        # Auxiliary regression head for smooth valence score not only 0, 1, 2, 3, 4, 5 it gives 2.7, 3.8...
        #captures intensity of sentiments good vs bad, bad vs terrible
        self.valence_head = nn.Sequential(
            nn.Linear(encoder.output_dim, 64),
            nn.GELU(),
            nn.Linear(64, 1),
            nn.Sigmoid(),  # output 0-1, scale to 1-5
        )

    def forward(self, token_ids, lengths):
        embedded = self.embedding(token_ids)
        _, final = self.encoder(embedded, lengths)
        logits = self.class_head(final)
        valence = self.valence_head(final).squeeze(-1) * 4 + 1  # 1-5 scale
        return logits, valence

    def predict(self, token_ids, lengths):
        logits, valence = self.forward(token_ids, lengths)
        probs = F.softmax(logits, dim=-1)
        labels = torch.argmax(probs, dim=-1) + 1  # 1-indexed
        return labels, valence.detach(), probs


# ─────────────────────────────────────────────────────────────────────────────
# MODEL 3: CBT DISTORTION TAGGER
# ─────────────────────────────────────────────────────────────────────────────

class CBTDistortionTagger(nn.Module):
    """
    11-class: 10 cognitive distortions + "none".
    Uses attention pooling over all hidden states
    (distortions often hinge on specific phrases, not just final state).
    """
    NUM_CLASSES = 11
    CLASS_NAMES = [
        "catastrophizing", "all_or_nothing", "mind_reading", "fortune_telling",
        "emotional_reasoning", "should_statements", "labeling", "personalization",
        "mental_filter", "discounting_positives", "none"
    ]

    def __init__(self, embedding: WordEmbedding, encoder: SharedBiLSTMEncoder):
        super().__init__()
        self.embedding = embedding
        self.encoder = encoder

        # Self-attention over encoder outputs for better phrase-level detection
        self.attn = nn.Linear(encoder.output_dim, 1)
        self.head = ClassifierHead(encoder.output_dim, self.NUM_CLASSES)

    def attention_pool(self, all_hidden, mask=None):
        """Soft attention pooling over encoder outputs."""
        scores = self.attn(all_hidden).squeeze(-1)     # (B, T)
        if mask is not None:
            scores = scores.masked_fill(mask == 0, float("-inf"))
        weights = F.softmax(scores, dim=-1).unsqueeze(-1)  # (B, T, 1)
        pooled = (all_hidden * weights).sum(dim=1)     # (B, hidden_dim*2)
        return pooled

    def forward(self, token_ids, lengths):
        embedded = self.embedding(token_ids)
        all_hidden, _ = self.encoder(embedded, lengths)

        # Build padding mask
        B, T, _ = all_hidden.shape
        mask = torch.arange(T, device=token_ids.device).unsqueeze(0) < lengths.unsqueeze(1)

        pooled = self.attention_pool(all_hidden, mask)
        logits = self.head(pooled)
        return logits

    def predict(self, token_ids, lengths):
        logits = self.forward(token_ids, lengths)
        probs = F.softmax(logits, dim=-1)
        labels = torch.argmax(probs, dim=-1)
        return labels, probs
    
class BahdanauAttention(nn.Module):
    """
    Bahdanau (additive) attention.
    Scores each encoder timestep against current decoder hidden state.
    """
    def __init__(self, enc_dim: int, dec_dim: int, attn_dim: int = 128):
        super().__init__()
        self.W_enc = nn.Linear(enc_dim, attn_dim, bias=False)
        self.W_dec = nn.Linear(dec_dim, attn_dim, bias=False)
        self.v = nn.Linear(attn_dim, 1, bias=False)

    def forward(self, enc_outputs, dec_hidden, src_mask=None):
        """
        enc_outputs: (B, T_src, enc_dim)
        dec_hidden:  (B, dec_dim)
        Returns:
            context: (B, enc_dim)
            attn_weights: (B, T_src)
        """
        enc_proj = self.W_enc(enc_outputs)               # (B, T, attn_dim)
        dec_proj = self.W_dec(dec_hidden).unsqueeze(1)   # (B, 1, attn_dim)
        scores = self.v(torch.tanh(enc_proj + dec_proj)).squeeze(-1)  # (B, T)

        if src_mask is not None:
            scores = scores.masked_fill(src_mask == 0, float("-inf"))

        attn_weights = F.softmax(scores, dim=-1)         # (B, T)
        context = (enc_outputs * attn_weights.unsqueeze(-1)).sum(dim=1)  # (B, enc_dim)
        return context, attn_weights


# ─────────────────────────────────────────────────────────────────────────────
# MODEL 4: SEQ2SEQ RESPONSE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

class Seq2SeqDecoder(nn.Module):
    def __init__(
        self,
        embedding: WordEmbedding,
        vocab_size: int,
        enc_dim: int,          # encoder output dim (hidden_dim * 2)
        dec_hidden_dim: int = 512,
        num_layers: int = 2,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.embedding = embedding
        self.dec_hidden_dim = dec_hidden_dim
        self.num_layers = num_layers

        self.attention = BahdanauAttention(enc_dim, dec_hidden_dim)
        self.dropout = nn.Dropout(dropout)

        # Input to decoder LSTM: [embed, context_vector]
        self.lstm = nn.LSTM(
            embedding.embed_dim + enc_dim,
            dec_hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )

        # Project encoder final hidden → decoder initial hidden
        self.enc2dec_h = nn.Linear(enc_dim, dec_hidden_dim * num_layers)
        self.enc2dec_c = nn.Linear(enc_dim, dec_hidden_dim * num_layers)

        # Output projection
        self.output_proj = nn.Linear(dec_hidden_dim + enc_dim + embedding.embed_dim, vocab_size)

    def init_hidden(self, enc_final_hidden):
        """Initialize decoder hidden state from encoder final state."""
        B = enc_final_hidden.size(0)
        h = self.enc2dec_h(enc_final_hidden)  # (B, dec_hidden * num_layers)
        c = self.enc2dec_c(enc_final_hidden)

        h = h.view(B, self.num_layers, self.dec_hidden_dim).transpose(0, 1).contiguous()
        c = c.view(B, self.num_layers, self.dec_hidden_dim).transpose(0, 1).contiguous()
        return h, c

    def forward_step(self, token_ids, hidden, cell, enc_outputs, src_mask=None):
        """
        One decoder timestep.
        token_ids: (B,)
        Returns: logits (B, vocab_size), new hidden, new cell, attn_weights
        """
        embedded = self.dropout(self.embedding(token_ids.unsqueeze(1)))  # (B, 1, E)

        dec_h_top = hidden[-1]  # top layer hidden: (B, dec_hidden)
        context, attn_w = self.attention(enc_outputs, dec_h_top, src_mask)  # (B, enc_dim)

        lstm_input = torch.cat([embedded, context.unsqueeze(1)], dim=-1)  # (B, 1, E+enc_dim)
        lstm_out, (new_h, new_c) = self.lstm(lstm_input, (hidden, cell))  # (B, 1, dec_dim)

        lstm_out = lstm_out.squeeze(1)  # (B, dec_dim)
        emb_squeezed = embedded.squeeze(1)  # (B, E)

        # Concatenate lstm output + context + embedding for rich output
        proj_input = torch.cat([lstm_out, context, emb_squeezed], dim=-1)
        logits = self.output_proj(proj_input)  # (B, vocab_size)

        return logits, new_h, new_c, attn_w
