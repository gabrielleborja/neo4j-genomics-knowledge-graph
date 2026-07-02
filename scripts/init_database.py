import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase


load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

BASE_DIR = Path(__file__).resolve().parents[2]
IMPORT_DIR = BASE_DIR / "data" / "import"

REQUIRED_FILES = [
    IMPORT_DIR / "variants.csv",
    IMPORT_DIR / "genes.csv",
    IMPORT_DIR / "variant_gene.csv",
    IMPORT_DIR / "gene_disease.csv",
]


QUERIES = [
    {
        "name": "Criando constraint Variant",
        "query": """
        CREATE CONSTRAINT variant_id IF NOT EXISTS
        FOR (v:Variant)
        REQUIRE v.id IS UNIQUE
        """
    },
    {
        "name": "Criando constraint Gene",
        "query": """
        CREATE CONSTRAINT gene_symbol IF NOT EXISTS
        FOR (g:Gene)
        REQUIRE g.symbol IS UNIQUE
        """
    },
    {
        "name": "Criando constraint Disease",
        "query": """
        CREATE CONSTRAINT disease_umls_cui IF NOT EXISTS
        FOR (d:Disease)
        REQUIRE d.umls_cui IS UNIQUE
        """
    },
    {
        "name": "Importando nós Variant",
        "query": """
        LOAD CSV WITH HEADERS FROM 'file:///variants.csv' AS row
        WITH row
        WHERE row.VARIANT_ID IS NOT NULL AND trim(row.VARIANT_ID) <> ''
        MERGE (v:Variant {id: trim(row.VARIANT_ID)})
        SET v.chr = trim(row.CHR),
            v.start = CASE
                WHEN row.START_POSITION IS NULL OR trim(row.START_POSITION) = ''
                THEN null
                ELSE toInteger(row.START_POSITION)
            END,
            v.ref = trim(row.REF_ALLELE),
            v.alt = trim(row.ALT_ALLELE),
            v.frequency = CASE
                WHEN row.FREQUENCY IS NULL OR trim(row.FREQUENCY) = ''
                THEN null
                ELSE toFloat(row.FREQUENCY)
            END,
            v.predicted_consequence = CASE
                WHEN row.PRED_CONSEQUENCE IS NULL OR trim(row.PRED_CONSEQUENCE) = ''
                THEN null
                ELSE trim(row.PRED_CONSEQUENCE)
            END,
            v.predicted_function = CASE
                WHEN row.PREDICTED_FUNCTION IS NULL OR trim(row.PREDICTED_FUNCTION) = ''
                THEN null
                ELSE trim(row.PREDICTED_FUNCTION)
            END,
            v.cohort = CASE
                WHEN row.COHORT_NAME IS NULL OR trim(row.COHORT_NAME) = ''
                THEN null
                ELSE trim(row.COHORT_NAME)
            END,
            v.rsid = CASE
                WHEN row.AVSNP147 IS NULL
                  OR trim(row.AVSNP147) = ''
                  OR trim(row.AVSNP147) = 'Nao_catalogado'
                  OR trim(row.AVSNP147) = 'Não_catalogado'
                THEN null
                ELSE trim(row.AVSNP147)
            END
        """
    },
    {
        "name": "Importando nós Gene",
        "query": """
        LOAD CSV WITH HEADERS FROM 'file:///genes.csv' AS row
        WITH row
        WHERE row.GENE_NAME IS NOT NULL AND trim(row.GENE_NAME) <> ''
        MERGE (g:Gene {symbol: toUpper(trim(row.GENE_NAME))})
        SET g.in_abraom = true
        """
    },
    {
        "name": "Criando relações Variant -> Gene",
        "query": """
        LOAD CSV WITH HEADERS FROM 'file:///variant_gene.csv' AS row
        WITH row
        WHERE row.VARIANT_ID IS NOT NULL
          AND row.GENE_NAME IS NOT NULL
          AND trim(row.VARIANT_ID) <> ''
          AND trim(row.GENE_NAME) <> ''
        MATCH (v:Variant {id: trim(row.VARIANT_ID)})
        MERGE (g:Gene {symbol: toUpper(trim(row.GENE_NAME))})
        SET g.in_abraom = true
        MERGE (v)-[r:OCORRE_EM]->(g)
        SET r.frequency = v.frequency
        """
    },
    {
        "name": "Importando nós Disease e relações Gene -> Disease",
        "query": """
        LOAD CSV WITH HEADERS FROM 'file:///gene_disease.csv' AS row
        WITH row
        WHERE row.symbolOfGene IS NOT NULL
          AND row.diseaseUMLSCUI IS NOT NULL
          AND row.assocID IS NOT NULL
          AND trim(row.symbolOfGene) <> ''
          AND trim(row.diseaseUMLSCUI) <> ''
          AND trim(row.assocID) <> ''

        MERGE (g:Gene {symbol: toUpper(trim(row.symbolOfGene))})
        SET g.in_disgenet = true,
            g.ncbi_id = row.geneNcbiID,
            g.ncbi_type = row.geneNcbiType

        MERGE (d:Disease {umls_cui: trim(row.diseaseUMLSCUI)})
        SET d.name = row.diseaseName,
            d.type = row.diseaseType,
            d.inheritance = row.disease_inheritance,
            d.prevalence_class = row.disease_prevalence_class,
            d.prevalence_geo_area = row.disease_prevalence_geo_area,
            d.prevalence_type = row.disease_prevalence_type,
            d.source = "DisGeNET"

        MERGE (g)-[r:ASSOCIADO_A {assoc_id: row.assocID}]->(d)
        SET r.score = CASE
                WHEN row.score IS NULL OR trim(row.score) = ''
                THEN null
                ELSE toFloat(row.score)
            END,
            r.normalized_score = CASE
                WHEN row.normalized_score IS NULL OR trim(row.normalized_score) = ''
                THEN null
                ELSE toFloat(row.normalized_score)
            END,
            r.ei = CASE
                WHEN row.ei IS NULL OR trim(row.ei) = ''
                THEN null
                ELSE toFloat(row.ei)
            END,
            r.el = row.el,
            r.num_pmids = CASE
                WHEN row.numPMIDs IS NULL OR trim(row.numPMIDs) = ''
                THEN null
                ELSE toInteger(row.numPMIDs)
            END,
            r.year_initial = CASE
                WHEN row.yearInitial IS NULL OR trim(row.yearInitial) = ''
                THEN null
                ELSE toInteger(row.yearInitial)
            END,
            r.year_final = CASE
                WHEN row.yearFinal IS NULL OR trim(row.yearFinal) = ''
                THEN null
                ELSE toInteger(row.yearFinal)
            END,
            r.source = "DisGeNET",
            r.weight = CASE
                WHEN row.score IS NULL OR trim(row.score) = ''
                THEN null
                ELSE toFloat(row.score)
            END
        """
    },
]


