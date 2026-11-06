# Prova prática — Back-end e IA (ERP)

Resolução da prova técnica de Back-end e Inteligência Artificial aplicada a um cenário de ERP. A implementação segue uma proposta modular em FastAPI, com decisões documentadas em Architecture Decision Records (ADRs).

## Estado atual do projeto (05/11/2026)

O projeto utiliza FastAPI modular, PostgreSQL, Redis, autenticação JWT, processamento assíncrono com RQ e Docker Compose.

| Questão | Tema | Situação |
| --- | --- | --- |
| 1 | Arquitetura de Pedidos e Estoque | Documentada — ADR-001 |
| 2 | Organização do FastAPI | Documentada — ADR-002 |
| 3 | Concorrência em Python | Documentada — ADR-003 |
| 4 | Consulta concorrente e resiliência | Implementada |
| 5 | Escopo a conferir no enunciado | Não classificada neste README |
| 6 | API de Produtos, Estoque e JWT | Implementada e validada nos principais fluxos locais |
| 7 | Docker Compose e inicialização | Implementada e validada localmente |
| 8 | Agente determinístico para consultas ao ERP | Implementação inicial publicada; testes novos aguardam execução local |
| 9–11 | Etapas posteriores | Pendentes |

**Evidências locais:** depois de consolidar a suíte, **17 testes passaram**, segundo a execução relatada pelo autor; 4 testes de regras percorrem 14 cenários de estoque. O ambiente foi recriado com volumes novos usando apenas `docker compose up`, com migrations e seed automáticos. O workflow GitHub Actions está configurado, mas seu resultado remoto ainda não foi confirmado.

As validações locais e limitações técnicas são descritas abaixo e no [ADR-004](docs/adr/ADR-004-produtos-estoque-autenticacao-inicializacao.md).

## Parte 1 — Arquitetura e organização (Questões 1 e 2)

### Questão 1 — Arquitetura de Pedidos e Estoque

Escolhi uma aplicação **modular em FastAPI** para Pedidos e Estoque, integrada por contratos aos microsserviços já existentes de Clientes e Financeiro. Como o enunciado não fornece volume de usuários ou requisitos quantitativos de escala, preferi começar com um **monólito modular** em vez de criar novos serviços distribuídos sem necessidade comprovada.

- **Comunicação:** REST para consultas que exigem retorno imediato; eventos e tarefas assíncronas para processos desacoplados, com idempotência e recuperação de falhas. Um evento `PagamentoAprovado` e a Transactional Outbox são propostas arquiteturais, não funcionalidades entregues.
- **Persistência:** PostgreSQL como fonte de verdade; reservas de estoque precisam de transações e controle de concorrência. Redis será utilizado para cache e filas, sem substituir a consistência transacional.
- **Entrada e observabilidade:** Kong, Prometheus, Grafana, logs estruturados e tracing são opções de evolução; não foram implantados.
- **Crescimento:** antes de separar módulos ou ampliar infraestrutura, investigaria métricas, consultas, índices e gargalos reais.

Detalhes, alternativas e justificativas: [ADR-001](docs/adr/ADR-001-arquitetura-pedidos-estoque.md).

### Questão 2 — Organização do FastAPI

Optei por uma **organização por domínio e camadas**, inspirada na separação de responsabilidades que conheço do Java/Spring, mas adaptada aos recursos do FastAPI. Em operações com persistência, a direção é **Router → Service → Repository → ORM/PostgreSQL**, com schemas Pydantic. Não crio Repository quando não existe acesso a banco, como no resumo simulado da Questão 4.

A estrutura atual inclui `app/core/`, `app/modules/products/`, `app/modules/stock/`, `app/modules/orders/`, `app/modules/auth/`, `app/modules/employees/`, `app/integrations/`, `app/workers/` e `tests/`. Os módulos de Produtos e Estoque já implementam a API, a classificação de estoque e a integração com o worker.

Justificativas: [ADR-002](docs/adr/ADR-002-organizacao-fastapi.md).

## Parte 2 — Assíncrono e concorrência (Questões 3 e 4)

