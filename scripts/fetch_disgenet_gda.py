import os
import time
import requests

from dotenv import load_dotenv
from neo4j import GraphDatabase


load_dotenv()

DISGENET_API_KEY = os.getenv("DISGENET_API_KEY")

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
BASE_URL = os.getenv("BASE_URL")


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

            save_associations_to_neo4j(driver, valid_associations)

            imported += len(valid_associations)

            print(f"{len(valid_associations)} associações importadas.")

            time.sleep(1)

        except Exception as error:
            failed_batches += 1
            print(f"Erro ao processar lote {gene_param}: {error}")

    driver.close()

    print("\n==============================")
    print("Importação finalizada.")
    print(f"Genes considerados: {len(genes)}")
    print(f"Associações importadas: {imported}")
    print(f"Lotes com erro: {failed_batches}")


if __name__ == "__main__":
    main()