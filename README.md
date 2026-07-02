# Neo4j Genomics Knowledge Graph

Knowledge Graph biomédico utilizando **Neo4j**, integrando dados genômicos da **ABraOM** com associações **Gene--Disease** da **DisGeNET**.

O objetivo do projeto é modelar dados biomédicos conectados em um banco NoSQL orientado a grafos, permitindo representar variantes genéticas brasileiras, genes e doenças como entidades relacionadas.

## Modelo do grafo

```text
(:Variant)-[:OCORRE_EM]->(:Gene)-[:ASSOCIADO_A]->(:Disease)
```

O grafo representa:

- `Variant`: variante genética observada na base ABraOM;
- `Gene`: gene associado à variante;
- `Disease`: doença associada ao gene;
- `OCORRE_EM`: relação entre variante e gene;
- `ASSOCIADO_A`: relação entre gene e doença, obtida a partir da DisGeNET.

## Como rodar

### 1. Configure o `.env`

Crie um arquivo `.env` na raiz do projeto:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

DISGENET_API_KEY=sua_chave_aqui
BASE_URL=https://api.disgenet.com/api/v1/gda/summary
```

A variável `DISGENET_API_KEY` só é necessária caso você deseje buscar novas associações diretamente na API da DisGeNET.

### 2. Suba o Neo4j

```bash
docker compose up -d
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Acesse o Neo4j Browser

Endereço:

```text
http://localhost:7474
```

Credenciais:

```text
Usuário: neo4j
Senha: password123
Conexão: bolt://localhost:7687
```

## Dados esperados

Os arquivos processados e prontos para importação devem estar em:

```text
data/import/
```

Arquivos esperados:

```text
variants.csv
genes.csv
variant_gene.csv
gene_disease.csv
```

Descrição dos arquivos:

- `variants.csv`: contém os dados dos nós `Variant`;
- `genes.csv`: contém os dados dos nós `Gene`;
- `variant_gene.csv`: contém as relações `Variant -> Gene`;
- `gene_disease.csv`: contém as associações `Gene -> Disease`, obtidas da DisGeNET.

Os arquivos brutos da ABraOM devem ser armazenados em:

```text
data/raw/abraom/
```

Os arquivos processados podem ser armazenados em:

```text
data/processed/
data/import/
```

Arquivos grandes, como `.gz`, não devem ser versionados no repositório.

## Inicialização do banco

Com o Neo4j rodando e os arquivos CSV posicionados em `data/import/`, execute:

```bash
python scripts/load/init_database.py
```

Esse script executa a criação do banco a partir dos CSVs processados. A pipeline realizada é:

1. criação das constraints de unicidade;
2. importação dos nós `Variant`;
3. importação dos nós `Gene`;
4. criação das relações `Variant -> Gene`;
5. importação dos nós `Disease`;
6. criação das relações `Gene -> Disease`.

Ao final da execução, o banco deve conter o caminho completo:

```text
Variant -> Gene -> Disease
```

## Buscar associações na DisGeNET

Caso o arquivo `gene_disease.csv` ainda não exista, ele pode ser gerado a partir da API da DisGeNET.

Para isso, primeiro é necessário que os genes já estejam presentes no Neo4j. Depois, execute:

```bash
python scripts/fetch_disgenet_gda.py
```

Esse script consulta os genes presentes no banco, busca associações gene-doença na DisGeNET e salva os resultados em:

```text
data/import/gene_disease.csv
```

Depois que o arquivo `gene_disease.csv` for gerado, execute novamente o script de inicialização:

```bash
python scripts/load/init_database.py
```

Assim, as associações Gene--Disease serão importadas para o Neo4j e reutilizadas posteriormente sem depender de novas chamadas à API.

## Validação da importação

Depois de criar os nós e relações, execute no Neo4j Browser:

### Total de variantes

```cypher
MATCH (v:Variant)
RETURN count(v) AS total_variantes;
```

### Total de genes

```cypher
MATCH (g:Gene)
RETURN count(g) AS total_genes;
```

### Total de doenças

```cypher
MATCH (d:Disease)
RETURN count(d) AS total_doencas;
```

### Total de relações `Variant -> Gene`

```cypher
MATCH (:Variant)-[r:OCORRE_EM]->(:Gene)
RETURN count(r) AS total_relacoes_variant_gene;
```

### Total de relações `Gene -> Disease`

```cypher
MATCH (:Gene)-[r:ASSOCIADO_A]->(:Disease)
RETURN count(r) AS total_relacoes_gene_doenca;
```

### Total de caminhos completos

```cypher
MATCH (:Variant)-[:OCORRE_EM]->(:Gene)-[:ASSOCIADO_A]->(:Disease)
RETURN count(*) AS total_caminhos_completos;
```

### Verificar genes duplicados

```cypher
MATCH (g:Gene)
WITH g.symbol AS gene, count(*) AS qtd
WHERE qtd > 1
RETURN gene, qtd
ORDER BY qtd DESC;
```

O esperado é que essa consulta não retorne linhas.