### Questão 3 — Asyncio, threading e multiprocessing

- **`asyncio`:** operações concorrentes de I/O com bibliotecas assíncronas, como consultas independentes a APIs.
- **`threading`:** operações bloqueantes de I/O, por exemplo, clientes HTTP síncronos legados; `asyncio.to_thread()` pode evitar bloquear o event loop.
- **`multiprocessing`:** cálculos intensivos de CPU, como processamento de grandes volumes para previsão de demanda, considerando os custos de processos e o GIL do CPython tradicional.

Comparações e evolução do raciocínio: [ADR-003](docs/adr/ADR-003-concorrencia-resiliencia.md).

### Questão 4 — Consulta concorrente com tratamento de falhas

Endpoint implementado: **`GET /orders/{order_id}/summary`**.

O endpoint consulta **Clientes, Estoque e Financeiro simulados** com `asyncio.gather()` e `asyncio.sleep()`. Cada operação tem timeout por tentativa, até **três tentativas totais** e backoff progressivo para timeouts/falhas transitórias. Erros permanentes não são repetidos; falhas de programação inesperadas são propagadas.

| Cenário | HTTP | Corpo |
| --- | --- | --- |
| Três fontes respondem | 200 | `status: "complete"` |
| Uma ou duas fontes falham de forma esperada | 200 | `status: "partial"`, dados disponíveis e avisos |
| Todas as fontes falham de forma esperada | 503 | `status: "unavailable"` |
| Erro inesperado interno | 500 | Erro interno, sem mascarar como indisponibilidade externa |

**Parâmetros padrão:** `REQUEST_TIMEOUT=2.0` segundos por tentativa, `MAX_ATTEMPTS=3` tentativas totais e `BACKOFF_BASE=0.5` segundo, gerando esperas de 0,5 s e 1 s antes dos retries.

**Limite da demonstração:** as integrações são mocks; esse endpoint não cria pedidos, reserva estoque nem efetua pagamentos. Os testes cobrem os cenários de sucesso, concorrência, timeout, retries, backoff, falha parcial, indisponibilidade total, falha permanente e erro interno. A suíte foi executada localmente na versão consolidada, com 17 testes aprovados segundo o relato do autor; a execução remota na CI ainda não foi confirmada.

Código: `app/modules/orders/`, `app/integrations/mock_services.py`, `app/integrations/retry.py` e `tests/test_order_summary.py`. Histórico das decisões: [ADR-003](docs/adr/ADR-003-concorrencia-resiliencia.md).

## Parte 3 — Produtos, Estoque e JWT (Questão 6)

> **Status:** implementação concluída para o escopo desenvolvido, com validação manual de seus fluxos principais e 17 testes aprovados na execução local informada pelo autor. A CI remota ainda requer verificação.

### Funcionalidades implementadas

- **Produtos:** `POST /products`, `GET /products`, `GET /products/{id}`, `PATCH /products/{id}` e `DELETE /products/{id}` (exclusivo de administrador).
- **Cadastro:** quantidade inicial de 12 ou mais; nome textual; preço Decimal não negativo.
- **Estoque:** 0 = sem estoque; 1–5 = últimas unidades; 6–12 = estoque baixo; 13+ = disponível. Atualizações posteriores podem chegar a zero.
- **Listagem:** `page`, `page_size`, `nome`, `preco_min`, `preco_max`, `estoque_baixo`.
- **Funcionários:** `POST /auth/login` com formulário `username` (e-mail) e `password` (senha); `GET /employees/me`; `POST /employees` apenas para administrador.
- **Autorização:** funcionários podem consultar, criar e alterar produtos; somente o administrador pode excluir produtos e cadastrar funcionários.
- **Redis:** cache-aside em `GET /products/{id}`, com TTL e invalidação após alterações.
- **RQ:** mudanças para faixas mais críticas enfileiram tarefa; o worker grava `stock_alerts` e emite log estruturado.
- **Persistência:** SQLAlchemy, PostgreSQL, Alembic; seed idempotente.

**Inicialização:** apenas `docker compose up`; a execução automática de migrations e seed está detalhada na Questão 7.

