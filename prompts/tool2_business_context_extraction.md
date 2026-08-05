# Tool 2 Business Context Extraction

Analiza la documentacion de negocio y devuelve JSON valido con estas claves exactas:

- business_terms
- definitions
- business_rules
- kpis
- processes
- states
- synonyms
- candidate_entities
- candidate_relationships
- ambiguities
- questions_for_workshop

Reglas obligatorias:

1. No inventes datos fuera del contenido provisto.
2. Cada elemento debe incluir el `source_chunk_id` exacto del chunk que lo sustenta. No inventes IDs.
3. Cada elemento debe incluir `source_excerpt` con un fragmento breve que respalde la extraccion.
4. `source_document_id` sera normalizado por la aplicacion a partir del chunk; no lo uses como sustituto del chunk.
5. Cada termino, definicion, regla, KPI, entidad candidata o relacion candidata debe incluir `confidence` y `status`.
6. Usa `pending_review` como estado por defecto cuando no exista validacion humana.
7. Si hay contradicciones o definiciones multiples, registralas en `ambiguities`.
8. Si faltan definiciones o decisiones clave, conviertelas en `questions_for_workshop`.
9. Aprovecha los conceptos tecnicos ya conocidos del proyecto solo como contexto para matching, no como verdad de negocio.
10. La salida debe ser exclusivamente JSON valido, sin texto extra.

Estructuras sugeridas:

- business_terms: `{ "term": "...", "source_chunk_id": "...", "source_excerpt": "...", "confidence": 0.0, "status": "pending_review" }`
- definitions: `{ "term": "...", "definition": "...", "source_chunk_id": "...", "source_excerpt": "...", "confidence": 0.0, "status": "pending_review" }`
- business_rules: `{ "text": "...", "source_chunk_id": "...", "source_excerpt": "...", "confidence": 0.0, "status": "pending_review" }`
- kpis: `{ "text": "...", "source_chunk_id": "...", "source_excerpt": "...", "confidence": 0.0, "status": "pending_review" }`
- candidate_entities: `{ "term": "...", "matched_semantic_object": "...", "source_chunk_id": "...", "source_excerpt": "...", "confidence": 0.0, "status": "suggested" }`
- candidate_relationships: `{ "source_term": "...", "target_term": "...", "relationship_type": "...", "source_chunk_id": "...", "source_excerpt": "...", "confidence": 0.0, "status": "suggested" }`
- ambiguities: `{ "concept": "...", "issue": "...", "severity": "low|medium|high", "source_chunk_id": "...", "source_excerpt": "..." }`
- questions_for_workshop: `{ "question": "...", "source_chunk_id": "...", "source_excerpt": "...", "priority": "low|medium|high" }`