VALIDATION_QUERIES = [
    (
        "Total de variantes",
        """
        MATCH (v:Variant)
        RETURN count(v) AS total
        """
    ),
    (
        "Total de genes",
        """
        MATCH (g:Gene)
        RETURN count(g) AS total
        """
    ),
    (
        "Total de doenças",
        """
        MATCH (d:Disease)
        RETURN count(d) AS total
        """
    ),
    (
        "Relações Variant -> Gene",
        """
        MATCH (:Variant)-[r:OCORRE_EM]->(:Gene)
        RETURN count(r) AS total
        """
    ),
    (
        "Relações Gene -> Disease",
        """
        MATCH (:Gene)-[r:ASSOCIADO_A]->(:Disease)
        RETURN count(r) AS total
        """
    ),
    (
        "Caminhos completos Variant -> Gene -> Disease",
        """
        MATCH (:Variant)-[:OCORRE_EM]->(:Gene)-[:ASSOCIADO_A]->(:Disease)
        RETURN count(*) AS total
        """
    ),
]


def check_required_files():
    missing = [
        str(path)
        for path in REQUIRED_FILES
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Arquivos obrigatórios não encontrados:\n" + "\n".join(missing)
        )


def run_queries(session):
    for item in QUERIES:
        print(f"\nExecutando: {item['name']}")
        session.run(item["query"])
        print("OK")


def validate(session):
    print("\nValidação final:")

    for title, query in VALIDATION_QUERIES:
        result = session.run(query).single()
        total = result["total"] if result else 0
        print(f"{title}: {total}")


def main():
    check_required_files()

    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    )

    with driver.session() as session:
        run_queries(session)
        validate(session)

    driver.close()

    print("\nBanco criado com sucesso.")
    print("Consulta principal para visualizar no Neo4j Browser:")
    print("""
MATCH (v:Variant)-[r1:OCORRE_EM]->(g:Gene)-[r2:ASSOCIADO_A]->(d:Disease)
RETURN v, r1, g, r2, d
LIMIT 50;
""")


if __name__ == "__main__":
    main()