As credenciais demonstrativas estão documentadas no `.env.example`, **apenas para desenvolvimento local**; altere-as e substitua `JWT_SECRET` antes de expor o sistema. Dois logins demonstrativos:

| Perfil | E-mail | Senha demonstrativa |
| --- | --- | --- |
| Administrador | `admin@example.test` | `LocalAdmin123!` |
| Funcionário | `employee@example.test` | `LocalEmployee123!` |

Exemplo de login:

```bash
curl -X POST http://localhost:8000/auth/login \
  -d 'username=admin@example.test&password=LocalAdmin123!'
```

Os campos de cadastro de funcionários e as credenciais iniciais são demonstrativos, não um sistema completo de gestão de identidade.

### Evidências e limitações

**Evidências locais (05/11/2026):** com Postman, foram verificados login de admin e funcionário (`200`), acesso sem token (`401`), CRUD de produto e exclusão restrita ao administrador (`403` para funcionário, `204` para admin e `404` após exclusão), cadastro abaixo de 12 unidades (`422`), classificação de estoque, filtros por nome/preço/estoque baixo e paginação. O Redis apresentou uma chave preenchida após `GET /products/{id}` e ausência da chave após o PATCH (consistente com invalidação, mas o TTL também poderia explicar ausência tardia). O RQ recebeu e processou alertas reais, persistidos em `stock_alerts`; a alteração dentro da mesma faixa não gerou alerta. A primeira tentativa de alerta falhou porque a tabela `products` não estava registrada no metadata do worker; o import do modelo foi corrigido e as transições posteriores funcionaram. Após a refatoração, o autor informou **17 testes aprovados** no pytest.

**CI:** `.github/workflows/integration.yml` constrói o Compose, executa novamente init/seed e a suíte. Ainda não há resultado remoto confirmado. **Limitação de histórico:** a exclusão física de produto aciona `ON DELETE CASCADE` e remove alertas associados; isso deve ser considerado para evolução/auditoria.

Decisões técnicas: [ADR-004](docs/adr/ADR-004-produtos-estoque-autenticacao-inicializacao.md).

## Parte 4 — Infraestrutura e execução (Questão 7)

A inicialização foi projetada para ocorrer com **um único comando**, sem migrations ou seeds manuais. Os serviços aguardam as dependências necessárias, e os volumes preservam dados entre reinicializações. A recriação local com volumes vazios foi validada.

Pré-requisito: Docker Engine ou Docker Desktop com Docker Compose. Na raiz do projeto:

```bash
docker compose up
```

Para reconstruir a imagem após mudanças em dependências ou código:

```bash
docker compose up --build
```

O Compose define **seis serviços**: `postgres` (PostgreSQL 16), `redis` (Redis 7), `init` (migração Alembic + seed), `api` (FastAPI/Uvicorn), `worker` (RQ, fila `default`, processando alertas de estoque) e `ready` (mensagem de conclusão). `init` e `ready` são serviços de execução única; seu encerramento com código 0 é esperado.

Endereços locais com portas padrão:

- Swagger/OpenAPI: http://localhost:8000/docs
- Healthcheck da API: http://localhost:8000/health
- Resumo simulado: http://localhost:8000/orders/12345/summary
- PostgreSQL: `localhost:5433`; Redis está acessível apenas entre containers.

Personalização do ambiente:

```bash
cp .env.example .env
```

Edite o `.env` conforme necessário e recrie a API com `docker compose up -d --force-recreate api` para aplicar mudanças das variáveis. O Compose fornece valores padrão caso o `.env` não exista. O arquivo `.env` deve permanecer fora do Git; as credenciais do exemplo são **somente para desenvolvimento local**. Alterar a senha do PostgreSQL após inicializar seu volume não atualiza automaticamente a senha já persistida.

Comandos de verificação:

```bash
docker compose ps
docker compose config
docker compose exec api printenv REQUEST_TIMEOUT MAX_ATTEMPTS BACKOFF_BASE
docker compose down
```

