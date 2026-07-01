// Doenças mais associadas ao BRCA1 por score
MATCH (g:Gene {symbol: "BRCA1"})-[r:ASSOCIADO_A]->(d:Disease)
RETURN g.symbol AS gene,
       d.name AS disease,
       r.weight AS weight,
       r.normalized_score AS normalized_score,
       r.num_pmids AS publications
ORDER BY r.weight DESC
LIMIT 20;

// Visualizar associações fortes
MATCH (g:Gene {symbol: "BRCA1"})-[r:ASSOCIADO_A]->(d:Disease)
WHERE r.weight >= 0.5
RETURN g, r, d;