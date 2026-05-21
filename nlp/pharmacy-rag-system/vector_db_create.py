import json
from time import sleep
from typing import List

import sys, os

from collections import deque

from itertools import batched

from dotenv import load_dotenv

from google import genai
from google.genai import types

from models import Medicament, InfoSection
import chromadb

def delete_duplicates(meds_json: List[Medicament]):
    names = set()
    meds_out = []
    for med in meds_json:
        if med.nazwa_handlowa in names:
            continue
        else:
            names.add(med.nazwa_handlowa)
            meds_out.append(med)
    return meds_out

def embedded_documents(meds: List[Medicament], batch_size=1):
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    chroma_client = chromadb.PersistentClient("./chroma_db")
    collection = chroma_client.get_collection(name="documents")

    queue = deque(batched(meds, batch_size))

    embeddings = []
    docs = []

    total_batches = len(queue)
    sleep_time = 0.5

    while len(queue) != 0:
        sleep(sleep_time)

        print(f"Progress: {total_batches - len(queue)}/{total_batches}")
        batch = queue.popleft()

        try:

            response = client.models.embed_content(
                model="gemini-embedding-001",
                contents=[types.Content(parts=[types.Part(text=el.rag_input_chunk)]) for el in batch],
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )

            vectors = [emb.values for emb in response.embeddings]

            embeddings.extend(vectors)
            docs.extend(batch)

            # -------------------------
            # BATCH INSERT TO CHROMA
            # -------------------------

            collection.upsert(
                documents=[doc.rag_input_chunk for doc in batch],
                embeddings=vectors,
                ids=[str(doc.id) for doc in batch],
                metadatas=[{"med_name": doc.nazwa_handlowa} for doc in batch])

            print(f"Added batch of {len(batch)} documents ({[str(doc.id) for doc in batch]})")
            sleep_time = 0.5

        except Exception as e:
            queue.append(batch)
            sleep_time = min(sleep_time * 2, 360)

            print(f"ERROR: {e}")

    return docs, embeddings

def init_database(path="./chroma_db"):
    try:
        client  = chromadb.PersistentClient(path)
        client.create_collection(name="documents")
    except Exception as e: pass

def main():
    load_dotenv("./.env")
    print("=" * 10, "DATABASE INIT", "=" * 10)
    init_database()

    print("="*10, "REMOVEING DUPLICATES", "="*10)
    data = json.load(open("./pharmacy_dataset_rag.json"))

    meds_json = [Medicament.from_dict(rec) for rec in data]
    meds_json_nodup = delete_duplicates(meds_json)

    print(f"Before depuclication: {len(meds_json)}\nAfter depuclication: {len(meds_json_nodup)}")

    print("="*10, "EMBED DOCS", "="*10)
    embedded_documents(meds_json_nodup)


if __name__ == "__main__":
    main()