O healthcheck da API confirma a resposta HTTP, sem testar diretamente PostgreSQL ou Redis. O Compose aguarda os healthchecks do PostgreSQL e Redis antes do serviço `init`. O serviço `ready` aguarda `api: service_healthy` e `worker: service_started` e imprime **`PROJETO INICIALIZADO CORRETAMENTE E PRONTO PARA TESTES`**; isso não garante, isoladamente, que o worker processou uma tarefa. Esse processamento foi validado separadamente. O comando `docker compose down` preserva volumes; **`docker compose down -v` apaga os volumes de dados**.

### Testes

Com o ambiente iniciado via `docker compose up`, execute em outro terminal, na raiz do projeto:

```bash
docker compose run --rm --no-deps -v "$PWD/tests:/srv/app/tests:ro" api python -m pytest -q
```

Também é possível executar `python -m pytest -q` diretamente, desde que as dependências, variáveis de ambiente e os serviços de PostgreSQL/Redis estejam configurados e acessíveis.

O Dockerfile não copia `tests/` por padrão; o comando acima monta a pasta somente para testes. **Resultado local informado após a refatoração: 17 testes aprovados.** O arquivo `test_stock_rules.py` contém 4 funções que verificam 14 cenários; a quantidade de testes coletados pelo pytest não é a quantidade de cenários percorridos. A execução não substitui a análise de casos não cobertos.

## Parte 5 — Agente determinístico de consultas (Questão 8)

**Escopo da versão A:** interpretador local determinístico, sem chamadas a APIs de LLM, que reconhece **uma única condição afirmativa** de estoque ou preço. Uma pergunta em português é convertida em intenção + filtro estruturado; o Service coordena e o Repository consulta os dados reais de `products` no PostgreSQL usando expressões SQLAlchemy, sem executar SQL fornecido pelo usuário.

### Como iniciar e testar no Swagger

