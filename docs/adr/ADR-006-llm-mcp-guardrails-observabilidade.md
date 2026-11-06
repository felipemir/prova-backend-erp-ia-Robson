# ADR-006 — Evolução plugável para LLM, Tool Calling e MCP (Questão 9)

**Status:** Proposta arquitetural aprovada para documentação (não implementada).

**Questão:** 9, Parte 5 — desafio teórico/design da prova de back-end.

**Relacionamento:** evolui o agente determinístico da [Questão 8 / ADR-005](ADR-005-agente-deterministico-consultas-erp.md) e respeita a separação de serviços discutida na Parte 1.

**Como cheguei às decisões:** discuti as alternativas com apoio do ChatGPT, questionando autonomia do agente, segurança, exposição de dados financeiros, servidor MCP central versus múltiplos servidores, uso de cache antigo, custos por token e observabilidade. Priorizei uma arquitetura consultiva, simples para três domínios e evolutiva. O documento registra uma **proposta**, não funcionalidades existentes nem resultados de testes.

## 1. Contexto e objetivo

Na Questão 8, implementei uma API FastAPI com interpretador determinístico local que reconhece um filtro simples de preço ou estoque e devolve JSON após consultar o PostgreSQL por meio de Service/Repository. A Questão 9 pede explicar como seria possível conectar futuramente um LLM real, sem depender de um provedor específico, incluindo tool/function calling, MCP, guardrails e custo/latência/observabilidade.

A escolha é **não substituir as regras de domínio pelo modelo**. A IA interpreta a pergunta e propõe uma operação de leitura. O backend valida o contrato, autoriza e executa a consulta, mantendo o controle sobre dados e efeitos.

## 2. Decisão: arquitetura híbrida e plugável

O fluxo proposto é:

```text
Funcionário autenticado (JWT) → API / Orquestrador de consultas
                                |
                                +→ Interpretador determinístico (Q8)
                                |    └→ quando entender completamente e com segurança:
                                |       Service → Repository → PostgreSQL → JSON
                                |
                                └→ quando não entender / consulta mais elaborada:
                                     Adaptador de LLM (interface plugável)
                                       └→ propõe nome de ferramenta + argumentos estruturados
                                            → validador de schema + autorização do usuário
                                            → cliente MCP / dispatcher autorizado
                                            → Servidor MCP central (somente leitura)
                                            → APIs/Services de Produtos, Pedidos, Financeiro
                                            → respostas estruturadas e fundamentadas
                                            → apresentação ao funcionário
```

Não basta encontrar uma palavra conhecida: o interpretador local só responde se reconhecer **a condição inteira**. Perguntas ambíguas geram pedido de esclarecimento ou falha controlada, nunca uma consulta parcial disfarçada de correta.

Uma interface de interpretação independente do provedor (ex.: `interpretar(pergunta, contexto_autorizado) -> PropostaDeFerramenta`) permitiria plugar diferentes modelos ou um modelo hospedado internamente sem reescrever o Service, os contratos e a autorização. O modelo devolve **propostas**, não privilégios de execução. A integração com o LLM e o MCP central é futura; na versão atual da Questão 8 existem apenas regras locais e chamadas diretas ao Service.

## 3. Tool/function calling e contratos de ferramentas

Cada ferramenta tem nome, finalidade, parâmetros tipados e formato de saída definido. A lista é fechada; nenhum `execute_sql`, `update`, `delete`, `create` ou executor genérico será exposto ao agente. Mesmo administradores não ganham acesso de escrita via IA.

Exemplo **ilustrativo de schema JSON**, não implementado:

```json
{
  "name": "consultar_estoque",
  "description": "Consulta o saldo de um produto autorizado no ERP",
  "inputSchema": {
    "type": "object",
    "properties": {
      "produto_id": { "type": "integer", "minimum": 1 }
    },
    "required": ["produto_id"],
    "additionalProperties": false
  }
}
```

Exemplo de proposta do modelo:

```json
{
  "ferramenta": "consultar_estoque",
  "argumentos": { "produto_id": 42 }
}
```

Outras ferramentas propostas, todas somente de leitura:

| Ferramenta | Entradas principais | Resultado | Restrições |
| --- | --- | --- | --- |
| `consultar_produtos` | campo permitido, operador, valor, limite | lista/total | filtro e paginação validados, sem SQL livre |
| `consultar_estoque` | `produto_id` | quantidade, origem e data de atualização | acesso autorizado; dado atual ou marcado como último saldo conhecido |
| `consultar_pedido` | `pedido_id` | resumo autorizado do pedido | não expor informações de outro cliente/setor indevidamente |
| `consultar_valor_pedido` | `pedido_id` | total registrado, moeda e estado | apenas para perfis autorizados e pedidos permitidos |
| `consultar_documentacao` | assunto/termo | procedimento e fonte | documentação aprovada; não criar procedimentos fictícios |

