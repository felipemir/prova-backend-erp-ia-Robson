# Uso de Inteligência Artificial — Registro de apoio

## Ferramenta e objetivo

Utilizei o ChatGPT para apoiar o estudo, a discussão de alternativas, a organização do projeto, a redação da documentação, a elaboração inicial de código e testes e as revisões técnicas. A prova permite apoio de IA, mas procurei manter explícitas as escolhas, as dúvidas que tive e os limites entre uma proposta e algo de fato implementado e validado.

## Questões 1 e 2 — Arquitetura e organização

Conversei com a IA sobre a separação entre Pedidos, Estoque, Clientes e Financeiro; comunicação REST e eventos; transações, consistência, Redis, idempotência, observabilidade e escalabilidade.

Trouxe minha experiência com Magento 2 e reservas de estoque como referência para avaliar as alternativas. Questionei a necessidade de novos microsserviços sem dados de escala e preferi começar por um monólito modular, com possibilidade de evolução. Discutimos também o uso de arquitetura em camadas no FastAPI, em comparação com padrões conhecidos do Java/Spring. Inicialmente considerei consultas diretamente no Service, mas preferi separar o acesso ao banco em Repository quando houver persistência.

A IA ajudou a comparar as opções e a organizar e redigir o README e os ADRs 001 e 002 a partir das discussões. As propostas conceituais não devem ser interpretadas como componentes já implementados.

## Questão 3 — Concorrência em Python

Utilizei a IA para comparar `asyncio`, `threading` e `multiprocessing`, distinguindo I/O assíncrono, bibliotecas bloqueantes e processamento intensivo de CPU. Discutimos também a diferença entre concorrência durante uma requisição e tarefas delegadas a uma fila Redis/worker.

Esses pontos foram registrados no ADR-003, com situações de ERP e justificativas.

## Questão 4 — Implementação e revisão

O ChatGPT colaborou na proposta inicial de organização dos arquivos, do endpoint `GET /orders/{order_id}/summary`, dos mocks de Clientes/Estoque/Financeiro, do uso de `asyncio.gather()`, da política de timeout e retries e dos testes automatizados.

Durante a discussão, preferi **três tentativas totais**, com **backoff progressivo**, em vez de retries imediatos. Também considerei um fluxo transacional de aprovação de pedidos, mas escolhi uma consulta informativa para manter o escopo próximo ao enunciado.

Depois da primeira implementação, revisei o comportamento e identifiquei, com apoio da análise, pontos que exigiam ajustes:

- O resumo totalmente indisponível passou a retornar HTTP `503` e `status: "unavailable"`, em vez de apresentar uma falha total como resposta parcial bem-sucedida.
- As falhas esperadas passaram a usar exceções próprias de integração; erros de programação inesperados não devem ser disfarçados como indisponibilidade externa.
- Foi adicionado um teste específico para os intervalos de backoff, além dos testes de quantidade de tentativas.
- As variáveis de timeout, tentativas e backoff, lidas pela aplicação, passaram a ser encaminhadas pelo Docker Compose ao container da API.

O ADR-003 detalha a sequência dessas decisões, o que considerei e o que alterei. A existência dos testes no repositório **não equivale à confirmação de que todos passaram após os últimos ajustes**.

## Preparação do ambiente Docker

Usei o ChatGPT para criar e revisar o Dockerfile e o Compose, incluindo FastAPI, PostgreSQL, Redis e worker RQ. Optei por antecipar a conteinerização para não deixar essa etapa para o final. Também recebi apoio para examinar logs, healthchecks e informações de consumo de recursos após rodar o ambiente localmente.

Os containers foram inicializados no meu ambiente e a API respondeu ao endpoint de saúde. Isso não comprova, por si só, as integrações de banco, cache, execução de tarefas e testes automatizados, que ainda precisam ser validados quando implementados.

## Decisões, responsabilidades e limites

Utilizei o apoio da IA para acelerar o trabalho dentro do prazo, mas questionei alternativas e procurei manter o projeto simples e evolutivo. Não tratei sugestões como decisões obrigatórias.

O código e os documentos incluem contribuições geradas ou redigidas com assistência do ChatGPT. Não atribuo à IA testes, pesquisas ou execuções que não tenham sido realizados ou verificados. Continuo responsável por entender, revisar, validar e apresentar a solução.

Este registro deverá ser atualizado à medida que novas partes práticas forem implementadas.


## Questão 6 — Implementação assistida por IA

Após aprovar o ADR-004, autorizei o ChatGPT a iniciar a implementação da API de Produtos e Estoque e preparar uma pipeline no GitHub, mantendo o trabalho na branch `feat/products-stock-crud`. O ChatGPT produziu a primeira versão dos modelos, migrations Alembic, script de seed, endpoints CRUD, autenticação JWT e RBAC, cache Redis, integração com fila RQ, testes e workflow GitHub Actions. Minha participação anterior foi definir os requisitos e as regras de negócio detalhadas no ADR-004.

Os limites são relevantes: compilei os arquivos localmente com auxílio da ferramenta, executei 14 testes isolados de regras de estoque e Pydantic, fiz um smoke test de migration/seed usando SQLite temporário e verifiquei hashing Argon2id e emissão/leitura de JWT para os dois perfis. A instalação de dependências adicionais não foi possível por indisponibilidade de rede no ambiente de testes. Não foi possível realizar nesta sessão testes reais com Docker Engine, PostgreSQL e Redis.

O workflow `.github/workflows/integration.yml` foi adicionado à branch com gatilho em push, mas não recebi confirmação de conclusão da execução. O resultado da integração precisa ser verificado posteriormente na aba Actions. Não devo apresentar a simples publicação do workflow como evidência de testes aprovados.

O código entregue está sujeito à revisão, correção e validação final. A responsabilidade de entender e apresentar as decisões permanece comigo, inclusive nos pontos em que a IA produziu trechos de implementação.