## Consultas principais

As consultas Cypher utilizadas no projeto também podem ser armazenadas em:

```text
neo4j/cypher/queries.cypher
```

### Visualizar relações `Variant -> Gene`

```cypher
MATCH (v:Variant)-[r:OCORRE_EM]->(g:Gene)
RETURN v, r, g
LIMIT 50;
```

Essa consulta mostra a primeira parte do grafo, conectando variantes genéticas brasileiras aos genes associados.

### Visualizar relações `Gene -> Disease`

```cypher
MATCH (g:Gene)-[r:ASSOCIADO_A]->(d:Disease)
RETURN g, r, d
LIMIT 50;
```

Essa consulta mostra as associações gene-doença importadas a partir da DisGeNET.

### Visualizar caminho completo

```cypher
MATCH (v:Variant)-[r1:OCORRE_EM]->(g:Gene)-[r2:ASSOCIADO_A]->(d:Disease)
RETURN v, r1, g, r2, d
LIMIT 50;
```

Essa é a consulta principal do projeto, pois demonstra a integração entre ABraOM e DisGeNET no caminho:

```text
Variant -> Gene -> Disease
```

### Resultado tabular do caminho completo

```cypher
MATCH (v:Variant)-[:OCORRE_EM]->(g:Gene)-[r:ASSOCIADO_A]->(d:Disease)
RETURN v.id AS variante,
       v.rsid AS rsid,
       v.frequency AS frequencia,
       g.symbol AS gene,
       d.name AS doenca,
       r.score AS score,
       r.normalized_score AS score_normalizado,
       r.num_pmids AS publicacoes
ORDER BY r.score DESC
LIMIT 50;
```

Essa consulta mostra o caminho completo em formato tabular, facilitando a leitura dos resultados.

### Consulta por gene específico

```cypher
MATCH (v:Variant)-[:OCORRE_EM]->(g:Gene)-[r:ASSOCIADO_A]->(d:Disease)
WHERE g.symbol = "BRCA1"
RETURN v.id AS variante,
       v.rsid AS rsid,
       v.frequency AS frequencia,
       g.symbol AS gene,
       d.name AS doenca,
       r.score AS score,
       r.num_pmids AS publicacoes
ORDER BY r.score DESC
LIMIT 30;
```

Essa consulta pode ser adaptada para qualquer gene presente no banco.

### Genes com mais doenças associadas

```cypher
MATCH (g:Gene)-[:ASSOCIADO_A]->(d:Disease)
RETURN g.symbol AS gene,
       count(DISTINCT d) AS total_doencas
ORDER BY total_doencas DESC
LIMIT 20;
```

Essa consulta permite identificar genes com maior número de doenças associadas no grafo.

### Genes com variantes brasileiras e doenças associadas

```cypher
MATCH (v:Variant)-[:OCORRE_EM]->(g:Gene)-[:ASSOCIADO_A]->(d:Disease)
RETURN g.symbol AS gene,
       count(DISTINCT v) AS total_variantes,
       count(DISTINCT d) AS total_doencas
ORDER BY total_doencas DESC, total_variantes DESC
LIMIT 20;
```

Essa consulta mostra genes que conectam variantes brasileiras da ABraOM com doenças catalogadas na DisGeNET.

### Visualização em grafo dos genes mais conectados

```cypher
MATCH (v:Variant)-[r1:OCORRE_EM]->(g:Gene)-[r2:ASSOCIADO_A]->(d:Disease)
WITH g,
     count(DISTINCT v) AS total_variantes,
     count(DISTINCT d) AS total_doencas
ORDER BY total_doencas DESC, total_variantes DESC
LIMIT 3

MATCH (v:Variant)-[r1:OCORRE_EM]->(g)-[r2:ASSOCIADO_A]->(d:Disease)
RETURN v, r1, g, r2, d
LIMIT 50;
```

Essa consulta é útil para apresentação visual no Neo4j Browser, pois evita que o grafo fique muito poluído.

## Interpretação do score Gene--Disease

A relação `ASSOCIADO_A` possui propriedades vindas da DisGeNET, como:

- `score`;
- `normalized_score`;
- `num_pmids`;
- `source`.

O `score` pode ser interpretado como uma medida de suporte ou evidência da associação gene-doença na DisGeNET. Valores mais altos indicam associações mais bem documentadas na base.

No entanto, esse valor não deve ser interpretado automaticamente como causalidade biológica direta. Ele indica evidência de associação, não necessariamente que o gene cause sozinho a doença.

## Estrutura dos scripts

```text
scripts/
├── fetch_disgenet_gda.py
├── init_database.py
└── ...
```

## Estrutura geral do projeto

```text
.
├── data/
│   └── import/
│       ├── variants.csv
│       ├── genes.csv
│       ├── variant_gene.csv
│       └── gene_disease.csv
├── neo4j/
├── scripts/
│   ├── fetch_disgenet_gda.py
│   └── init_database.py
├── docker-compose.yml
├── requirements.txt
└── README.md
```