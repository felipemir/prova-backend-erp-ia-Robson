# ADR-004 — Como defini a gestão de Produtos e Estoque, autenticação e inicialização do ambiente

**Status:** Aceito — implementação inicial publicada na branch `feat/products-stock-crud`. Testes de integração com Docker/PostgreSQL/Redis pendentes de confirmação.

**Escopo:** Parte 3 — Questão 6, com impactos na Questão 7 (Docker).

**Uso de Inteligência Artificial:** Utilizei o ChatGPT como apoio para discutir alternativas, avaliar regras de negócio, entender requisitos técnicos e organizar e redigir este ADR. As decisões foram construídas e revisadas durante nossas conversas. A implementação e os testes ainda não foram realizados nesta etapa.

---

## 1. Por onde comecei

Depois de trabalhar na Questão 4, analisei a Questão 6: API RESTful para gestão de Produtos e Estoque, com CRUD, validações Pydantic, PostgreSQL, JWT, filtros, paginação, cache Redis e tarefa real de domínio executada em segundo plano.

Minha preocupação foi manter a solução coerente com a arquitetura escolhida nas Questões 1 e 2, sem aumentar a complexidade desnecessariamente. Minha experiência com Magento 2, MSI, reservas e disponibilidade me levou inicialmente a considerar separar fisicamente Produtos e Estoque, mas o enunciado não exige múltiplos depósitos, reservas ou histórico de movimentações.

## 2. Quantidade diretamente na tabela products

Decidi manter **uma tabela `products` com `quantidade_em_estoque`**, preservando no código a separação entre responsabilidades de Produtos e Estoque. A separação por domínio não exige uma tabela para cada módulo.

| Campo | Tipo proposto | Regra |
| --- | --- | --- |
| `id` | Identificador do banco | Chave primária |
| `nome` | Texto | Obrigatório, não vazio e não exclusivamente numérico |
| `preco` | `NUMERIC(12,2)` / `Decimal` | Não negativo |
| `quantidade_em_estoque` | Inteiro | Não negativo |
| `data_criacao` | Data/hora com timezone | Definida na criação |
| `data_atualizacao` | Data/hora com timezone | Atualizada nas alterações |

Escolhi `Decimal` para valores monetários e restrições de não negatividade no banco para proteger a persistência além das validações Pydantic.

## 3. Mínimo de 12 unidades para cadastrar

Defini **12 unidades como o mínimo para o cadastro inicial de um produto**. Quantidades inferiores a 12 devem ser rejeitadas no `POST /products`; 12 é permitido, embora já seja classificado como estoque baixo.

Essa regra vale para a criação e **não** impede atualizações posteriores que reduzam a quantidade, inclusive a zero. É uma decisão de negócio desta demonstração, não uma exigência explícita da IPM.

## 4. Atualização administrativa de estoque

Nesta primeira implementação, a quantidade será um valor absoluto: atualizar um produto de 20 para 8 unidades significa substituir o saldo por 8. Não implementarei operações específicas de venda, entrada, saída, reserva ou liberação.

Assim, uma redução de quantidade não representa necessariamente uma venda, e não haverá histórico completo de movimentações. Uma evolução futura poderia acrescentar operações transacionais e atualizações atômicas para evitar perdas em mudanças concorrentes.

## 5. Classificação do estoque

| Quantidade | Situação |
| --- | --- |
| 13 ou mais | Disponível |
| 6 a 12 | Estoque baixo |
| 1 a 5 | Últimas unidades |
| 0 | Sem estoque |

A classificação será **calculada a partir da quantidade**, sem coluna redundante no PostgreSQL. Produtos zerados continuam cadastrados e serão apresentados como `sem_estoque`. A resposta poderá incluir `situacao_estoque` e um aviso informativo como “Últimas unidades!”.

## 6. Alertas apenas na mudança para uma faixa mais crítica

