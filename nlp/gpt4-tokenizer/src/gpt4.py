from overrides import overrides

import regex as re

from .base import Tokenizer

import tiktoken

class GPT4Tokenizer(Tokenizer):

    def __init__(self):
        super().__init__()

        gpt4_tokenizer = tiktoken.get_encoding("cl100k_base")

        self.gpt2_regex = re.compile(r"""'(?i:[sdmt]|ll|ve|re)|[^\r\n\p{L}\p{N}]?+\p{L}+|\p{N}{1,3}| ?[^\s\p{L}\p{N}]++[\r\n]*|\s*[\r\n]|\s+(?!\S)|\s+""")

        mergable_ranks = gpt4_tokenizer._mergeable_ranks

        self.encode_dict = self.__recover_merges(mergable_ranks)
        self.decode_dict = {v:k for k,v in mergable_ranks.items()}
        byte_shuffle = {i: mergable_ranks[bytes([i])] for i in range(256)}

        self.special_tokens = {
            '<|endoftext|>': 100257,
            '<|fim_prefix|>': 100258,
            '<|fim_middle|>': 100259,
            '<|fim_suffix|>': 100260,
            '<|endofprompt|>': 100276
        }

        print(byte_shuffle)


    def __bpe(self, mergeable_ranks, token, max_rank):
        # helper function used in get_gpt4_merges() to reconstruct the merge forest
        parts = [bytes([b]) for b in token]
        while True:
            min_idx = None
            min_rank = None
            for i, pair in enumerate(zip(parts[:-1], parts[1:])):
                rank = mergeable_ranks.get(pair[0] + pair[1])
                if rank is not None and (min_rank is None or rank < min_rank):
                    min_idx = i
                    min_rank = rank
            if min_rank is None or (max_rank is not None and min_rank >= max_rank):
                break
            assert min_idx is not None
            parts = parts[:min_idx] + [parts[min_idx] + parts[min_idx + 1]] + parts[min_idx + 2:]
        return parts

    def __recover_merges(self, mergeable_ranks):
        # the `merges` are already the byte sequences in their merged state.
        # so we have to recover the original pairings. We can do this by doing
        # a small BPE training run on all the tokens, in their order.
        # also see https://github.com/openai/tiktoken/issues/60
        # also see https://github.com/karpathy/minbpe/issues/11#issuecomment-1950805306
        merges = {}
        for token, rank in mergeable_ranks.items():
            if len(token) == 1:
                continue # skip raw bytes
            pair = tuple(self.__bpe(mergeable_ranks, token, max_rank=rank))
            assert len(pair) == 2
            # recover the integer ranks of the pair
            ix0 = mergeable_ranks[pair[0]]
            ix1 = mergeable_ranks[pair[1]]
            merges[(ix0, ix1)] = rank

        return merges

    def register_special_tokens(self, special_tokens):
        for v,k in special_tokens.items():
            self.special_tokens[v] = k

    @overrides
    def train(self, text:str, vocab_size:int, verbose=False):
        # it is pretrained
        raise NotImplementedError()

    @overrides
    def encode(self, text):
        pass

    @overrides
    def decode(self, tokens):
        pass