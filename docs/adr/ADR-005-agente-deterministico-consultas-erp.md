# ADR-005 — Agente determinístico de consultas ao ERP

**Status:** Aceito para a primeira versão (Caminho A); implementação e validação registradas separadamente após execução.

**Escopo:** Questão 8, Parte 5 da prova; proposta de evolução para a Questão 9.

**Apoio de IA:** Discuti os conceitos com o ChatGPT durante o estudo: intenção, campo, operadores, valores, parsing, identificação de entidades, ambiguidade, contexto e separação entre interpretador, Service e Repository. Escolhi o escopo da primeira versão após comparar uma alternativa simples (A) com uma mais abrangente (B). A IA auxiliou na redação e na elaboração inicial do código; a validação efetiva será documentada depois de executada.

## 1. Problema e objetivos

A Questão 8 pede um módulo que receba uma pergunta em linguagem natural sobre o ERP, interprete-a como ação/consulta estruturada sobre os dados de Produtos e Estoque e devolva JSON. O enunciado autoriza regras determinísticas e não exige acesso a serviços de LLM.

Quero demonstrar **o fluxo arquitetural completo**, e não um simulador de respostas fixas: entrada em português → interpretação estruturada → validação de regra → consulta real ao PostgreSQL → JSON.

## 2. Decisão: Caminho A

Escolhi um interpretador **determinístico, local, de leitura e com um único filtro por pergunta**. A primeira versão reconhecerá somente consultas de estoque e preço quando houver um campo explicitamente identificável, um operador e um valor numérico.

| Elemento | Decisão |
| --- | --- |
| Intenções | `consultar_estoque` e `consultar_produtos` (quando o filtro é preço) |
| Campos permitidos | `quantidade_em_estoque` e `preco` |
| Comparações | `<`, `>`, `=`, `<=`, `>=` |
| Vocabulário inicial | abaixo de/menor que/inferior a/menos de; acima de/maior que/superior a/mais de; igual a/exatamente; no mínimo; no máximo |
| Valores | inteiro não negativo para estoque; decimal não negativo para preço |
| Entrada | JSON com `pergunta` |
| Saída | JSON com intenção, filtro interpretado, total e produtos encontrados |
| Autenticação | Bearer JWT existente; sem nova política de autorização |
| Persistência | Consulta somente leitura à tabela `products` via SQLAlchemy |
| Limite | Resposta paginada/limitada para não devolver um catálogo ilimitado |

O agente não executa ações destrutivas e não envia a pergunta para serviços externos. Quando uma pergunta está fora do vocabulário, tem condições múltiplas ou é ambígua, **não tenta adivinhar**: retorna erro explicativo.

## 3. Responsabilidades

- **Router:** recebe o JSON, exige JWT e entrega a resposta.
- **Interpretador:** transforma uma pergunta reconhecida em um contrato estruturado com intenção, campo, operador e valor; não acessa banco, não gera SQL.
- **Service:** valida a operação e coordena o acesso a dados; decide o que retornar quando a pergunta não é suportada.
- **Repository:** usa apenas colunas explicitamente permitidas e operadores SQLAlchemy previamente mapeados; nunca executa SQL livre proveniente do texto.
- **Schemas Pydantic:** contratos de entrada, filtro e saída.

A separação é compatível com o ADR-002 e permite trocar o interpretador determinístico por um adaptador de LLM no futuro sem alterar a consulta de domínio.

## 4. Segurança, ambiguidades e limites

Não confio em campos, operadores ou valores arbitrários da entrada. Apenas os padrões aceitos podem gerar consultas. Não há execução dinâmica de SQL; as condições são compostas com expressões SQLAlchemy e os valores são passados de forma parametrizada. A API exige a identidade do funcionário como na Questão 6.

`re.search(r"\d+", pergunta)` isoladamente não é suficiente: em perguntas com dois números, extrairia o primeiro sem preservar a associação com o campo. Os padrões precisam relacionar **campo + operador + valor**. A primeira versão rejeita perguntas com múltiplos filtros (`e`/`ou`) em vez de retornar resultados parciais como se tivesse entendido tudo.

Casos não previstos explicitamente: nomes e modelos de produtos, referências como "o segundo", contexto entre mensagens, negação complexa, comparações com números escritos por extenso, sinônimos não cadastrados e ações de escrita. A limitação deve ser mostrada no README e nos erros retornados.

## 5. Alternativa B — Evolução futura, não implementada nesta etapa

Depois de validar o Caminho A, poderemos estudar:

1. **Filtros compostos:** lista de condições com `AND`/`OR`, precedência e agrupamento.
2. **Entidades:** extração de nomes de produtos e busca no banco; se houver múltiplas correspondências, devolver opções em vez de escolher arbitrariamente.
3. **Contexto:** manter a intenção e IDs de opções anteriores por sessão/autorização, com expiração, para entender respostas como "o segundo" e correções como "na verdade, teclados".
4. **LLM plugável:** um adaptador produzindo o mesmo contrato validado, sob allowlist de ferramentas, sem execução arbitrária de SQL; tema aprofundado na Questão 9.
5. **Confiabilidade:** testes de ambiguidade, limites de paginação, sanitização, métricas de erro de interpretação e observabilidade.

**Não considero o Caminho B requisito para concluir a Questão 8.** Primeiro validaremos o caso simples e real.

## 6. Critérios de aceitação do Caminho A

- Entender comparações simples de estoque e preço com valores numéricos.
- Respeitar a semântica inclusiva de "no mínimo" e "no máximo".
- Rejeitar frases desconhecidas ou com múltiplos filtros, em vez de inventar uma consulta.
- Consultar os produtos verdadeiros do PostgreSQL sem construir SQL a partir da frase.
- Exigir JWT e retornar JSON estruturado.
- Ter testes automatizados das regras, dos casos inválidos e do fluxo de consulta.
- Documentar exemplos, limites e resultados efetivamente verificados.

## 7. Registro de validação

**Implementação inicial publicada na branch (05/11/2026):** foram adicionados os módulos `app/modules/agent/` (schemas, interpreter, service, repository e router), o endpoint autenticado `POST /agent/query`, casos de teste em `tests/test_agent.py` e documentação no README. A implementação usa SQLAlchemy somente de leitura e rejeita condições múltiplas ou não reconhecidas. **A nova suíte de testes e o endpoint ainda não foram executados/validados no ambiente Docker do autor após esses commits.** Quando houver resultados, serão registrados sem sobrescrever as decisões iniciais.
