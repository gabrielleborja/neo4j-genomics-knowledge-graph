# Neo4j Genomics Knowledge Graph

Knowledge Graph biomédico utilizando **Neo4j**, integrando dados
genômicos da **ABraOM** e associações **Gene--Disease** da **DisGeNET**.

## Modelo do grafo

``` text
Variant Brasileira → Gene → Disease
```

## Como rodar

### 1. Configure o `.env`

Crie um arquivo `.env` na raiz do projeto:

``` env
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
DISGENET_API_KEY=sua_chave_aqui
```

### 2. Suba o Neo4j

``` bash
docker compose up -d
```

### 3. Acesse o Neo4j Browser

Endereço:

``` text
http://localhost:7474
```

Credenciais:

``` text
Usuário: neo4j
Senha: password123
Conexão: neo4j://localhost:7687
```

## Inicialização do banco

Execute o script de criação das constraints:

``` bash
python scripts/load/init_constraints.py
```

Ou execute manualmente o arquivo:

``` text
neo4j/cypher/constraints.cypher
```

## Consultas

As consultas Cypher utilizadas no projeto estão disponíveis em:

``` text
neo4j/cypher/queries.cypher
```

## Estrutura dos scripts

``` text
scripts/
├── fetch_disgenet_gda.py
├── load/
│   └── init_constraints.py
└── ...
```

## Dados

Os arquivos brutos da ABraOM devem ser armazenados em:

``` text
data/raw/abraom/
```

Os arquivos processados e prontos para importação devem ser armazenados
em:

``` text
data/processed/
data/import/
```

Não versionar arquivos grandes (`.gz`) no repositório.

## Status do projeto

-   Neo4j configurado via Docker Compose.
-   Integração com a API da DisGeNET funcionando.
-   Importação Gene → Disease implementada.
-   Próxima etapa: pré-processamento da ABraOM e importação das relações
    Variant → Gene.