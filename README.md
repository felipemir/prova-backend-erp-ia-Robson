# Prova prática — Back-end e IA (ERP)

Resolução da prova técnica de Back-end e Inteligência Artificial aplicada a um cenário de ERP. A implementação segue uma proposta modular em FastAPI, com decisões documentadas em Architecture Decision Records (ADRs).

## Estado atual do projeto (06/11/2026)

O projeto utiliza FastAPI modular, PostgreSQL, Redis, autenticação JWT, processamento assíncrono com RQ e Docker Compose.

| Questão | Tema | Situação |
| --- | --- | --- |
| 1 | Arquitetura de Pedidos e Estoque | Documentada — ADR-001 |
| 2 | Organização do FastAPI | Documentada — ADR-002 |
| 3 | Concorrência em Python | Documentada — ADR-003 |
| 4 | Consulta concorrente e resiliência | Implementada |
| 5 | Não consta no PDF fornecido | Sem questão correspondente |
| 6 | API de Produtos, Estoque e JWT | Implementada e validada nos principais fluxos locais |
| 7 | Docker Compose e inicialização | Implementada e validada localmente |
| 8 | Agente determinístico para consultas ao ERP | Implementada; revalidação local relatada pelo autor |
| 9 | LLM, Tool Calling e MCP | Desenho teórico concluído — ADR-006 |
| 10 | Avaliação de Go | Resposta teórica concluída — ADR-007 |
| 11 | Portfólio | Publicado e documentado — NERVA Build |

**Evidências locais:** depois de consolidar a suíte, **17 testes passaram**, segundo a execução relatada pelo autor; 4 testes de regras percorrem 14 cenários de estoque. O ambiente foi recriado com volumes novos usando apenas `docker compose up`, com migrations e seed automáticos. O GitHub Actions apresentou falhas remotas no comando de inicialização com `--wait`, apesar de a API e as dependências terem iniciado; o workflow foi corrigido em 06/11 para respeitar serviços one-shot e passou a executar na `main`. O resultado da nova execução precisa ser observado na aba Actions.

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

**CI:** `.github/workflows/integration.yml` constrói o Compose, executa novamente init/seed e a suíte. A execução antiga falhou no passo `docker compose up --wait`, que tratava inadequadamente os serviços `init`/`ready` de execução única; houve alteração no workflow em 06/11 e nova execução na `main`, cujo resultado deve ser conferido no GitHub Actions. **Limitação de histórico:** a exclusão física de produto aciona `ON DELETE CASCADE` e remove alertas associados; isso deve ser considerado para evolução/auditoria.

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

## Parte 6 — Avaliação de Go para processamento de eventos (Questão 10)

> **Status: resposta teórica/documental.** Não foi criado um serviço Go nem houve migração, benchmark ou alteração no processamento existente.

### Posicionamento e decisão

Eu aceitaria com interesse o desafio de desenvolver em Go, linguagem que tenho vontade de aprender. Entretanto, **não escolheria uma tecnologia apenas por expectativa de desempenho**. Antes de migrar um consumidor de eventos Python, instrumentaria o pipeline para analisar throughput, latências p95/p99, backlog da fila, CPU, memória, tempo em banco e chamadas externas, erros e custo de infraestrutura.

Go pode ser adequado para processamento concorrente e tarefas exigentes em CPU, mas o comportamento depende da carga real; se o gargalo estiver em I/O, no broker ou no PostgreSQL, uma reescrita pode não resolver. O volume hipotético de 100 mil eventos/minuto, sozinho, não prova que Python seja insuficiente. Eu também avaliaria otimizações da solução Python atual.

### Protótipo antes da migração

Minha proposta seria começar com um **consumidor pequeno em Go** para um tipo representativo de evento, comparando Go e Python sob as mesmas entradas, regras e recursos. Mediria throughput, latência, CPU, memória, custo e estabilidade, além de testar idempotência, duplicações, retries, falhas e integridade dos dados. Só consideraria um rollout gradual se os resultados justificassem a complexidade adicional e houvesse plano de rollback.

Um eventual ganho de desempenho não encerraria a avaliação: a equipe precisaria conseguir **manter e operar** o serviço. Consideraria o risco de concentrar conhecimento em poucas pessoas (*bus factor*), documentação, revisões, pareamento e treinamento. Se discordasse da adoção de Go, apresentaria esses argumentos com métricas e alternativas, sem transformar a discussão em preferência pessoal.