O schema aceita apenas argumentos previstos, com limites de tamanho e validação Pydantic. O backend utiliza o contexto do JWT autenticado para autorização e auditoria; **não confia em um campo de `role` ou `employee_id` que o LLM forneça**. Os Services e microsserviços fazem a verificação definitiva antes de acessar os registros. Os totais e quantidades apresentados ao funcionário devem refletir os valores devolvidos pelas ferramentas; o LLM não deve inventar números.

O enunciado menciona `criar_pedido` como exemplo de ferramenta possível. **Escolhi não disponibilizar essa ferramenta** porque nosso escopo estabelece uma IA exclusivamente consultiva.

## 4. MCP: servidor central para três domínios

Escolhi **um servidor MCP central** como ponto de exposição das ferramentas dos domínios Produtos, Pedidos e Financeiro. É suficiente para o porte inicial, facilita manutenção e padroniza contratos, autenticação, políticas e observabilidade. A experiência prática do autor com MCP em ferramentas de trabalho motivou a avaliação dessa alternativa.

O servidor MCP funciona como **adaptador de ferramentas**, não como banco, ORM ou local de regras de negócio. Seu trabalho é publicar ferramentas de leitura, receber chamadas do cliente MCP, validar e encaminhar requisições às APIs/Services existentes. Os microsserviços continuam donos dos dados e das decisões de negócio. A aplicação que orquestra o agente é cliente MCP; o LLM não recebe conexão direta ao PostgreSQL nem credenciais dos serviços.

**Cuidados:** um servidor central pode se tornar ponto único de falha e gargalo. Planejaria instâncias replicadas, timeouts, limites por usuário/ferramenta, circuit breaker, healthchecks e isolamento do acesso à rede interna. Se a carga ou as equipes justificarem, as ferramentas poderão ser separadas por domínio posteriormente. Não criaria três servidores MCP sem demanda real.

## 5. Guardrails, permissões e privacidade

### 5.1. Agente consultivo como restrição arquitetural

A IA não executa ações de criação, atualização ou exclusão, independentemente de o usuário ser administrador. **Não basta pedir ao LLM que não execute**: as ferramentas de escrita não existem no catálogo nem no dispatcher, e os serviços de execução do agente recebem credenciais com permissões somente de leitura. Não disponibilizaria SQL livre, shell ou acesso direto ao banco.

Se o usuário escrever `Quero excluir todos os pedidos cancelados`, o agente **não executa**. Pode esclarecer que não tem permissão para excluir e, se houver documentação autorizada, oferecer instruções fundamentadas sobre o procedimento — sem presumir que o funcionário perguntou apenas "como fazer".

### 5.2. RBAC e dados financeiros de alcance limitado

Leitura não significa acesso irrestrito. Haverá controle baseado em perfil/escopo do funcionário no catálogo de ferramentas, seguido de verificação obrigatória no backend e em cada serviço. Ocultar uma ferramenta na interface **não substitui a autorização na execução**. A autorização a um pedido específico deve considerar suas relações e limites de acesso, e não só o cargo.

Consultas financeiras profundas e agregações sensíveis (faturamento global, margens, contas bancárias, informações financeiras confidenciais) **não entram no escopo inicial**. Consultas pontuais como total e status de pagamento de um pedido podem ser permitidas somente aos usuários autorizados para aquele pedido; respostas precisam ser mínimas, sem campos sensíveis desnecessários. Habilitar análises financeiras mais amplas exigiria nova avaliação de segurança, privacidade, autorização, auditoria e aprovação da empresa.

### 5.3. Alucinação, ambiguidade e dados não confiáveis

- Resultados de ferramentas e documentos não são instruções privilegiadas; bloquear tentativas de *prompt injection* neles.
- Validar schema e permissões antes da chamada, limitar número de chamadas e solicitar esclarecimento quando a intenção for ambígua.
- Se a ferramenta retornar `nao_encontrado`, `acesso_negado` ou `indisponivel`, não transformar o erro em um resultado inventado.
- Valores financeiros ou de estoque devem vir diretamente do retorno autorizado do ERP, com identificação de origem e instante quando aplicável.
- Instruções operacionais devem ser fundamentadas em documentação aprovada; sem fonte confiável, declarar a impossibilidade de confirmar o procedimento.

## 6. Falhas, dados antigos e política de cache

O ERP pode ficar indisponível sem que o provedor de IA esteja fora do ar, e o inverso também é possível. A arquitetura trata os dois cenários:

