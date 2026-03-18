import regex as re
from overrides import overrides
from .base import Tokenizer

class RegexTokenizer(Tokenizer):
    def __init__(self):
        super().__init__()

        self.regex = re.compile(r"""'(?i:[sdmt]|ll|ve|re)|[^\r\n\p{L}\p{N}]?+\p{L}+|\p{N}{1,3}| ?[^\s\p{L}\p{N}]++[\r\n]*|\s*[\r\n]|\s+(?!\S)|\s+""")

        # (int, int) -> int
        # basicly how to merge a specific pair into token
        self.encode_dict = {}

        # int -> bytes
        # token to the corresponding bytes
        self.decode_dict = {}

        # str -> int
        # special_token -> token
        self.special_tokens_encode = {}

        # int -> str
        # token -> special_token
        self.special_tokens_decode = {}

    def __count_pairs(self, encoded_text, stats = None):
        counts = {}
        for pair in zip(encoded_text, encoded_text[1:]):
            counts[pair] = counts.get(pair, 0) + 1

        if stats is not None:
            for pair, count in counts.items():
                stats[pair] = stats.get(pair, 0) + count
            return stats

        return counts

    def __merge(self, tokens, pair, merge_token):
        merged_tokens = []
        i = 0

        while i < len(tokens):
            # if we have a match we siwtch the pair tokens with our token
            if i+1 < len(tokens) and pair[0] == tokens[i] and pair[1] == tokens[i+1]:
                merged_tokens.append(merge_token)
                i+=2
            else: # if not just add the tokens as they are
                merged_tokens.append(tokens[i])
                i+=1

        return merged_tokens

    @overrides(check_signature=False)
    def train(self, text: str, vocab_size: int, verbose=False):
        assert vocab_size >= 256

        self.encode_dict = {}
        self.decode_dict = {}

        text_splitted = re.findall(self.regex, text)

        tokens_utf8 = [list(text_chunk.encode("utf-8")) for text_chunk in text_splitted]

        chunked_tokens = tokens_utf8

        num_merges = vocab_size - 256

        replace_token = 256

        self.decode_dict = {token_id: bytes([token_id]) for token_id in range(256)}


        for i in range(num_merges):
            counter = {}

            for chunk in chunked_tokens:
                counter = self.__count_pairs(chunk, counter)

            if not counter:
                break

            most_common_pair = max(counter.keys(), key=counter.get)

            chunked_tokens = [self.__merge(chunk, most_common_pair, replace_token)
                              for chunk in chunked_tokens]

            self.encode_dict[most_common_pair] = replace_token
            self.decode_dict[replace_token] = self.decode_dict[most_common_pair[0]] + self.decode_dict[most_common_pair[1]]

            if verbose:
                print(f"{i+1}/{num_merges} | Merging {most_common_pair} to {replace_token}")

            replace_token+=1

    def register_special_token(self, special_tokens):
        # special_tokens is a dictionary of str -> int
        # example: {"<|endoftext|>": 100257}
        self.special_tokens_encode = special_tokens

        # int -> str
        self.special_tokens_decode = {k: v for v, k in special_tokens.items()}



    def _encode_chunk(self, text_tokens):
        while len(text_tokens) >= 2:
            counter = self.__count_pairs(text_tokens)

            # choose the pair that was merged earliest during training
            # (i.e. the pair with the lowest merge index)
            # we only consider pairs that currently appear in the token sequence
            # this ensures we apply merges in the same order as they were learned during training
            pair = min(counter, key=lambda p: self.encode_dict.get(p, float("inf")))

            if pair not in self.encode_dict:
                break

            text_tokens = self.__merge(text_tokens, pair, self.encode_dict[pair])

        return text_tokens

    def _encode_ordinary(self, text):
        text_splitted = re.findall(self.regex, text)
        tokens_utf8 = [list(text_chunk.encode("utf-8")) for text_chunk in text_splitted]

        tokenized_string = []

        for chunk in tokens_utf8:
            tokenized_chunk = self._encode_chunk(chunk)
            tokenized_string.extend(tokenized_chunk)

        return tokenized_string

    @overrides
    def encode(self, text, allow_special='none_raise'):
        special = None
        if allow_special == "all":
            special = self.special_tokens_encode
        elif allow_special == "none":
            special = {}
        elif allow_special == "none_raise":
            special = {}
            assert all(token not in text for token in self.special_tokens_encode)
        elif isinstance(allow_special, set):
            special = {k: v for k, v in self.special_tokens_encode.items() if k in allow_special}
        else:
            raise ValueError(f"allowed_special={allow_special} not understood")
        if not special:
            # shortcut: if no special tokens, just use the ordinary encoding
            return self._encode_ordinary(text)

        special_pattern = "(" + "|".join(re.escape(k) for k in special) + ")"
        special_chunks = re.split(special_pattern, text)
        # now all the special characters are separated from the rest of the text
        # all chunks of text are encoded separately, then results are joined
        ids = []
        for part in special_chunks:
            if part in special:
                # pert with sepcial token
                ids.append(special[part])
            else:
                # part without special token, normal text to encode normally
                ids.extend(self._encode_ordinary(part))
        return ids



    @overrides
    def decode(self, tokens):

        text_bytes = b""

        for token in tokens:
            if token in self.decode_dict:
                text_bytes += self.decode_dict[token]
            elif token in self.special_tokens_decode:
                text_bytes += self.special_tokens_decode[token].encode("utf-8")
            else:
                raise ValueError("Bad token inside of the sentence")

        text_out = text_bytes.decode('utf-8', errors='replace')
        return text_out