from abc import ABC, abstractmethod

class Tokenizer(ABC):
    @abstractmethod
    def train(self, text:str, vocab_size:int, verbose=False): pass

    @abstractmethod
    def encode(self, text): pass

    @abstractmethod
    def decode(self, tokens): pass