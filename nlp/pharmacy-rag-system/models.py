from dataclasses import dataclass
from typing import List

@dataclass
class InfoSection:
    tytul: str
    tresc: str


@dataclass
class Medicament:
    id: int
    nazwa_handlowa: str
    substancja_czynna: str
    specyfikacja: str
    status_recepty: str
    ulotka_sekcje: List[InfoSection]
    rag_input_chunk: str

    @classmethod
    def from_dict(cls, data: dict):
        '''
        Takes single med of data set and converts it to Medicament class
        :param data: med json record
        :return: Medicament object with data from json
        '''
        sekcje = [InfoSection(**s) for s in data.get('ulotka_sekcje', [])]

        return cls(
            id=data['id'],
            nazwa_handlowa=data['nazwa_handlowa'],
            substancja_czynna=data['substancja_czynna'],
            specyfikacja=data['specyfikacja'],
            status_recepty=data['status_recepty'],
            ulotka_sekcje=sekcje,
            rag_input_chunk=data['rag_input_chunk']
        )