Não quero gerar alertas a cada atualização na mesma faixa. O alerta será solicitado apenas quando o produto entrar em uma faixa **mais crítica**.

| Alteração | Comportamento |
| --- | --- |
| 20 → 12 | Alerta de estoque baixo |
| 12 → 11 | Nenhum |
| 6 → 5 | Alerta de últimas unidades |
| 3 → 0 | Alerta de produto sem estoque |
| 20 → 3 | Um único alerta de últimas unidades |
| 5 → 20 | Nenhum alerta de redução |
| 20 → 12 após reposição | Novo alerta de estoque baixo |

Se uma alteração atravessar várias faixas, será gerado somente o alerta correspondente à situação final. Consultar um produto não produz alertas.

## 7. Cadastro inicial e faixa baixa

Inicialmente discutimos um alerta especial para produtos cadastrados abaixo do mínimo. Reconsiderei essa ideia: a API **não deve aceitar cadastro inicial com menos de 12 unidades**, então esse tipo de evento não é necessário no fluxo normal.

O cadastro com exatamente 12 unidades é permitido. Produtos demonstrativos com menos de 12 representarão estados posteriores ao cadastro; não devem justificar flexibilizar a regra da API pública.

## 8. Worker RQ, alertas persistidos e logs estruturados

Utilizarei **Redis + RQ**, aproveitando a infraestrutura preparada, para processar uma tarefa real do domínio quando o estoque passar a uma faixa mais crítica.

O worker receberá a tarefa, **registrará o alerta na tabela `stock_alerts` do PostgreSQL** e **emitirá um log estruturado**. Não simularei envios de e-mail, WhatsApp ou serviços externos inexistentes.

Campos mínimos propostos para `stock_alerts`:

| Campo | Finalidade |
| --- | --- |
| `id` | Identificador do alerta |
| `product_id` | Produto relacionado |
| `previous_quantity` | Quantidade anterior |
| `current_quantity` | Quantidade atual |
| `previous_status` | Faixa anterior |
| `current_status` | Faixa atual |
| `created_at` | Data da ocorrência |

Exemplo de log estruturado:

```json
{
  "event": "stock.threshold_crossed",
  "product_id": 15,
  "previous_quantity": 14,
  "current_quantity": 12,
  "previous_status": "disponivel",
  "current_status": "estoque_baixo",
  "alert_id": 42,
  "result": "success"
}
```

Uma gravação no PostgreSQL e uma publicação no Redis **não formam uma única transação atômica**. Não prometerei entrega garantida sem implementá-la. Recuperação de falhas e prevenção de duplicidades durante retries serão detalhadas na implementação, sem antecipar complexidade como Transactional Outbox.

## 9. CRUD e filtros

| Método | Endpoint | Finalidade |
| --- | --- | --- |
| `POST` | `/products` | Cadastrar |
| `GET` | `/products` | Listar |
| `GET` | `/products/{id}` | Consultar |
| `PATCH` | `/products/{id}` | Atualizar parcialmente |
| `DELETE` | `/products/{id}` | Excluir |

A listagem terá paginação e filtros opcionais por nome, preço mínimo/máximo e estoque baixo. A validação do mínimo inicial de 12 ficará restrita ao cadastro. Respostas HTTP deverão distinguir entradas inválidas, recursos inexistentes e falta de autorização.

## 10. Persistência e camadas

Manterei PostgreSQL como fonte de verdade, **SQLAlchemy 2.0** como ORM e **psycopg** como driver. A estrutura segue **Router → Service → Repository → PostgreSQL**, com schemas Pydantic.

Router recebe HTTP e aplica autenticação; Service contém regras de negócio e coordena mudanças de faixa e tarefas; Repository concentra consultas e persistência. A organização por domínio preserva o ADR-002.

## 11. Cache de leitura Redis

O endpoint inicial com cache será `GET /products/{id}`, usando **cache-aside**:

1. Consultar Redis.
2. Em cache hit, retornar o dado.
3. Em cache miss, consultar PostgreSQL e preencher Redis.
4. Após alteração confirmada, invalidar a chave correspondente.

Um TTL limitará o período de retenção. O Redis não substitui a fonte de verdade; reconheço que a invalidação não é atômica com o commit PostgreSQL e poderá existir uma janela de inconsistência. Os detalhes de ordem operacional serão resolvidos durante a implementação.

## 12. Funcionários persistidos e JWT

Preferi **funcionários persistidos no PostgreSQL** a um único usuário fixo de desenvolvimento.

Tabela `employees`:

| Campo | Finalidade |
| --- | --- |
| `id` | Identificador |
| `nome` | Nome |
| `email` | Login único |
| `password_hash` | Hash da senha |
| `role` | `admin` ou `employee` |
| `ativo` | Situação da conta |
| `data_criacao` | Data do cadastro |

Pretendo utilizar Argon2id para senhas e emitir JWTs assinados e com expiração após validar credenciais e conta ativa. Na API protegida, validarei assinatura, algoritmo permitido, expiração e identidade.

Endpoints propostos: `POST /auth/login`, `POST /employees` e `GET /employees/me`. Não criarei um sistema completo de RH.

## 13. Papéis e permissões

| Operação | Administrador | Funcionário |
| --- | --- | --- |
| Consultar/listar produtos | Permitido | Permitido |
| Cadastrar produtos | Permitido | Permitido |
| Atualizar nome/preço | Permitido | Permitido |
| Atualizar quantidade | Permitido | Permitido |
| Excluir produtos | Permitido | **Negado** |
| Cadastrar funcionários | Permitido | **Negado** |
| Consultar próprio perfil | Permitido | Permitido |

Quero demonstrar **JWT e RBAC simples**, sem uma estrutura extensa de permissões. Excluir produtos é potencialmente destrutivo e fica restrito ao administrador; uma tentativa por funcionário autenticado retorna **403 Forbidden**.

## 14. Migrations e seeds simples

Utilizarei **Alembic** para versionar o esquema e um **script de seed** para dados iniciais fictícios: um administrador, um funcionário e produtos em diferentes faixas de estoque.

O seed deverá ser **idempotente**, não duplicar dados nem sobrescrever quantidades alteradas nos testes. Produtos demonstrativos abaixo de 12 unidades deverão representar alterações posteriores a um cadastro válido, sem liberar cadastro irregular pelo endpoint público.

As credenciais de demonstração devem ser apropriadas para desenvolvimento, sem versionar segredos reais. A estratégia concreta será resolvida ao implementar.

## 15. Requisito funcional: somente docker compose up

Exijo que o avaliador prepare e inicie tudo com:

```bash
docker compose up
```

Fluxo planejado:

1. PostgreSQL e Redis sobem e passam por healthchecks.
2. Um serviço de inicialização executa `alembic upgrade head`.
3. O mesmo serviço executa o seed idempotente.
4. FastAPI e worker iniciam após a preparação bem-sucedida.

Se migration ou seed falharem, a API não deverá aparentar estar pronta. Reexecuções do Compose preservarão os dados existentes. Não serão necessários comandos manuais adicionais para a preparação.

Essa automação foi um requisito funcional definido por mim, além das exigências explícitas do enunciado.

## 16. Estratégia de testes

Pretendo testar cadastro válido/inválido (inclusive o mínimo de 12 unidades), validações de nome/preço/quantidade, CRUD, paginação, filtros, classificação do estoque, JWT, papéis, cache e invalidação, enfileiramento e processamento real pelo RQ, persistência e logs dos alertas, idempotência do seed e inicialização por Compose.

A implementação deverá incluir testes de integração com PostgreSQL e Redis reais, além de testes isolados quando úteis. Não declararei aprovação da suíte antes de executá-la e conferir os resultados.

