import csv
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from neo4j import GraphDatabase


load_dotenv()

DISGENET_API_KEY = os.getenv("DISGENET_API_KEY")

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
BASE_URL = os.getenv("BASE_URL")

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "import"
DATA_DIR.mkdir(parents=True, exist_ok=True)

GENE_DISEASE_CSV = DATA_DIR / "gene_disease.csv"

CSV_FIELDS = [
    "symbolOfGene",
    "geneNcbiID",
    "geneNcbiType",
    "diseaseUMLSCUI",
    "diseaseName",
    "diseaseType",
    "disease_inheritance",
    "disease_prevalence_class",
    "disease_prevalence_geo_area",
    "disease_prevalence_type",
    "assocID",
    "score",
    "normalized_score",
    "ei",
    "el",
    "numPMIDs",
    "yearInitial",
    "yearFinal",
    "source",
]


def chunk_list(items, chunk_size):
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]


def get_genes_from_neo4j(driver):
    query = """
    MATCH (g:Gene)
    RETURN DISTINCT g.symbol AS symbol
    ORDER BY symbol
    """

    with driver.session() as session:
        result = session.run(query)
        return [
            record["symbol"]
            for record in result
            if record["symbol"]
        ]


def fetch_gene_disease_associations(gene_symbols):
    if not DISGENET_API_KEY:
        raise ValueError("DISGENET_API_KEY não encontrada no .env")

    headers = {
        "Authorization": f"Bearer {DISGENET_API_KEY}",
        "Accept": "application/json",
    }

    params = {
        "gene_symbol": gene_symbols,
    }

    response = requests.get(
        BASE_URL,
        headers=headers,
        params=params,
        timeout=30,
    )

    if response.status_code != 200:
        print("URL:", response.url)
        print("Status:", response.status_code)
        print("Resposta da API:")
        print(response.text)
        response.raise_for_status()

    return response.json()


def normalize_disgenet_response(data):
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ["payload", "results", "data", "items"]:
            if key in data and isinstance(data[key], list):
                return data[key]

    raise ValueError(
        f"Formato inesperado da resposta da API: {type(data)} | {data}"
    )


def filter_valid_associations(associations):
    valid = []

    for assoc in associations:
        if not isinstance(assoc, dict):
            continue

        if not assoc.get("symbolOfGene"):
            continue

        if not assoc.get("diseaseUMLSCUI"):
            continue

        if not assoc.get("assocID"):
            continue

        valid.append(assoc)

    return valid


def load_existing_csv_keys():
    """
    Lê o CSV já existente para evitar salvar associações duplicadas.
    A chave principal usada é assocID.
    """
    existing_keys = set()

    if not GENE_DISEASE_CSV.exists():
        return existing_keys

    with open(GENE_DISEASE_CSV, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            assoc_id = row.get("assocID")

            if assoc_id:
                existing_keys.add(assoc_id)

    return existing_keys


def save_associations_to_csv(associations):
    """
    Salva as associações válidas retornadas pela DisGeNET em um CSV persistente.
    O arquivo é salvo em data/import/gene_disease.csv.
    """
    if not associations:
        return 0

    existing_keys = load_existing_csv_keys()
    file_exists = GENE_DISEASE_CSV.exists()

    saved = 0

    with open(GENE_DISEASE_CSV, "a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)

        if not file_exists:
            writer.writeheader()

        for assoc in associations:
            assoc_id = assoc.get("assocID")

            if assoc_id in existing_keys:
                continue

            row = {
                field: assoc.get(field)
                for field in CSV_FIELDS
            }

            row["source"] = "DisGeNET"

            writer.writerow(row)

            existing_keys.add(assoc_id)
            saved += 1

    return saved


def save_associations_to_neo4j(driver, associations):
    query = """
    UNWIND $associations AS assoc

    WITH assoc
    WHERE assoc.symbolOfGene IS NOT NULL
      AND assoc.diseaseUMLSCUI IS NOT NULL
      AND assoc.assocID IS NOT NULL

    MERGE (g:Gene {symbol: assoc.symbolOfGene})
    SET g.ncbi_id = assoc.geneNcbiID,
        g.ncbi_type = assoc.geneNcbiType

    MERGE (d:Disease {umls_cui: assoc.diseaseUMLSCUI})
    SET d.name = assoc.diseaseName,
        d.type = assoc.diseaseType,
        d.inheritance = assoc.disease_inheritance,
        d.prevalence_class = assoc.disease_prevalence_class,
        d.prevalence_geo_area = assoc.disease_prevalence_geo_area,
        d.prevalence_type = assoc.disease_prevalence_type

    MERGE (g)-[r:ASSOCIADO_A {assoc_id: assoc.assocID}]->(d)
    SET r.score = toFloat(assoc.score),
        r.normalized_score = toFloat(assoc.normalized_score),
        r.ei = toFloat(assoc.ei),
        r.el = assoc.el,
        r.num_pmids = toInteger(assoc.numPMIDs),
        r.year_initial = toInteger(assoc.yearInitial),
        r.year_final = toInteger(assoc.yearFinal),
        r.source = "DisGeNET",
        r.weight = toFloat(assoc.score)
    """

    with driver.session() as session:
        session.run(query, associations=associations)


def main():
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    )

    genes = get_genes_from_neo4j(driver)

    print(f"{len(genes)} genes encontrados no Neo4j.")

    # Para testar sem gastar muitas chamadas do trial:
    # genes = genes[:20]

    imported = 0
    saved_csv = 0
    failed_batches = 0

    for batch in chunk_list(genes, 10):
        gene_param = ",".join(batch)

        print(f"\nBuscando associações para lote: {gene_param}")

        try:
            raw_response = fetch_gene_disease_associations(gene_param)

            associations = normalize_disgenet_response(raw_response)

            valid_associations = filter_valid_associations(associations)

            print(f"Total retornado pela API: {len(associations)}")
            print(f"Total válido para importar: {len(valid_associations)}")

            if not valid_associations:
                continue

            saved_now = save_associations_to_csv(valid_associations)
            save_associations_to_neo4j(driver, valid_associations)

            imported += len(valid_associations)
            saved_csv += saved_now

            print(f"{saved_now} associações salvas no CSV.")
            print(f"{len(valid_associations)} associações importadas no Neo4j.")

            time.sleep(1)

        except Exception as error:
            failed_batches += 1
            print(f"Erro ao processar lote {gene_param}: {error}")

    driver.close()

    print("\n==============================")
    print("Importação finalizada.")
    print(f"Genes considerados: {len(genes)}")
    print(f"Associações importadas no Neo4j: {imported}")
    print(f"Associações novas salvas no CSV: {saved_csv}")
    print(f"CSV gerado em: {GENE_DISEASE_CSV}")
    print(f"Lotes com erro: {failed_batches}")


if __name__ == "__main__":
    main()