- **Provedor de LLM fora do ar:** o interpretador determinístico continua atendendo perguntas simples; as demais recebem erro ou solicitação de reformulação, sem inventar respostas.
- **ERP/estoque indisponível:** o Service pode oferecer o **último saldo conhecido** somente se houver política de negócio permitindo dados desatualizados para aquele produto, com informação de origem e `atualizado_em` — nunca apresentar esse valor como estoque atual confirmado.
- O limite de idade do cache não é universal. Para um estoque de baixa movimentação, 30–60 minutos foi discutido como **hipótese ilustrativa**, a ser definida e aprovada com métricas do negócio; para estoque de alta rotatividade, mesmo 20 minutos podem ser inadequados.
- Nunca usar um saldo desatualizado para reservar produtos, confirmar disponibilidade de venda ou desencadear operação crítica. Se não houver cache confiável ou política autorizada, informar indisponibilidade. A decisão sobre frescor cabe ao **Service**, não ao LLM.
- O cache deve conter marcação do último dado obtido da fonte, não apenas do momento em que alguém consultou o Redis. Controle TTL, invalidação e isolamento por escopo autorizado.

## 7. Custo, latência e resiliência

A escolha entre provedor externo ou modelo local dependerá de privacidade, infraestrutura, preço por tokens de entrada/saída, limites de requisições, capacidade, disponibilidade, residência de dados e manutenção. Não escolhemos fornecedor nem estimamos custo em reais sem volumes e preços medidos.

Medidas propostas:

1. **Roteamento híbrido:** perguntas simples usam o interpretador local sem consumir tokens; só perguntas que precisam seguem ao LLM.
2. **Modelos e prompts enxutos:** schemas compactos, limite de contexto, limites de tokens de saída e seleção de modelo adequado à tarefa.
3. **Orçamento:** acompanhar tokens e custo estimado por ferramenta/funcionalidade, por períodos e limites configurados, com alerta de consumo excessivo.
4. **Latência:** timeout e número máximo de chamadas ao modelo e às ferramentas, retry apenas quando seguro, circuit breaker, limites de concorrência e respostas controladas sob falha.
5. **Cache:** considerar cache de interpretação para perguntas não sensíveis e invariantes, mas **não reutilizar respostas com saldo/preço variável sem revalidar o dado e a permissão do usuário**. Nunca compartilhar cache de dados privados entre funcionários não autorizados.
6. **Fallback:** se o LLM estiver indisponível, preservar o caminho determinístico; se uma ferramenta estiver indisponível, responder com estado explícito em vez de alucinar.

Indicadores prioritários: taxa de atendimento pelo interpretador local versus LLM, taxa de erro/422, tempo p50/p95/p99 por etapa, taxas de timeout, tentativas e rejeições de ferramentas, uso de tokens, custo por consulta, cache hit rate, erros de autorização e satisfação/qualidade de respostas.

## 8. Observabilidade com minimização de dados

Prefiro não registrar por padrão perguntas completas, prompts, respostas de ferramentas ou conteúdo financeiro sensível. Os logs operacionais terão metadados como `request_id`, ferramenta escolhida, status, duração, origem (determinístico/LLM), versão do interpretador/modelo, uso agregado de tokens, código de erro e identificador de rastreio. Não registrar segredos, JWT, dados bancários ou conteúdo privado. A identidade auditável deve usar identificador protegido ou trilha segregada conforme política interna.

Para investigar uma resposta incorreta, correlacionamos as etapas (interpretação → seleção/validação da ferramenta → Service → fonte de dados → apresentação), verificamos se a fonte estava disponível/atual e analisamos o impacto. Qualquer coleta excepcional de conteúdo dependerá de política de retenção, minimização, autorização e acesso restrito, considerando LGPD e regras da empresa. Métricas agregadas podem ser exportadas para Prometheus/Grafana e rastreamento distribuído, alinhados à Parte 1.

## 9. Limites do que está implementado e plano de evolução

**Implementado e validado localmente na Questão 8:** interpretador determinístico de uma condição, endpoint autenticado, consulta SQLAlchemy e JSON, com testes e exemplos no README.

**Somente proposto para a Questão 9:** cliente/servidor MCP, interface de LLM plugável, seleção de ferramentas pelo modelo, ferramentas de Pedidos/Financeiro/Documentação, RBAC por escopo e perfil, fallback com cache antigo, métricas específicas de LLM e filtros avançados. Não foi realizado deploy, integração com API de LLM nem medição de tokens ou latência de modelo real.

Uma sequência futura seria: definir contratos de ferramentas → testes de permissões e limites → cliente/servidor MCP em ambiente de teste → adaptador para modelo local ou provedor autorizado → avaliações de qualidade e segurança → observabilidade → aprovação formal antes de habilitar dados financeiros adicionais.

**Resultado da decisão:** a evolução será plugável, com ferramentas consultivas estritamente controladas, MCP central e autorizações mantidas nos serviços, sem sacrificar a simplicidade da implementação real da Questão 8.
