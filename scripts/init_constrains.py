import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase


load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")


CONSTRAINTS = [
    """
    CREATE CONSTRAINT variant_id IF NOT EXISTS
    FOR (v:Variant)
    REQUIRE v.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT gene_symbol IF NOT EXISTS
    FOR (g:Gene)
    REQUIRE g.symbol IS UNIQUE
    """,
    """
    CREATE CONSTRAINT disease_name IF NOT EXISTS
    FOR (d:Disease)
    REQUIRE d.name IS UNIQUE
    """
]


def main():
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )

    with driver.session() as session:
        for query in CONSTRAINTS:
            session.run(query)
            print("Constraint criada/verificada.")

    driver.close()
    print("Banco inicializado com sucesso.")


if __name__ == "__main__":
    main()