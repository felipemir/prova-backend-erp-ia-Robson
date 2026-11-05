# Prova prática — Back-end e IA (ERP)

Resolução da prova técnica de Back-end e Inteligência Artificial voltada a um cenário de ERP.

> **Estado do projeto:** a Parte 1 (Questões 1 e 2) estabelece a base arquitetural. As partes práticas ainda serão implementadas e as decisões poderão ser atualizadas com as descobertas durante o desenvolvimento.

## Parte 1 — Arquitetura e organização

### Questão 1 — Arquitetura de Pedidos e Estoque

**Proposta:** uma aplicação modular em FastAPI para os domínios de Pedidos e Estoque, integrada aos microsserviços existentes de Clientes e Financeiro. Como o enunciado não especifica volume de usuários, requisições por segundo ou metas quantitativas de disponibilidade, preferi uma solução evolutiva em vez de introduzir complexidade distribuída sem evidências de necessidade.

A decisão considera minha experiência com Magento 2 e MSI, principalmente quantidades vendáveis, reservas e operações concorrentes.

| Componente | Responsabilidade |
| --- | --- |
| Pedidos | Criar e acompanhar pedidos, administrar estados e cancelamentos e coordenar integrações comerciais |
| Estoque | Controlar quantidades, disponibilidade, reservas, liberações e movimentações |
| Clientes (existente) | Manter dados cadastrais e fornecer informações para validações |
| Financeiro (existente) | Processar operações financeiras e disponibilizar seus resultados |
| API Gateway | Encaminhar requisições externas e aplicar políticas gerais de entrada |

**Comunicação:** REST para consultas que exigem resposta imediata, como validações de cadastro; mensageria para eventos e tarefas desacopladas. O Financeiro pode publicar `PagamentoAprovado` como mecanismo principal, com reconciliação direcionada via REST para situações pendentes. Eventos críticos precisam de idempotência, recuperação e entrega confiável; Transactional Outbox é uma alternativa para publicação consistente.

**Persistência:** PostgreSQL é a fonte de verdade das operações críticas. Reservas devem utilizar transações e controle de concorrência. Redis apoia cache e execução de tarefas por workers, mas não substitui a consistência do PostgreSQL. O cache terá invalidação ou atualização explícita e, quando adequado, fallback para consultas ao banco. Não introduziria locks distribuídos inicialmente sem uma necessidade identificada.

**Gateway e observabilidade:** Kong é uma alternativa para roteamento, autenticação geral e rate limiting; regras específicas de autorização continuam nos serviços. Prometheus e Grafana apoiariam métricas e alertas, complementados por logs estruturados e tracing distribuído (por exemplo, via OpenTelemetry). Monitoraria latência, erros, integrações, filas e inconsistências entre pedidos e pagamentos.

**Escalabilidade e limites:** como Pedidos e Estoque compartilham implantação e recursos, primeiro investigaria consultas, índices, concorrência e processamento se houver aumento de carga. Uma separação em serviços independentes seria reavaliada diante de requisitos concretos de escala, disponibilidade ou implantação independente.

Essa é uma **proposta conceitual**: não significa que Kong, um broker externo ou toda a infraestrutura de observabilidade já tenham sido implementados.

Registro das alternativas e decisões: [ADR-001](docs/adr/ADR-001-arquitetura-pedidos-estoque.md).

### Questão 2 — Organização do FastAPI

Escolhi uma **arquitetura em camadas inspirada no MVC do Java/Spring, adaptada ao FastAPI**. O framework não impõe MVC; aproveitarei recursos como `APIRouter`, `Depends` e Pydantic, com camadas Service e Repository para separar responsabilidades.

Estrutura inicial planejada:

```text
app/
├── main.py
├── core/
│   ├── config.py
│   ├── database.py
│   └── security.py
├── modules/
│   ├── products/
│   │   ├── router.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   ├── models.py
│   │   └── schemas.py
│   └── stock/
│       ├── router.py
│       ├── service.py
│       ├── repository.py
│       ├── models.py
│       └── schemas.py
├── integrations/
├── workers/
└── tests/
```

| Componente | Responsabilidade |
| --- | --- |
| Router | Endpoints, parâmetros HTTP e encaminhamento das operações |
| Schema (Pydantic) | Validação e contratos de entrada e saída |
| Service | Regras de negócio e coordenação |
| Repository | Consultas e persistência |
| Model (ORM) | Representação das entidades persistidas |
| Core | Configurações, segurança e recursos compartilhados |

Organizo as camadas **por domínio**, mantendo perto os arquivos relacionados a Produtos e Estoque. Isso preserva a linha de raciocínio da Questão 1. Quero aproveitar princípios de SOLID, Clean Architecture e DDD leve sem afirmar que implementarei esses padrões integralmente ou criar abstrações sem utilidade. Por exemplo, o módulo de Estoque detecta estoque baixo, mas delega a notificação a outro componente.

A estrutura acima é uma **base estabelecida para a implementação**, não uma lista de arquivos já criados. Poderá evoluir conforme as necessidades reais.

Registro do raciocínio: [ADR-002](docs/adr/ADR-002-organizacao-fastapi.md).

## Documentação e uso de IA

- [ADR-001 — Como fui pensando na arquitetura de Pedidos e Estoque](docs/adr/ADR-001-arquitetura-pedidos-estoque.md)
- [ADR-002 — Como escolhi organizar o projeto FastAPI](docs/adr/ADR-002-organizacao-fastapi.md)
- [Uso de IA — Transparência e responsabilidades](docs/USO-DE-IA.md)

Utilizei o ChatGPT para questionamentos, estudo, exploração de alternativas e apoio à escrita dos documentos. Minhas decisões e mudanças de direção estão registradas nos ADRs. As próximas etapas de implementação e testes serão documentadas conforme forem realizadas.

## Ambiente local com Docker Compose

Pré-requisito: Docker Engine/Desktop com o plugin Compose. Na raiz do projeto:

```bash
docker compose up
```

O Compose construirá a imagem na primeira execução e iniciará FastAPI, PostgreSQL, Redis e o worker RQ. Para reconstruir depois de alterar dependências: `docker compose up --build`.

- Swagger: http://localhost:8000/docs
- Saúde da API: http://localhost:8000/health
- PostgreSQL: localhost:5433 (alterável por `POSTGRES_PORT`)
- Redis: acessível somente entre containers

Os valores padrão são apenas para **desenvolvimento local** e permitem subir sem configurar nada antes. Para personalizar, copie `.env.example` para `.env`, ajuste as variáveis e não versione esse arquivo. Não utilize as credenciais de exemplo fora do ambiente local. Uma senha alterada após a inicialização do volume do PostgreSQL não atualiza automaticamente as credenciais já criadas.

Use `docker compose ps` para verificar os containers e `docker compose down` para desligar. Os dados ficam em volumes Docker; `docker compose down -v` **remove os volumes e seus dados**.

O worker já escuta a fila `default`, mas tarefas do domínio, migrações e seed serão implementadas nas etapas seguintes. O healthcheck da API valida apenas a resposta HTTP, não a conectividade com banco e Redis. O ambiente está preparado para a implementação; o CRUD ainda não está implementado.
