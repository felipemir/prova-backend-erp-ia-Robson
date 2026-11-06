# ADR-005 — Agente determinístico de consultas ao ERP

**Status:** Aceito; Caminho A implementado e validado nos cenários registrados abaixo. Melhorias de resposta aguardam nova execução local.

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
| Saída | JSON com intenção, filtro interpretado, situação, mensagem, total e produtos encontrados |
| Autenticação | Bearer JWT existente; sem nova política de autorização |
| Persistência | Consulta somente leitura à tabela `products` via SQLAlchemy |
| Limite | No máximo 50 produtos por resposta, ordenados por ID; total considera todas as correspondências, sem paginação nesta versão |

O agente não executa ações destrutivas e não envia a pergunta para serviços externos. Quando uma pergunta está fora do vocabulário, tem condições múltiplas ou é ambígua, **não tenta adivinhar**: retorna erro explicativo.

## 3. Responsabilidades

- **Router:** recebe o JSON, exige JWT e entrega a resposta.
- **Interpretador:** transforma uma pergunta reconhecida em um contrato estruturado com intenção, campo, operador e valor; não acessa banco, não gera SQL.
- **Service:** valida a operação e coordena o acesso a dados; diferencia consulta com registros, consulta válida sem resultados e pergunta não suportada.
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

## 7. Contrato de resposta e casos de erro

A decisão foi preservar a semântica HTTP em vez de transformar uma busca sem registros em erro:

| Caso | HTTP | Resultado |
| --- | --- | --- |
| Pergunta entendida, produtos encontrados | 200 | `situacao: "encontrado"`, `mensagem` e itens |
| Pergunta entendida, nenhum produto corresponde | 200 | `situacao: "sem_resultados"`, `mensagem` explicativa, `total: 0` e `produtos: []` |
| Pergunta não reconhecida / múltiplas condições | 422 | `detail` explica o limite e sugere exemplos válidos |
| Token ausente, inválido ou expirado | 401 | Autenticação existente no FastAPI |
| Corpo JSON inválido | 422 | Detalhes de validação Pydantic |

Exemplo conceitual: para `Preço abaixo de 100`, a seed inicial não contém produtos correspondentes. Retornar 200 com uma explicação e lista vazia permite distinguir **ausência de dados correspondentes** de **falha de interpretação**, que recebe 422.

O interpretador não busca ou conhece os produtos. Ele reconhece apenas padrões suportados; o Repository consulta o PostgreSQL. Perguntas como `Qual produto é o mais caro?` e `Qual produto abaixo de 100 reais?` ainda são incompatíveis com o Caminho A. Não afirmamos que elas são compreendidas apenas porque fazem sentido para um humano.

## 8. Registro de validação e revisão

- **Implementação inicial publicada (05/11/2026):** módulos `app/modules/agent/`, rota autenticada `POST /agent/query`, `tests/test_agent.py` e documentação.
- **Teste automatizado inicial informado pelo autor (05/11/2026):** **20 testes aprovados em 0,84 s** com a pasta `tests/` montada no container. O `Dockerfile` não copia os testes; isso explica os erros iniciais de arquivo ausente no container, não uma falha do agente. O teste do módulo usa SQLite em memória e substitui dependências; ele não equivale ao teste manual contra PostgreSQL e JWT reais.
- **Evidências manuais informadas pelo autor, Swagger/JWT/PostgreSQL:** estoque abaixo de 10 (3 produtos), preço acima de 200 (4), preço abaixo de 100 (0, HTTP 200), abaixo de 150 (1), abaixo de 190 (2). Perguntas de ranking e de campo implícito receberam HTTP 422, conforme o escopo.
- **Melhoria após os testes:** foram adicionados `situacao` e `mensagem` para os retornos 200 e mensagens de erro 422 mais orientativas, sem alterar a regra de consulta. Novos testes cobrem resposta sem correspondências e pergunta não suportada. **Ainda é necessário reexecutar a suíte após essas alterações**, inclusive a suíte geral, e validar os novos campos no Swagger. Não há resultado de CI remota confirmado para essa versão.

O README agora traz preparação, autenticação no Swagger, exemplos com entradas e saídas, tabela de comportamentos HTTP e comando de testes com volume `tests/` montado, além das limitações e do plano B.

