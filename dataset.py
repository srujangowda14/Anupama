import os
import re
import json
import pickle
import numpy as np
from collections import Counter
from typing import Optional

import torch
from torch.utils.data import Dataset
from torch.nn.utils.rnn import pad_sequence

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

EMBED_DIM = 300
PAD_TOKEN = "<PAD>"
UNK_TOKEN = "<UNK>"
SOS_TOKEN = "<SOS>"
EOS_TOKEN = "<EOS>"
SPECIAL_TOKENS = [PAD_TOKEN, UNK_TOKEN, SOS_TOKEN, EOS_TOKEN]

# Conditioning tokens prepended to decoder input to control response tone
COND_TOKENS = [
    "<CRISIS>", "<AT_RISK>", "<SAFE>",          # crisis level
    "<MOOD_1>", "<MOOD_2>", "<MOOD_3>", "<MOOD_4>", "<MOOD_5>",  # mood
    "<MODE_SUPPORT>", "<MODE_CBT>", "<MODE_INTAKE>",              # session mode
    "<DISTORTION>", "<NO_DISTORTION>",           # CBT signal
]
