# Prova prática — Back-end e IA (ERP)

Resolução da prova técnica de Back-end e Inteligência Artificial aplicada a um cenário de ERP. A implementação segue uma proposta modular em FastAPI, com decisões documentadas em Architecture Decision Records (ADRs).

> **Estado atual:** Questões 1, 2 e 3 documentadas; Questão 4 implementada com mocks e testes automatizados escritos, ainda sem confirmação da execução integral da suíte após os últimos ajustes. O Docker Compose já foi iniciado localmente com API, PostgreSQL, Redis e worker. O CRUD, o agente de IA e as demais questões ainda estão em desenvolvimento.

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

A estrutura atual inclui `app/core/`, `app/modules/products/`, `app/modules/stock/`, `app/modules/orders/`, `app/integrations/`, `app/workers/` e `tests/`. Os arquivos de Produtos e Estoque ainda são bases para a implementação posterior do CRUD.

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

**Limite da demonstração:** as integrações são mocks; esse endpoint não cria pedidos, reserva estoque nem efetua pagamentos. Os testes cobrem os cenários de sucesso, concorrência, timeout, retries, backoff, falha parcial, indisponibilidade total, falha permanente e erro interno. A suíte deve ser executada e seu resultado confirmado na versão atual.

Código: `app/modules/orders/`, `app/integrations/mock_services.py`, `app/integrations/retry.py` e `tests/test_order_summary.py`. Histórico das decisões: [ADR-003](docs/adr/ADR-003-concorrencia-resiliencia.md).

## Ambiente local — Docker Compose (base da Questão 7)

Pré-requisito: Docker Engine ou Docker Desktop com Docker Compose. Na raiz do projeto:

```bash
docker compose up
```

Para reconstruir a imagem após mudanças em dependências ou código:

```bash
docker compose up --build
```

O Compose inicia quatro serviços: **API FastAPI/Uvicorn**, **PostgreSQL 16**, **Redis 7** e **worker RQ** (escutando a fila `default`, ainda sem tarefas de domínio).

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

O healthcheck atual confirma somente a resposta HTTP da API, não uma conexão efetiva com PostgreSQL ou Redis. O comando `docker compose down` preserva volumes; **`docker compose down -v` apaga os volumes de dados**.

### Testes

Com Python e as dependências de `requirements.txt` instalados no ambiente local, execute na raiz:

```bash
python -m pytest -q
```

O Dockerfile atual copia `app/`, mas não a pasta `tests/`; portanto, os testes não estão incluídos na imagem da API por padrão. Não se deve interpretar a inicialização bem-sucedida dos containers como evidência de que a suíte de testes passou.

## Próximas etapas

- **Questão 6:** CRUD de Produtos e Estoque com PostgreSQL/ORM, Pydantic, JWT, paginação, filtros, cache Redis com invalidação e tarefa de domínio em worker.
- **Questão 7:** validar o conjunto completo após implementar banco, fila e eventuais migrations/seed.
- **Questões 8 e 9:** agente local para consultas em linguagem natural e explicação de uma integração futura com LLM, tool calls/MCP e controles de segurança.
- **Questões 10 e 11:** proposta conceitual em Go, portfólio e reflexão final.

A documentação distingue o que está **implementado**, o que está **conceitualmente decidido** e o que segue **pendente**.

## Documentação e uso de IA

- [ADR-001 — Arquitetura de Pedidos e Estoque](docs/adr/ADR-001-arquitetura-pedidos-estoque.md)
- [ADR-002 — Organização do FastAPI](docs/adr/ADR-002-organizacao-fastapi.md)
- [ADR-003 — Concorrência e resiliência](docs/adr/ADR-003-concorrencia-resiliencia.md)
- [Uso de IA — Registro de apoio e responsabilidades](docs/USO-DE-IA.md)

Utilizei o ChatGPT para estudo, questionamentos, alternativas de arquitetura, redação de documentos, propostas de implementação, testes e revisão. As escolhas e revisões estão registradas nos ADRs, e os resultados de testes somente serão declarados quando efetivamente verificados.
