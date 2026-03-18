from overrides import overrides

import regex as re

from .regex import RegexTokenizer

import tiktoken

class GPT4Tokenizer(RegexTokenizer):

    def __init__(self):
        # (int, int) -> int
        # basicly how to merge a specific pair into token
        # self.encode_dict = {}
        # ---
        # int -> bytes
        # token to the corresponding bytes
        # self.decode_dict = {}
        # ---
        # str -> int
        # special_token -> token
        # self.special_tokens_encode = {}
        # ---
        # int -> str
        # token -> special_token
        # self.special_tokens_decode = {}
        super().__init__()

        gpt4_tokenizer = tiktoken.get_encoding("cl100k_base")

        mergable_ranks = gpt4_tokenizer._mergeable_ranks

        self.encode_dict = self.__recover_merges(mergable_ranks)

        decode_dict = {token: bytes([token]) for token in range(256)}

        for (token1, token2), token_out in self.encode_dict.items():
            decode_dict[token_out] = decode_dict[token1] + decode_dict[token2]

        self.decode_dict = decode_dict

        # normal byte -> permuted byte
        self.byte_shuffle = {i: mergable_ranks[bytes([i])] for i in range(256)}
        # permuted byte -> normal byte
        self.inverted_byte_shuffle = {k: v for v, k in self.byte_shuffle.items()}

        self.register_special_token({
            '<|endoftext|>': 100257,
            '<|fim_prefix|>': 100258,
            '<|fim_middle|>': 100259,
            '<|fim_suffix|>': 100260,
            '<|endofprompt|>': 100276
        })



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


    @overrides
    def train(self, text:str, vocab_size:int, verbose=False):
        # it is pretrained
        raise NotImplementedError()

    @overrides
    def _encode_chunk(self, text_tokens):
        text_tokens_permutated = bytes(self.byte_shuffle[token] for token in text_tokens)
        tokens = super()._encode_chunk(text_tokens_permutated)
        return tokens

    @overrides
    def decode(self, tokens):
        output = []

        byte_buffer = b""

        for token in tokens:
            if token in self.decode_dict:
                byte_buffer += self.decode_dict[token]

            elif token in self.special_tokens_decode:
                if byte_buffer:
                    byte_buffer = bytes(self.inverted_byte_shuffle[b] for b in byte_buffer)
                    output.append(byte_buffer.decode("utf-8", errors="replace"))
                    byte_buffer = b""

                output.append(self.special_tokens_decode[token])

            else:
                raise ValueError("Bad token")

        if byte_buffer:
            byte_buffer = bytes(self.inverted_byte_shuffle[b] for b in byte_buffer)
            output.append(byte_buffer.decode("utf-8", errors="replace"))

        return "".join(output)