## 17. Alternativas descartadas

- Tabela separada para estoque, reservas e movimentações completas: complexidade não exigida nesta etapa.
- Alertar em toda atualização: geraria registros repetidos.
- Permitir novos produtos abaixo de 12 unidades: contraria a regra de entrada escolhida.
- Usuário único em memória: preferi persistência e dois perfis.
- Módulo completo de RH ou permissões: fora do escopo.
- Enviar mensagens externas fictícias: preferi registro persistente e logs reais.
- Prometer entrega garantida Redis/PostgreSQL sem implementá-la: evitar.
- Exigir migrations e seeds manuais: descarto por requisito de usabilidade.

## 18. Decisões consolidadas

Manter quantidade em `products`, mínimo de 12 unidades somente na criação, atualização administrativa até zero, quatro faixas de classificação, alertas apenas na piora de faixa, worker RQ com tabela de histórico e logs, PostgreSQL/SQLAlchemy/Pydantic, cache Redis, JWT para funcionários persistidos, RBAC básico, migration Alembic e seed idempotente automáticos ao executar `docker compose up`.

## 19. Reflexão final

Procurei equilibrar simplicidade e coerência de domínio. Minha experiência com MSI me levou a considerar uma separação física do estoque, mas o enunciado não a exige. Preferi implementar o essencial com regras de negócio explícitas, autenticação persistente e processamento em segundo plano verificável.

Também considero importante facilitar a avaliação com um único comando de inicialização. Este ADR registra minhas decisões **antes de implementar**. As questões operacionais ainda em aberto — prevenção de alertas duplicados, ordem entre transação/cache/fila e credenciais demonstrativas — serão analisadas na implementação e registradas quando houver uma decisão concreta.


---

## 20. Registro da implementação inicial (05/11/2026)

A primeira versão dos módulos foi publicada na branch de desenvolvimento, **sem merge na main**. Foram criados os modelos SQLAlchemy `products`, `employees`, `stock_alerts`; a migration Alembic; o seed idempotente de dois funcionários e seis produtos; o CRUD FastAPI com filtros e paginação; JWT com senhas Argon2id e regras dos perfis; cache-aside Redis; e tarefa RQ que registra alerta no PostgreSQL e emite log estruturado.

O Compose passou a incluir um serviço `init` que aplica migrations e seed antes de iniciar API e worker, preservando o requisito de um único `docker compose up`.

**Validação efetivamente realizada:** a compilação dos arquivos Python terminou sem erro, e **14 testes de regras de estoque e Pydantic passaram**. Executei a migration e o seed duas vezes em um banco **SQLite temporário** como smoke test: foram criados 2 funcionários, 6 produtos e 1 registro de versão do Alembic, sem duplicações no segundo seed. Também validei os hashes Argon2id e a emissão/leitura de JWT para ambos os perfis nesse ambiente temporário. Esses testes não substituem PostgreSQL ou Redis reais. Não consegui executar Docker Engine, PostgreSQL ou Redis reais nesta sessão nem instalar dependências adicionais devido à indisponibilidade do índice de pacotes. Portanto, **não afirmo que os testes de integração com os serviços reais passaram**.

Foi publicado o workflow `.github/workflows/integration.yml`, configurado para execuções no push da branch e manualmente. A conexão com GitHub aceitou o arquivo, mas não confirmou uma execução ou resultado remoto. Essa checagem deve ser concluída pelo avaliador ou na revisão posterior, usando a aba Actions do repositório.

**Limitações mantidas e explicitadas:** a operação de atualização do estoque é administrativa, sem transações de movimentação; a persistência PostgreSQL e a fila Redis não são atômicas; o cache pode apresentar uma pequena janela de inconsistência; e as credenciais presentes no `.env.example` são exclusivamente demonstrações locais. A entrega permanece sujeita aos ajustes que os testes reais apontarem.