### Aprendizado e qualidade

- **Semana 1:** fundamentos de Go (`struct`, interfaces, erros, módulos, testes), aprendidos em paralelo à construção de um consumidor simples de eventos fictícios.
- **Semana 2:** goroutines, channels, contextos de cancelamento, controle de concorrência, tratamento de falhas, segurança, testes de corrida (`go test -race`), benchmarks e revisão de código.

A proposta prioriza aprender construindo, com feedback de quem conhece a linguagem e testes desde o início. A entrega real dependeria de critérios de aceitação, CI, observabilidade, consistência de eventos e capacidade de manutenção da equipe.

**Documento completo:** [ADR-007 — Avaliação de Go para processamento de eventos](docs/adr/ADR-007-adocao-go-processamento-eventos.md). Os números utilizados nos exemplos de discussão são hipotéticos, não medições efetuadas neste projeto.

## Parte 7 — Portfólio (Questão 11)

**GitHub:** [felipemir](https://github.com/felipemir).

**Projeto escolhido:** [NERVA Build — Backend](https://github.com/felipemir/NERVA-Build-vers-o-para-portf-lio) — [registro detalhado de portfólio](https://github.com/felipemir/NERVA-Build-vers-o-para-portf-lio/blob/main/PORTFOLIO.md).

### Problema que o projeto buscava resolver

O NERVA Build nasceu como MVP de uma plataforma para o segmento de materiais de construção, após investigação do mercado e validação inicial de interesse em Manaus. O objetivo do backend era sustentar um catálogo por loja, usuários e clientes, pedidos e regras de estoque, permitindo organizar operações comerciais de diferentes estabelecimentos.

A visão futura do produto incluía estimar materiais para reformas com assistência de IA e, possivelmente, utilizar câmera do celular para compreender medidas de ambientes. **Essas ideias não foram implementadas neste backend** e não devem ser confundidas com funcionalidades disponíveis no código publicado.

O projeto foi desenvolvido com participação de uma colega e do sócio da iniciativa, com decisões de produto tomadas em conjunto. Minha contribuição concentrou-se principalmente na escrita do backend, no levantamento e entendimento das regras de negócio e na transformação delas em fluxos e validações da aplicação.

### Principais decisões técnicas e por quê

- **Java 21 e Spring Boot:** escolhemos uma base consolidada para desenvolver APIs, organizar serviços e aplicar regras transacionais.
- **Controllers, Services, Repositories e DTOs:** separamos entrada HTTP, regras de negócio e persistência para facilitar evolução, testes e manutenção.
- **PostgreSQL, JPA e Flyway:** persistência relacional para lojas, produtos e pedidos; migrations versionadas para evolução do esquema.
- **Spring Security e JWT:** autenticação e separação de responsabilidades; o escopo da loja deve ser associado ao usuário autenticado, reduzindo o risco de acesso indevido entre estabelecimentos.
- **Modelagem por loja (`store_id`):** abordagem multi-tenant em banco compartilhado, adequada ao escopo inicial do MVP; exigiria testes adicionais de isolamento para operação crítica.
- **Pedidos com snapshots de itens e transições de status:** preservar informações da compra mesmo após alterações no catálogo e controlar o momento de baixa/restauração de estoque.
- **Transações e bloqueios em operações de estoque:** buscar consistência quando pedidos competem pelo mesmo saldo, embora a garantia de segurança sob concorrência deva ser confirmada com testes específicos.

### O que eu faria diferente hoje

1. **Segurança desde o início:** remover contas e senhas de demonstração das migrations, exigir segredos configurados em ambiente, revisar permissões e fortalecer testes de isolamento entre lojas.
2. **Qualidade e consistência:** ampliar testes automatizados de concorrência, cancelamento, estoque insuficiente, idempotência e demais transições críticas de pedidos.
3. **Operação e entrega:** implementar CI, observabilidade, healthchecks e empacotamento da API, com ambientes reproduzíveis e documentação mais objetiva de execução.
4. **Foco e sustentabilidade do MVP:** priorizar os fluxos comerciais comprovados antes de avançar para recursos de IA e visão computacional; definir responsabilidades de manutenção, documentação e continuidade do projeto para reduzir dependência da disponibilidade de pessoas específicas.

### Situação do projeto e limites da demonstração

O desenvolvimento original do NERVA Build foi **pausado por mudanças de localização, disponibilidade e prioridades da equipe**, não por ausência de interesse na validação inicial. Soube posteriormente que parte da base poderá ser reaproveitada em outro projeto para um cliente, mas não participo dessa implementação e não afirmo nenhum resultado dela como entrega minha.

O repositório de portfólio publica um **MVP histórico e não pronto para produção**, com limitações explicitadas em `PORTFOLIO.md`. A preparação para exposição pública envolveu revisão com apoio de IA e remoção do histórico Git original e do segredo JWT padrão. Não executei os testes Maven nem fiz deploy nessa preparação; portanto, não apresento os fluxos como validados em ambiente operacional.

## Guia de validação da API — Swagger e Postman (Questões 4, 6 e 8)

Este roteiro cobre **somente os fluxos com código executável**. As Questões 1, 2, 3, 9, 10 e 11 são respostas de arquitetura, perfil ou portfólio e não possuem endpoints próprios. A Questão 7 é validada pelo Docker Compose e pelos comandos de infraestrutura ao final. **Não existe Questão 5 no PDF fornecido**: a numeração passa da 4 diretamente para a 6.

### 0. Subir a aplicação e acessar a documentação interativa

Requisitos: Docker com Compose instalado e portas locais 8000 e 5433 disponíveis. Na raiz do repositório:

```bash
# Opcional: personalizar segredos e credenciais de demonstração
cp .env.example .env
# Ajuste .env antes de compartilhar ou implantar o ambiente.
docker compose up -d --build
docker compose ps
```

Aguarde PostgreSQL e Redis ficarem `healthy`, `init` terminar com código 0, `api` ficar `healthy` e `worker` ficar iniciado. `ready` também termina com código 0 após imprimir a mensagem de prontidão — **isso é comportamento esperado**, não uma falha.

- **Swagger UI:** http://localhost:8000/docs
- **OpenAPI JSON:** http://localhost:8000/openapi.json
- **Base URL para Postman:** `http://localhost:8000`
- **Verificação inicial:** `GET http://localhost:8000/health` → `200`, `{"status":"ok"}`.

No **Swagger**, abra a operação, clique em **Try it out**, preencha os campos e clique em **Execute**. Examine **Server response** (código e corpo efetivos), não somente *Example Value* (modelo ilustrativo).

No **Postman**, crie um Environment com a variável `base_url=http://localhost:8000`. Use `{{base_url}}` no início de cada URL, abra a aba **Body → raw → JSON** para requisições JSON e configure o cabeçalho `Content-Type: application/json`. Nos endpoints protegidos, use **Authorization → Bearer Token** e cole o token obtido no passo 1. Para `/auth/login`, a requisição é **x-www-form-urlencoded**, não JSON.

**Atenção:** logins e produtos iniciais são fictícios; credenciais e segredos padrão servem somente para desenvolvimento local. A seed é idempotente: em volumes já usados, os dados podem ter mudado.

### 1. Autenticação JWT — Questão 6

**Swagger:** abra `POST /auth/login` → **Try it out**; no formulário, preencha `username=employee@example.test` e `password=LocalEmployee123!` e execute. Copie `access_token` da resposta HTTP `200`. Clique no botão **Authorize** no topo do Swagger e autentique-se usando as mesmas credenciais no fluxo OAuth2 (ou, se a interface pedir um token Bearer, informe o token obtido). Após autorizar, um cadeado indica as operações protegidas.

**Postman:** `POST {{base_url}}/auth/login` → **Body → x-www-form-urlencoded**:

| Key | Value |
| --- | --- |
| `username` | `employee@example.test` |
| `password` | `LocalEmployee123!` |

Resultado esperado: `200`, JSON com `access_token` e `token_type: "bearer"`. Salve o token na variável de ambiente `token` ou cole em **Authorization → Bearer Token** (sem digitar `Bearer` duas vezes). Para testar como administrador, repita com `admin@example.test` / `LocalAdmin123!` e guarde outro token, `admin_token`.

**Testes rápidos:** `GET /employees/me` com token válido → `200` e perfil do funcionário; `GET /products` sem token → `401`; `POST /auth/login` com senha errada → `401`. Com token de funcionário, `POST /employees` → `403`. Admin pode cadastrar usuário com:

```json
{
  "nome": "Avaliador Exemplo",
  "email": "avaliador.unico@example.test",
  "senha": "SenhaDemoSegura123!",
  "role": "employee"
}
```

Envie a `POST /employees` com **token de administrador** → `201`; repita com o mesmo e-mail → `409`. O exemplo cria um usuário real na base local de teste.

### 2. CRUD, validações, filtros e paginação — Questão 6

Autentique-se como funcionário (ou admin), usando o token nas requisições protegidas.

**2.1 Cadastrar produto:** `POST /products`, JSON:

```json
{
  "nome": "Produto de avaliação API",
  "preco": "399.90",
  "quantidade_em_estoque": 20
}
```

Esperado: HTTP `201`, incluindo `id`, `nome`, `preco`, `quantidade_em_estoque` e `situacao_estoque: "disponivel"`. **Copie o `id` retornado**; os exemplos abaixo usam `{id}` como marcador a substituir por esse valor. Se já executou o roteiro antes, crie outro nome se desejar identificar facilmente os novos registros.

**2.2 Consultar:** `GET /products/{id}` → `200` com o produto. Repita para testar a leitura cacheada. `GET /products` retorna `items`, `page`, `page_size` e `total`.

**2.3 Filtrar e paginar:** exemplos para copiar no Postman (query params também podem ser preenchidos no Swagger):

```http
GET /products?page=1&page_size=2
GET /products?page=2&page_size=2
GET /products?nome=Produto%20de%20avalia%C3%A7%C3%A3o
GET /products?preco_min=150&preco_max=500
GET /products?estoque_baixo=true
```

Esperado: `200`; página com no máximo dois itens quando `page_size=2`; `total` representa os resultados filtrados; `estoque_baixo=true` inclui os produtos com estoque entre 0 e 12 (conforme regra desta implementação). `preco_min=500&preco_max=100` → `422` por intervalo inválido.

**2.4 Atualizar:** `PATCH /products/{id}`, JSON:

```json
{"quantidade_em_estoque": 5}
```

Esperado: `200`, quantidade `5` e `situacao_estoque: "ultimas_unidades"`. A quantidade pode ser atualizada para zero; a restrição de mínimo de 12 vale **somente para o cadastro inicial**.

**2.5 Validar erros:** faça novo `POST /products` com `quantidade_em_estoque: 11` → `422`. Outros exemplos de rejeição: `nome: "12345"`, `preco: "-1"`, ou tentar atualizar preço para valor negativo. JSON incompleto também retorna `422`.

**2.6 Permissões de exclusão:** `DELETE /products/{id}` com **token de funcionário** → `403`. Com **token de administrador** → `204` sem corpo. Um `GET /products/{id}` posterior → `404`. Faça a exclusão **por último**, para não impedir os testes de cache, estoque e agente. A exclusão de produto **apaga os alertas históricos vinculados** por `ON DELETE CASCADE`, limitação conhecida registrada no ADR-004.

### 3. Cache Redis e worker RQ — Questão 6 (efeitos observáveis)

**Cache:** usando um produto existente, execute `GET /products/{id}` e depois `PATCH /products/{id}` para alterar preço ou estoque. Um novo `GET` deve retornar os valores atualizados. A API usa cache-aside apenas no detalhe `GET /products/{id}` e invalida a chave na alteração. Para **confirmar a chave no Redis**, abra outro terminal:

```bash
docker compose exec redis redis-cli GET erp:products:SEU_ID
```

Substitua `SEU_ID` pelo ID, sem chaves. Faça a leitura logo após o `GET`: o TTL padrão é 60 segundos. Após `PATCH`, verifique novamente; a chave normalmente estará ausente. A ausência isolada depois de muito tempo **não comprova invalidação**, pois o TTL também pode ter expirado.

**Fila e alerta persistido:** para testar, crie produto com estoque inicial `20`; altere-o por `PATCH /products/{id}` para `5`. O Service salva a alteração e enfileira uma tarefa RQ porque houve piora da faixa de estoque. Aguarde alguns segundos, então chame:

```http
GET /stock/alerts?limit=20
```

Com Bearer token, espere `200` e procure um registro com `product_id` igual ao ID criado, `previous_quantity: 20`, `current_quantity: 5`, `previous_status: "disponivel"` e `current_status: "ultimas_unidades"`. **A resposta do PATCH não é a confirmação de que a tarefa terminou**: a API e o worker executam separadamente. Se não aparecer, aguarde e consulte de novo; verifique `docker compose logs worker --tail=100`. Uma atualização dentro da mesma faixa não deve criar outro alerta.

A tarefa persiste o evento na tabela `stock_alerts`, além de registrar log. A gravação em PostgreSQL e publicação no Redis **não são atômicas**; falha no enqueue pode deixar uma atualização de estoque sem alerta, limitação registrada na documentação.

### 4. Endpoint assíncrono de integrações simuladas — Questão 4

**Sem JWT:** `GET /orders/12345/summary` no Swagger ou Postman. Use qualquer identificador textual no lugar de `12345`: o código **não busca um pedido real**; envia o identificador aos mocks.

Esperado no cenário padrão: HTTP `200`, `order_id: "12345"`, `status: "complete"`, entradas `cliente`, `estoque` e `financeiro` em `data`, três `services` com `"success"` e `warnings: []`. As chamadas são concorrentes via `asyncio.gather`. O código tem timeout individual e retry para falhas transitórias, com degradação parcial (`200` / `partial`) ou indisponibilidade total (`503` / `unavailable`).

**Limite do teste manual:** o cenário padrão de `GET` não oferece parâmetros para induzir timeout ou falhas dos mocks. Portanto, **não se consegue demonstrar os cenários `partial`, `503` e retries somente alterando a URL no Postman/Swagger**. Esses casos são verificados com mocks substituídos nos testes automatizados em `tests/test_order_summary.py`. Não há integração real com Financeiro ou Clientes.

### 5. Agente determinístico de consultas ao ERP — Questão 8

Requer JWT do passo 1. No Swagger abra **POST /agent/query → Try it out**; no Postman use **POST {{base_url}}/agent/query**, **Authorization → Bearer Token**, **Body → raw → JSON**.

Experimente:

```json
{"pergunta":"Quais produtos estão com estoque abaixo de 10 unidades?"}
```

Esperado: `200`; `filtros` com campo `quantidade_em_estoque`, operador `<`, valor `10`; `situacao` `encontrado` ou `sem_resultados` conforme os dados; `total`, `produtos` (até 50) e `limite: 50`. Na seed inicial intacta, normalmente há 3 correspondências (Mouse, Headset, Webcam).

Experimente também:

```json
{"pergunta":"Quero produtos com preço acima de 200 reais"}
```

Na seed inicial intacta, normalmente há 4 registros. Para consulta válida **sem resultado**, teste `{"pergunta":"Preço abaixo de 100"}` — espere `200`, `situacao: "sem_resultados"`, `total: 0` e `produtos: []`, desde que a base não tenha produtos novos abaixo desse preço. Para entrada fora do escopo, `{"pergunta":"Qual produto é o mais caro?"}` → `422` (ranking não suportado). Duas condições unidas por `e`, como estoque abaixo de 5 e preço acima de 100, também retornam `422`. Sem token → `401`.

**Esta versão não usa LLM remoto:** interpreta uma única condição numérica explícita de estoque ou preço, consulta PostgreSQL pelo Repository e devolve JSON estruturado.

### 6. Testes automatizados e verificação do Docker — Questões 4, 6, 7 e 8

Após `docker compose up -d --build`, execute:

```bash
# Toda a suíte, incluindo a integração com banco/Redis/worker:
docker compose run --rm --no-deps -v "$PWD/tests:/srv/app/tests:ro" api python -m pytest -q -p no:cacheprovider

# Somente os testes do agente (usam SQLite e overrides de dependências):
docker compose run --rm --no-deps -v "$PWD/tests:/srv/app/tests:ro" api python -m pytest -q -p no:cacheprovider tests/test_agent.py

# Infraestrutura e logs úteis:
docker compose ps
docker compose logs --tail=100 api worker init
docker compose down
```

Os testes de integração com `PostgreSQL`, `Redis` e `RQ` exigem os serviços ativos. O Dockerfile não embute a pasta `tests/`; a montagem no comando é intencional. Não confunda resultados relatados de execuções locais anteriores com uma execução atual da CI.

### 7. AWS, frontend e escopo não implementado

O **PDF lista AWS na stack esperada**, mas não solicita provisionar recursos AWS nem fazer um deploy na nuvem em uma questão específica. Não há serviço AWS configurado neste repositório. Para evoluir o projeto, eu consideraria imagens Docker em ECR, API e worker em ECS/Fargate, PostgreSQL em RDS, Redis em ElastiCache, secrets no Secrets Manager e logs/métricas no CloudWatch, avaliando custos, IAM e networking. **São propostas futuras, não entregas realizadas.**

O enunciado apresenta `React/Vite (front, se aplicável)`. **Não exige construir um frontend para as questões práticas**, que focam a API. Optei por concentrar o tempo disponível em regras de negócio, testes, infraestrutura e documentação. O Swagger UI já permite testar toda a API implementada; um painel React/Vite poderia ser acrescentado depois, mas **não existe neste repositório**.

O PDF pula da **Questão 4 diretamente para a Questão 6**. Não existe uma Questão 5 para implementar no documento recebido; portanto, não há pendência de código a respeito dela.

## Status final e verificações complementares

As **Questões 1, 2, 3, 9, 10 e 11** foram respondidas teoricamente ou por portfólio. As **Questões 4, 6 e 8** possuem endpoints executáveis documentados no guia acima. A **Questão 7** entrega Dockerfile, Compose, healthchecks, migrations e seed automáticos. **Questão 5 não consta no PDF.**

### Verificações feitas e limitações conscientes

- **CI remota:** as execuções antigas do GitHub Actions falharam durante o comando `docker compose up -d --build --wait`. O log mostrava API, PostgreSQL e Redis saudáveis, além de `ready` encerrado com código 0. Ajustei o workflow para inicializar em modo detached e verificar a prontidão com `docker compose run --rm ready`, e incluí disparo por push na `main`. A nova execução deve ser observada em [Actions](https://github.com/felipemir/prova-backend-erp-ia-Robson/actions); não declaro sucesso sem conferir a conclusão.
- **Alertas e exclusão:** `ON DELETE CASCADE` apaga os alertas associados ao produto excluído. A API atual funciona conforme essa regra, porém **perder histórico de auditoria é uma limitação real**. Migrar para exclusão lógica e/ou preservar snapshots seria evolução futura; não altero o domínio antes da entrega sem migration e testes adequados.
- **Limite entre transação e fila:** persistir o estoque e enfileirar alerta no Redis não é uma operação atômica. Uma Transactional Outbox é proposta futura, não implementada.
- **AWS e frontend:** são melhorias opcionais para este enunciado; o frontend não é exigido (texto: `front, se aplicável`) e não existe deploy AWS neste projeto.
- **Testes locais:** resultados registrados previamente no README/ADRs foram relatados pelo autor. O guia acima permite ao avaliador reproduzir os cenários e executar a suíte; não afirmo uma nova execução local nesta revisão.

As limitações da gestão de produtos e estoque estão detalhadas no [ADR-004](docs/adr/ADR-004-produtos-estoque-autenticacao-inicializacao.md), sem confundir funcionalidade implementada com melhoria planejada.

## Uso de IA

- [ADR-001 — Arquitetura de Pedidos e Estoque](docs/adr/ADR-001-arquitetura-pedidos-estoque.md)
- [ADR-002 — Organização do FastAPI](docs/adr/ADR-002-organizacao-fastapi.md)
- [ADR-003 — Concorrência e resiliência](docs/adr/ADR-003-concorrencia-resiliencia.md)
- [ADR-004 — Produtos, Estoque, JWT e inicialização](docs/adr/ADR-004-produtos-estoque-autenticacao-inicializacao.md)
- [ADR-005 — Agente determinístico de consultas ao ERP](docs/adr/ADR-005-agente-deterministico-consultas-erp.md)
- [ADR-006 — Evolução para LLM, Tool Calling e MCP (Questão 9)](docs/adr/ADR-006-llm-mcp-guardrails-observabilidade.md)
- [ADR-007 — Avaliação de Go para processamento de eventos (Questão 10)](docs/adr/ADR-007-adocao-go-processamento-eventos.md)
- [Uso de IA — Registro de apoio e responsabilidades](docs/USO-DE-IA.md)

Utilizei o ChatGPT para estudo, questionamentos, alternativas de arquitetura, redação de documentos, propostas de implementação, testes e revisão. As escolhas e revisões estão registradas nos ADRs, e os resultados de testes somente serão declarados quando efetivamente verificados.