1. Na raiz do projeto, em um primeiro clone, execute `docker compose up` (ele constrói as imagens ausentes). Se você **alterou o código** desde a última construção, execute `docker compose up -d --build` para incluir as mudanças na imagem. Aguarde `api` saudável em `docker compose ps`. Nenhum dos comandos apaga os volumes.
2. Acesse [Swagger](http://localhost:8000/docs).
3. Use **POST /auth/login** (formulário) com o usuário demonstrativo `employee@example.test` e senha `LocalEmployee123!` (somente ambiente local). Copie o `access_token` ou use **Authorize** com essas credenciais.
4. Abra **POST /agent/query**, clique em **Try it out**, cole o JSON abaixo e clique em **Execute**. Observe o código HTTP e o bloco **Server response → Response body**; o bloco **Responses → Example Value** é apenas um exemplo do esquema, não os dados consultados.

```json
{"pergunta": "Quais produtos estão com estoque abaixo de 10 unidades?"}
```

A resposta contém `intencao`, `filtros`, `situacao`, `mensagem`, `total`, `produtos` e `limite`. O filtro informa `campo` (`preco` ou `quantidade_em_estoque`), `operador` e `valor`. Produtos são ordenados por ID, com **limite máximo de 50 por consulta**; `total` considera todos os registros correspondentes, não apenas os 50 retornados. Não há paginação por cursor nesta versão.

### Exemplos para experimentar

| JSON: valor da chave `pergunta` | Interpretação | Resultado na seed inicial |
| --- | --- | --- |
| `Quais produtos estão com estoque abaixo de 10 unidades?` | Estoque `< 10` | 3 (Mouse, Headset, Webcam) |
| `Quero produtos com preço acima de 200 reais` | Preço `> 200` | 4 (Notebook, Monitor, Teclado, Headset) |
| `Quais produtos têm preço abaixo de 100 reais?` | Preço `< 100` | 0; consulta válida |
| `Quais produtos têm preço abaixo de 150 reais?` | Preço `< 150` | 1 (Mouse) |
| `Quais produtos têm preço abaixo de 190 reais?` | Preço `< 190` | 2 (Mouse, Webcam) |
| `Estoque no máximo 5` | Estoque `<= 5` | 2 (Headset, Webcam) |
| `Estoque no mínimo 13` | Estoque `>= 13` | 2 (Notebook, Monitor) |
| `Preço igual a 149,90` | Preço `= 149.90` | 1 (Mouse) |
| `Qual produto é o mais caro?` | Ranking não suportado | HTTP 422 |
| `Estoque abaixo de 5 e preço acima de 100` | Duas condições não suportadas | HTTP 422 |
| `Qual produto abaixo de 100 reais?` | Campo implícito, não suportado | HTTP 422 |

**Observação:** os resultados numéricos da tabela pressupõem a seed inicial intacta; se produtos forem criados/alterados, a resposta acompanha os dados reais do banco.

As expressões reconhecidas são: **abaixo de, menor que, inferior a, menos de** (`<`); **acima de, maior que, superior a, mais de** (`>`); **igual a, exatamente** (`=`); **no mínimo** (`>=`); **no máximo** (`<=`). É necessário informar o campo (`estoque` / `quantidade em estoque` ou `preço` / `valor`) imediatamente antes da expressão. Acentos e maiúsculas são normalizados. Estoque aceita inteiros não negativos, preço aceita decimal com uma ou duas casas, usando vírgula ou ponto, sem separador de milhar.

### Significado das respostas HTTP

**200, produtos encontrados:**

```json
{
  "intencao": "consultar_produtos",
  "filtros": [{"campo": "preco", "operador": "<", "valor": "150"}],
  "situacao": "encontrado",
  "mensagem": "1 produto(s) encontrado(s) para preço abaixo de 150.",
  "total": 1,
  "produtos": [
    {
      "id": 4,
      "nome": "Mouse sem fio",
      "preco": "149.90",
      "quantidade_em_estoque": 8,
      "data_criacao": "<data ISO 8601>",
      "data_atualizacao": "<data ISO 8601>",
      "situacao_estoque": "estoque_baixo",
      "alerta": "Estoque baixo"
    }
  ],
  "limite": 50
}
```

**200, pergunta compreendida mas sem correspondências:** não é uma falha; o banco respondeu corretamente à consulta.

```json
{
  "intencao": "consultar_produtos",
  "filtros": [{"campo": "preco", "operador": "<", "valor": "100"}],
  "situacao": "sem_resultados",
  "mensagem": "Nenhum produto encontrado para preço abaixo de 100.",
  "total": 0,
  "produtos": [],
  "limite": 50
}
```

**422, pergunta não suportada:** o interpretador não inventa uma intenção nem faz consulta parcial. Exemplo: `Qual produto é o mais caro?` gera erro explicativo com sugestões de formato, como `Estoque abaixo de 10` ou `Preço acima de 200`. Perguntas com `E`/`OU` ou negação também são rejeitadas. **401** indica token ausente ou inválido. O **422** também pode ocorrer por payload JSON inválido, como `pergunta` vazia, caso em que a validação do FastAPI/Pydantic fornece os detalhes.

### Executar testes automatizados

O `Dockerfile` **não copia a pasta `tests/` para a imagem da API**. Por isso, `docker compose exec api pytest tests/test_agent.py` sem volume montado produz `file or directory not found`. A maneira reproduzível de testar sem modificar a imagem é:

```bash
docker compose up -d --build
docker compose run --rm --no-deps -v "$PWD/tests:/srv/app/tests:ro" api python -m pytest -q -p no:cacheprovider tests/test_agent.py
# Para executar toda a suíte:
docker compose run --rm --no-deps -v "$PWD/tests:/srv/app/tests:ro" api python -m pytest -q -p no:cacheprovider
```

A pasta é montada somente para leitura; os testes de integração de API do agente usam SQLite em memória e substituem as dependências de banco/autenticação, enquanto os testes manuais acima foram executados com JWT e PostgreSQL reais.

**Evidência informada pelo autor em 05/11/2026:** a versão inicial do agente passou em **20 testes em 0,84 s** com `tests/` montada. Também foram observados pelo Swagger, usando JWT e PostgreSQL reais, os casos estoque `< 10` (3 registros), preço `> 200` (4), preço `< 100` (0), preço `< 150` (1) e preço `< 190` (2), além de perguntas não suportadas recebendo HTTP 422. **Revalidação final informada pelo autor (05/11/2026):** após a inclusão de `situacao`/`mensagem` e novos casos de teste, o autor confirmou que a suíte executada novamente passou, sem enviar a contagem/saída detalhada desta última execução. O Swagger confirmou a resposta nova para preço abaixo de 100 com HTTP 200, `situacao: "sem_resultados"`, mensagem explicativa, `total: 0` e lista vazia, usando JWT e PostgreSQL reais. A validação local do Caminho A está concluída para os cenários documentados. **A CI remota ainda não foi confirmada; o merge da Questão 8 na `main` não foi realizado.**

### Limites e caminhos futuros

**Caminho A:** somente uma condição por pergunta, sem contexto, nomes específicos de produtos, ranking `mais caro`, preço implícito por `reais`, números por extenso, SQL livre ou operações de escrita. O interpretador rejeita o que não entende.

**Caminho B (proposta, não implementada):** condições compostas `AND`/`OR`, identificação/desambiguação de produtos, contexto e referências como `o segundo`, adaptador de LLM produzindo o mesmo contrato validado, observabilidade, paginação e métricas. As decisões estão no [ADR-005](docs/adr/ADR-005-agente-deterministico-consultas-erp.md).

## Parte 5 — Evolução plugável para LLM, ferramentas e MCP (Questão 9)

> **Status: proposta teórica/design — não implementada.** A prova não exige integração com um LLM real nesta etapa. A versão executável continua sendo o agente determinístico da Questão 8.

### Decisão arquitetural

Eu adotaria uma **arquitetura híbrida**: o interpretador determinístico atende perguntas simples que reconhece integralmente; perguntas mais complexas podem ser encaminhadas a um adaptador plugável de LLM. O LLM **propõe** uma ferramenta de consulta e seus argumentos, mas nunca executa SQL livre nem tem acesso direto ao PostgreSQL. O backend valida schema, autorização e limites, encaminha a consulta ao Service e retorna os dados estruturados.

```text
Funcionário com JWT
    → API / orquestrador
      ├─→ Interpretador determinístico (Questão 8)
      │     → Service → Repository → PostgreSQL
      └─→ Adaptador de LLM (futuro)
            → validação de tool calling e autorização
            → cliente MCP → servidor MCP central
            → APIs/Services: Produtos, Pedidos, Financeiro
            → retorno estruturado e fundamentado
```

**Ferramentas propostas (somente leitura):** `consultar_produtos`, `consultar_estoque`, `consultar_pedido`, `consultar_valor_pedido` e `consultar_documentacao`. Cada ferramenta teria um contrato tipado, com argumentos validados, campos permitidos, limites de resultados e verificação de autorização. Ferramentas como `criar_pedido`, `atualizar_produto` e `excluir_pedidos` **não seriam expostas**, mesmo para usuários administradores.

**MCP central:** para os três domínios iniciais, prefiro um único servidor MCP publicando as ferramentas consultivas, sem concentrar regras de negócio. O MCP é a camada de adaptação; cada serviço continua responsável pelos dados e permissões. Em caso de aumento de carga ou autonomia de equipes, seria possível separar servidores MCP por domínio.

### Segurança e permissões

- O agente nunca cria, atualiza nem exclui registros. Essa proibição é imposta pelo catálogo e pelo executor de ferramentas, não apenas por uma instrução textual ao LLM.
- Ferramentas de consulta devem respeitar as permissões do usuário autenticado (RBAC e escopo do registro), com validação no backend e no serviço de destino. Não basta esconder ferramentas do modelo.
- **Financeiro inicial:** apenas consultas pontuais e autorizadas de pedidos, como valor total ou situação de pagamento. Faturamento global, margens, contas bancárias e análises financeiras profundas ficariam fora do catálogo inicial. Ampliação exigiria avaliação adicional de segurança e privacidade.
- Perguntas ambíguas pedem esclarecimento; valores devem vir da ferramenta e não ser inventados pelo modelo. Procedimentos devem ser fundamentados em documentação autorizada. Nenhum conteúdo retornado por uma ferramenta pode conceder novas permissões ao agente.

### Cache, falhas, custo e observabilidade

Quando o provedor de LLM falhar, as consultas simples continuam funcionando pelo interpretador local. Se o ERP estiver fora do ar, o Service **poderia** oferecer o último saldo conhecido apenas para dados cuja política de negócio permita cache antigo, com origem e horário de atualização visíveis. A hipótese de 30–60 minutos é ilustrativa para estoques pouco movimentados, **não um TTL definido para todos os produtos**. Dados antigos nunca devem ser tratados como saldo atual para efetivar uma venda ou reserva.

Antes de escolher um modelo ou provedor, avaliaria custo por tokens, cotas, volume, latência, privacidade e opções de hospedagem. Métricas propostas: uso de tokens/custo por funcionalidade, tempos p50/p95/p99, falhas de ferramentas, cache hit rate, taxa de fallback e rejeições de autorização. Prefiro **logs de metadados e IDs de correlação**, sem armazenar automaticamente prompts, respostas e dados financeiros sensíveis; qualquer auditoria de conteúdo exigiria política de acesso e retenção.

**Documento completo:** [ADR-006 — Evolução para LLM, Tool Calling e MCP](docs/adr/ADR-006-llm-mcp-guardrails-observabilidade.md). Ele diferencia claramente decisões de design e comportamento já implementado. Nenhum serviço MCP, adaptador de LLM ou ferramenta financeira foi implementado nesta etapa.

## Próximas etapas e verificações complementares

### Implementações seguintes

- **Questão 8:** escopo do Caminho A concluído e validado localmente conforme a seção acima; pendente apenas decisão posterior sobre merge na `main` e eventual confirmação da CI remota.
- **Questão 9:** desenho teórico concluído no ADR-006: LLM plugável, tool calling, MCP central, guardrails, cache, custo, latência e observabilidade. A implementação real não faz parte desta etapa.
- **Questões 10 e 11:** concluir os entregáveis previstos no enunciado, incluindo proposta conceitual em Go, portfólio e reflexão final.

### Verificações complementares

As Questões 6 e 7 foram implementadas e validadas nos principais fluxos locais. Ainda cabe:

- Confirmar o resultado remoto do GitHub Actions.
- Avaliar, como evolução futura, a preservação dos alertas quando um produto é excluído (`ON DELETE CASCADE`).
- Conferir o escopo da Questão 5 e manter README e ADRs consistentes com o avanço da prova.

Essas verificações não anulam os resultados locais já obtidos. O [ADR-004](docs/adr/ADR-004-produtos-estoque-autenticacao-inicializacao.md) registra as limitações técnicas conhecidas.

A documentação distingue o que foi **implementado**, o que foi **validado localmente**, o que foi apenas **decidido conceitualmente** e o que segue **pendente**.

## Uso de IA

- [ADR-001 — Arquitetura de Pedidos e Estoque](docs/adr/ADR-001-arquitetura-pedidos-estoque.md)
- [ADR-002 — Organização do FastAPI](docs/adr/ADR-002-organizacao-fastapi.md)
- [ADR-003 — Concorrência e resiliência](docs/adr/ADR-003-concorrencia-resiliencia.md)
- [ADR-004 — Produtos, Estoque, JWT e inicialização](docs/adr/ADR-004-produtos-estoque-autenticacao-inicializacao.md)
- [ADR-005 — Agente determinístico de consultas ao ERP](docs/adr/ADR-005-agente-deterministico-consultas-erp.md)
- [ADR-006 — Evolução para LLM, Tool Calling e MCP (Questão 9)](docs/adr/ADR-006-llm-mcp-guardrails-observabilidade.md)
- [Uso de IA — Registro de apoio e responsabilidades](docs/USO-DE-IA.md)

Utilizei o ChatGPT para estudo, questionamentos, alternativas de arquitetura, redação de documentos, propostas de implementação, testes e revisão. As escolhas e revisões estão registradas nos ADRs, e os resultados de testes somente serão declarados quando efetivamente verificados.
