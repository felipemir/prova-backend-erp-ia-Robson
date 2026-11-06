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
| 8–11 | Etapas posteriores | Pendentes |

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

## Próximas etapas e verificações complementares

### Implementações seguintes

- **Questão 8:** desenvolver o agente para consultas em linguagem natural sobre os dados do ERP, conforme o enunciado.
- **Questão 9:** documentar e avaliar integração futura com LLM, ferramentas/tool calls/MCP e controles de segurança.
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
- [Uso de IA — Registro de apoio e responsabilidades](docs/USO-DE-IA.md)

Utilizei o ChatGPT para estudo, questionamentos, alternativas de arquitetura, redação de documentos, propostas de implementação, testes e revisão. As escolhas e revisões estão registradas nos ADRs, e os resultados de testes somente serão declarados quando efetivamente verificados.
