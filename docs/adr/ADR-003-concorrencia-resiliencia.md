# ADR-003 — Concorrência, programação assíncrona e resiliência das integrações

**Uso de Inteligência Artificial:** Utilizei o ChatGPT como apoio para estudar concorrência em Python, discutir alternativas, questionar decisões arquiteturais e organizar este registro. Também utilizei IA para apoiar a elaboração da primeira versão do código e dos testes. Durante a revisão da implementação, identifiquei problemas e realizei ajustes no código, que estão registrados neste documento. O ChatGPT auxiliou na análise dessas mudanças e na atualização da documentação. O uso desse apoio acelerou o trabalho dentro do prazo da prova, mas não substitui a responsabilidade pelas decisões e pela validação da solução.

**Status:** Aceito — decisões estabelecidas e implementação da Questão 4 publicada, com validação final da versão revisada ainda pendente.

**Escopo:** Parte 2 — Questões 3 e 4 da prova prática de Back-end e Inteligência Artificial.

---

## 1. Como comecei a pensar em concorrência

Quando começamos a discutir programação assíncrona, tentei entender o assunto utilizando situações próximas de um ERP.

Imaginei uma API que precisa consultar os serviços de Clientes, Estoque e Financeiro. Minha primeira reação foi questionar por que a aplicação deveria aguardar o Financeiro responder para somente depois iniciar as outras consultas. Se essas operações não dependem umas das outras, não vejo muito sentido em executá-las sequencialmente.

Foi a partir desse exemplo que comecei a compreender melhor o `asyncio`. O que inicialmente parecia apenas uma maneira de executar várias funções acabou trazendo outras dúvidas. Uma delas era como essa abordagem se relacionaria com o Redis e os workers que já tínhamos considerado na arquitetura da Questão 1.

### Asyncio não é a mesma coisa que uma fila

Durante a discussão, entendi que o `asyncio` permite coordenar operações concorrentes dentro de um event loop. Enquanto uma coroutine aguarda uma operação de I/O assíncrona, outras tarefas podem avançar. Para consultar três serviços HTTP e devolver os resultados na mesma requisição, não precisamos obrigatoriamente utilizar uma fila.

Já o Redis com workers atende a outra necessidade: permitir que determinadas tarefas sejam executadas posteriormente, desacopladas da requisição original. Um exemplo seria processar uma notificação de estoque baixo sem obrigar o usuário a aguardar o envio dessa notificação.

Essa distinção foi importante porque não quero introduzir filas onde a concorrência assíncrona já resolve o problema.

---

## 2. Questão 3 — Asyncio, threading e multiprocessing

Procurei entender as diferenças entre os três mecanismos considerando o tipo de trabalho realizado. Não queria simplesmente afirmar que uma tecnologia é melhor que outra sem analisar o cenário.

### 2.1. Asyncio — Operações limitadas por espera de I/O

Para consultas HTTP independentes, considero `asyncio` uma escolha adequada. Se Clientes leva um segundo, Estoque dois segundos e Financeiro três segundos, executar tudo sequencialmente poderia consumir aproximadamente seis segundos. Ao iniciar as consultas concorrentemente, o tempo total pode ficar próximo da operação mais demorada, desconsiderando custos adicionais. Isso acontece porque podemos aproveitar os períodos de espera pela rede.

Também entendi que escrever `async def` não torna automaticamente qualquer operação não bloqueante. Precisamos utilizar bibliotecas compatíveis com execução assíncrona ou tratar adequadamente operações bloqueantes.

**Aplicação no ERP:** consultas concorrentes aos serviços de Clientes, Estoque e Financeiro.

### 2.2. Multiprocessing — Operações intensivas de CPU

Quando discutimos o processamento de milhões de registros para previsão de demanda, minha preferência foi utilizar processos separados. Eu já lembrava que threads de um mesmo processo compartilham seu espaço de memória, enquanto processos independentes possuem espaços de memória separados.

Mesmo sabendo que multiprocessing pode consumir mais recursos, pensei que o custo poderia ser justificado pela possibilidade de distribuir cálculos pesados entre núcleos da CPU. Durante o estudo, também compreendi melhor a influência do GIL no CPython tradicional. Ele pode limitar o paralelismo de código Python puro executado por múltiplas threads de um mesmo interpretador.

Isso reforçou minha preferência por multiprocessing para cálculos realmente intensivos. Mas não considero correto utilizar processos para qualquer tarefa. Primeiro precisamos identificar se existe uma limitação real de CPU e avaliar os custos de inicialização, memória e comunicação entre processos.

**Aplicação no ERP:** cálculos pesados de previsão de demanda ou processamento intensivo de grandes volumes de dados.

### 2.3. Threading — Integrações bloqueantes de I/O

Também discutimos um ERP que precisa acessar uma biblioteca antiga que realiza consultas HTTP de maneira síncrona. Nesse caso, não vejo necessidade inicial de utilizar multiprocessing apenas para aguardar respostas da rede. Minha preferência seria utilizar threads, considerando a frequência das chamadas e a carga esperada.

Entendi também que `asyncio.to_thread()` permite executar uma função bloqueante em uma thread, evitando bloquear diretamente o event loop. Isso pode facilitar a integração com código legado. Ainda assim, precisamos considerar limites de concorrência, segurança das bibliotecas utilizadas e timeouts.

**Aplicação no ERP:** integração com bibliotecas síncronas legadas que realizam operações bloqueantes de I/O.

### Conclusão da Questão 3

| Mecanismo | Quando considero adequado | Exemplo |
| --- | --- | --- |
| `asyncio` | Espera por I/O assíncrono | Consultar três APIs |
| `threading` | I/O bloqueante em bibliotecas síncronas | Integração HTTP legada |
| `multiprocessing` | Processamento intensivo de CPU | Previsão de demanda |

O principal aprendizado foi perceber que concorrência e paralelismo não são a mesma coisa. A escolha depende da natureza do trabalho, e não apenas da possibilidade de criar mais tarefas.

---

## 3. Questão 4 — O primeiro cenário que imaginei

Quando começamos a pensar na implementação, consideramos um endpoint que consultaria Clientes, Estoque e Financeiro. Mas, ao discutir a indisponibilidade do Financeiro, comecei a pensar em algo mais próximo de um fluxo real de pedidos.

Imaginei salvar o pedido, preservar uma reserva de estoque e informar que a situação financeira seria atualizada posteriormente. Minha preocupação era não perder o trabalho já realizado por causa da indisponibilidade de um serviço externo.

Depois percebi que estávamos misturando duas operações diferentes. Uma consulta informativa não possui as mesmas responsabilidades que uma operação de criação, pagamento ou aprovação de pedido.

Particularmente, continuo achando o segundo cenário mais interessante, porque envolve regras de negócio, consistência, idempotência e transições de estado. Mas reconheci que ele ampliaria muito o escopo da Questão 4. Por isso, decidi implementar inicialmente uma consulta informativa, deixando o cenário transacional como possibilidade de evolução.

---

## 4. Endpoint escolhido

Definimos o endpoint: `GET /orders/{order_id}/summary`.

Sua responsabilidade é consultar três fontes simuladas:

- Clientes: informações cadastrais.
- Estoque: informações de disponibilidade.
- Financeiro: informações financeiras.

O endpoint não cria pedidos, não reserva estoque e não modifica pagamentos. Escolhi utilizar mocks com `asyncio.sleep()` porque o próprio enunciado permite essa abordagem. Não considero necessário criar três microsserviços reais apenas para demonstrar concorrência, timeout e retry.

### Concorrência com asyncio.gather

A implementação utiliza `asyncio.gather()` para coordenar as três consultas. Cada integração possui tratamento individual de timeout e retry, evitando que uma falha externa esperada interrompa automaticamente os resultados das outras fontes. Essa separação permite demonstrar concorrência e tratamento de falhas sem adicionar infraestrutura desnecessária.

---

## 5. Primeira decisão: permitir respostas parciais

Quando discutimos o que aconteceria se Financeiro ficasse indisponível, considerei duas alternativas: fazer toda a requisição falhar ou preservar os dados recebidos de Clientes e Estoque. Para um resumo puramente informativo, preferi a segunda opção.

Entretanto, não queria simplesmente retornar `financeiro: null` sem explicar o motivo. Isso poderia fazer o consumidor interpretar ausência de dados como uma situação financeira conhecida. Por isso, escolhemos uma resposta que identifica os dados disponíveis, o estado de cada integração e os avisos de falha.

Também diferenciamos o estado técnico da consulta do estado comercial do pedido. Por exemplo, `status: "partial"` não significa que o pedido esteja parcialmente pago. Significa apenas que o resumo foi produzido com informações incompletas.

Inicialmente, nossa implementação retornava `complete` quando todas as integrações funcionavam e `partial` quando uma ou mais falhavam. Mas, durante a revisão do código, percebemos que havia um caso não tratado adequadamente.

---

## 6. Ajuste posterior: e se todas as integrações falharem?

Esse foi um dos problemas identificados depois que a primeira implementação já estava publicada. O endpoint retornava HTTP `200` e `status: "partial"` mesmo quando Clientes, Estoque e Financeiro falhavam simultaneamente.

Ao analisar esse comportamento, percebi que precisávamos diferenciar uma resposta realmente parcial de uma resposta sem qualquer dado útil. Se apenas Financeiro falhar, ainda podemos entregar informações de Clientes e Estoque. Mas, se nenhuma integração responder, não conseguimos montar um resumo informativo. Por isso, refinei a regra inicial.

### Decisão implementada

| Situação | Código HTTP | Status da resposta |
| --- | --- | --- |
| Todas as integrações respondem | 200 | `complete` |
| Uma ou duas integrações falham | 200 | `partial` |
| Todas as integrações falham | 503 | `unavailable` |

O HTTP `503` comunica que o endpoint não conseguiu disponibilizar o resumo devido às falhas das dependências. A resposta continua estruturada, permitindo identificar quais integrações falharam.

### Alterações realizadas

No `schemas.py`, acrescentei `unavailable` aos estados permitidos. No `service.py`, passei a diferenciar o resultado completo, parcial e totalmente indisponível. No `router.py`, passei a configurar o status HTTP `503` quando o service retorna `unavailable`.

Também foi adicionado o teste `test_todas_integracoes_indisponiveis`, que verifica o código HTTP, o estado da resposta e as informações retornadas.

Essa revisão não mudou nossa decisão original de permitir dados parciais. Ela apenas deixou mais claro que **uma resposta parcial precisa conter pelo menos um resultado válido**.

---

## 7. Minha decisão sobre timeout e retry

Desde o começo, tive uma preferência bastante clara sobre retries. Não gosto da ideia de realizar várias tentativas imediatamente, sem intervalo. Se um serviço já está enfrentando dificuldades, enviar muitas requisições consecutivas pode aumentar sua sobrecarga.

Por isso, preferi utilizar timeouts individuais e intervalos progressivos de espera. Também não queria um número elevado de tentativas. Inicialmente, falei em até três retries, mas depois esclarecemos a diferença entre retries e tentativas totais.

Minha decisão final foi: **três tentativas no total: uma tentativa inicial e dois retries.**

### Backoff progressivo

A política utiliza exponential backoff. Com os valores inicialmente propostos:

| Etapa | Timeout | Espera anterior |
| --- | --- | --- |
| Tentativa inicial | 2 segundos | Nenhuma |
| Retry 1 | 2 segundos | 0,5 segundo |
| Retry 2 | 2 segundos | 1 segundo |

Esses valores podem ser configurados. Com essa configuração, uma integração que esgote todos os timeouts pode levar aproximadamente 7,5 segundos até a falha definitiva, desconsiderando custos adicionais.

### Por que não escolhi um limite global de cinco segundos

Durante a discussão, surgiu a possibilidade de encerrar toda a consulta após cinco segundos. Preferi manter a oportunidade de executar as três tentativas.

Estou partindo da hipótese de um ERP inicialmente menor, sem evidências de tráfego extremamente elevado. Aceito uma resposta um pouco mais demorada para oferecer oportunidades adicionais de recuperação.

Mas reconheço que essa política deverá ser revista se a latência ou a taxa de falhas se tornar problemática. Quero utilizar métricas para orientar ajustes futuros, e não manter esses números permanentemente por preferência pessoal.

---

## 8. Ajuste posterior: testar o backoff de verdade

Depois da primeira implementação, identifiquei outra limitação. Os testes utilizavam `backoff_base=0`. Isso permitia verificar o número de tentativas sem precisar esperar entre elas. Era útil para manter os testes rápidos, mas não comprovava que os intervalos progressivos estavam sendo calculados corretamente.

Na prática, os testes poderiam passar mesmo que a regra de backoff estivesse errada. Por isso, acrescentei um teste específico.

O teste `test_backoff_progressivo` substitui temporariamente a função de espera por uma implementação que registra os intervalos solicitados. Com `backoff_base=0.5`, ele verifica que as esperas são:

```python
[0.5, 1.0]
```

Também verifica que ocorreram exatamente três tentativas. Achei esse ajuste importante porque não queria apenas afirmar que utilizamos backoff. Queria que o comportamento escolhido estivesse representado nos testes.

O teste está implementado no repositório, mas sua aprovação na versão revisada ainda depende da execução e confirmação da suíte.

---

## 9. Ajuste posterior: separar falhas externas de defeitos internos

Esse foi um dos pontos mais importantes da revisão. Na implementação inicial, o service utilizava um `except Exception` que capturava qualquer exceção e retornava um erro parcial. Minha intenção era evitar que uma integração indisponível derrubasse toda a consulta.

Mas percebi que esse tratamento também poderia esconder defeitos do próprio código. Imaginei, por exemplo, uma integração com uma variável inexistente ou um erro inesperado de programação. Nesse caso, o Python poderia gerar um `NameError`. Se simplesmente capturássemos essa exceção e devolvêssemos `status: "partial"`, o consumidor poderia acreditar que o serviço externo estava indisponível, quando o problema seria interno.

Isso dificultaria o diagnóstico e poderia fazer um defeito permanecer escondido atrás de um comportamento aparentemente resiliente.

### Como refinei o tratamento

Passei a utilizar uma hierarquia de exceções específicas:

```python
class IntegrationError(Exception):
    pass

class TransientServiceError(IntegrationError):
    pass

class PermanentServiceError(IntegrationError):
    pass
```

A distinção ficou assim:

**Timeout:** a chamada excedeu o tempo permitido e pode ser repetida dentro da política configurada.

**TransientServiceError:** representa uma falha transitória que pode justificar retry.

**PermanentServiceError:** representa uma falha esperada que não deve ser repetida automaticamente.

**Erro inesperado de programação:** deve ser registrado e propagado, em vez de ser apresentado como indisponibilidade normal de uma integração.

Na implementação atual, o retry trata timeouts e `TransientServiceError`. O service captura `IntegrationError` como falha esperada, mas propaga exceções inesperadas. Isso permite que um defeito interno resulte normalmente em HTTP `500`.

### Testes adicionados ou ajustados

O teste de falha permanente passou a utilizar `PermanentServiceError`, verificando que não ocorre retry.

Também foi adicionado `test_erro_inesperado_retorna_erro_interno`, que simula um `NameError` e verifica a resposta HTTP `500`.

Minha intenção foi deixar claro que **resiliência não significa esconder todos os erros**. Quero preservar resultados válidos diante de falhas externas esperadas, mas também quero que defeitos internos sejam identificados corretamente.

---

## 10. Configurações e integração com Docker

Desde nossas primeiras discussões, eu havia decidido que timeouts e retries deveriam ser configuráveis. Não queria deixar os valores fixos e espalhados pelo código.

A implementação utiliza `Settings`, em `app/core/config.py`, para ler:

- `REQUEST_TIMEOUT`
- `MAX_ATTEMPTS`
- `BACKOFF_BASE`

A configuração também valida valores inválidos, incluindo timeouts não positivos, backoff negativo e quantidade de tentativas fora do intervalo permitido.

### Problema identificado após a implementação

Durante a revisão, percebemos que o Python lia essas variáveis, mas o `compose.yaml` não as repassava para o container da API. Isso significava que alterar os parâmetros no `.env` do Docker Compose não era suficiente para modificar o comportamento da aplicação. O processo Python continuava utilizando os valores padrão.

Essa diferença entre variáveis usadas pelo Compose para interpolação e variáveis efetivamente disponibilizadas no container foi um aprendizado importante.

### Correção realizada

Atualizei o `compose.yaml` para encaminhar as três configurações ao container da API. O arquivo agora contém:

```yaml
REQUEST_TIMEOUT: "${REQUEST_TIMEOUT:-2.0}"
MAX_ATTEMPTS: "${MAX_ATTEMPTS:-3}"
BACKOFF_BASE: "${BACKOFF_BASE:-0.5}"
```

Com isso, o Compose passa a fornecer os valores configurados ao processo Python. A implementação mantém valores padrão para desenvolvimento local.

**Ponto ainda pendente:** o `.env.example` continua sem documentar essas três variáveis. Embora isso não impeça a configuração atual de funcionar, considero uma pequena melhoria necessária para facilitar o uso do projeto.

A verificação efetiva dos valores dentro do container após a última alteração também deve ser confirmada na execução local.

---

## 11. Organização do código

Mantive a arquitetura em camadas escolhida anteriormente. A Questão 4 está distribuída entre os seguintes componentes:

```text
app/
├── main.py
├── core/
│   └── config.py
├── modules/
│   └── orders/
│       ├── __init__.py
│       ├── router.py
│       ├── service.py
│       └── schemas.py
└── integrations/
    ├── mock_services.py
    └── retry.py

tests/
└── test_order_summary.py
```

O `router.py` recebe a requisição HTTP e define o contrato da rota. O `service.py` coordena as consultas, consolida os resultados e identifica o estado geral da resposta. O `schemas.py` representa o contrato da API utilizando Pydantic. O `mock_services.py` simula as três fontes de dados e suas latências. O `retry.py` concentra a política de recuperação. O `config.py` centraliza os parâmetros configuráveis.

Não criei um Repository para a consulta porque essa operação não acessa diretamente o PostgreSQL. Considero importante que cada camada tenha uma responsabilidade concreta, em vez de criar abstrações apenas para cumprir uma estrutura visual.

---

## 12. Testes e comportamento esperado

A implementação atual possui testes para os seguintes comportamentos:

| Cenário | Resultado esperado |
| --- | --- |
| Todas as fontes respondem | HTTP 200 e `complete` |
| Financeiro excede o timeout | Resposta `partial`, preservando Clientes e Estoque |
| Financeiro se recupera após retry | Resposta `complete` |
| Financeiro falha nas três tentativas | Resposta `partial`, com falha financeira |
| Falha permanente | Não executar retries desnecessários |
| Defeito inesperado de código | HTTP 500 |
| Todas as fontes indisponíveis | HTTP 503 e `unavailable` |
| Consultas concorrentes | As três operações podem avançar simultaneamente |
| Configuração inválida | Rejeitar parâmetros inválidos |
| Backoff progressivo | Registrar intervalos de 0,5 s e 1 s |

Esses testes foram escritos para demonstrar o comportamento da solução, e não apenas verificar o código HTTP do cenário de sucesso. O teste de concorrência, por exemplo, exige que as três integrações sejam iniciadas antes de liberar suas respostas. Isso ajuda a demonstrar que as operações estão sendo coordenadas concorrentemente.

**Estado da validação:** os testes constam no código atualizado. A execução integral da suíte após o último commit e a confirmação do comportamento no Docker ainda precisam ser registradas.

---

## 13. Relação com observabilidade

Minha decisão de permitir três tentativas, mesmo com maior latência, partiu de uma premissa sobre o porte inicial do ERP. Não quero tratar essa premissa como uma verdade permanente.

Conforme o volume de operações aumentar, precisamos medir o comportamento da aplicação. Gostaria de acompanhar principalmente:

- Latência por integração.
- Quantidade de timeouts.
- Quantidade de retries.
- Recuperações após uma nova tentativa.
- Falhas definitivas.
- Respostas parciais.
- Respostas totalmente indisponíveis.
- Erros internos inesperados.

Essas informações poderiam alimentar métricas em Prometheus e visualizações no Grafana, como discutimos na Questão 1. Entretanto, esses componentes ainda fazem parte do desenho de evolução, não da infraestrutura implementada para a Questão 4. Por enquanto, temos registros de logs e comportamentos testáveis que poderão servir de base para instrumentação futura.

---

## 14. Alternativas que considerei e não escolhi

Durante esse processo, algumas alternativas foram discutidas e descartadas para a implementação atual.

**Criar três microsserviços reais:** não seria necessário para demonstrar o comportamento exigido na questão.

**Utilizar Redis para realizar as consultas:** adicionaria infraestrutura sem uma necessidade concreta nesse endpoint.

**Utilizar multiprocessing para consultar APIs HTTP:** não parece adequado para operações limitadas principalmente por espera de rede.

**Fazer toda a consulta falhar quando apenas Financeiro estiver indisponível:** descartado para o resumo informativo, porque ainda existem dados úteis para devolver.

**Retornar HTTP 200 quando todas as integrações falharem:** reconsiderado durante a revisão. Agora a implementação utiliza HTTP 503.

**Realizar retries imediatos:** não corresponde à minha preferência por recuperação com intervalos progressivos.

**Executar retries ilimitados:** descartado. Mantive três tentativas no total.

**Capturar qualquer exceção como falha de integração:** reconsiderado depois de perceber o risco de esconder defeitos internos.

**Criar tarefas manuais para cada falha de consulta:** não considerei necessário porque o endpoint não modifica o estado dos pedidos.

**Implementar um fluxo completo de aprovação financeira:** continua sendo um cenário que considero mais interessante, mas não é necessário para atender à Questão 4.

---

## 15. Decisões consolidadas

Depois do estudo inicial, da implementação e da revisão, minha escolha ficou assim:

**Questão 3:** utilizar `asyncio` em operações assíncronas de I/O, `threading` para integrações bloqueantes de I/O e considerar `multiprocessing` para processamento intensivo de CPU.

**Questão 4:** implementar uma consulta informativa com três fontes simuladas, coordenadas por `asyncio.gather()`. Manter timeout individual, três tentativas no total e backoff progressivo configurável. Retornar resultados parciais quando pelo menos uma integração responder. Retornar HTTP 503 quando nenhuma fonte estiver disponível. Distinguir falhas externas esperadas de defeitos internos de programação. Não aplicar retry a falhas permanentes. Centralizar configurações e disponibilizá-las ao container por meio do Docker Compose. Testar concorrência, timeouts, retries, backoff, falhas parciais, indisponibilidade total e erros inesperados.

---

## 16. Reflexão final

O que considero mais importante nessa etapa é que minhas decisões não ficaram limitadas à primeira versão do código. Começamos discutindo conceitos de programação assíncrona, mas acabamos chegando a problemas reais de comportamento e recuperação de integrações.

Depois da implementação inicial, surgiram questões que eu não tinha considerado completamente. Uma delas foi a indisponibilidade simultânea de todas as fontes. Outra foi o risco de tratar um erro de programação como se fosse apenas uma integração indisponível.

Também percebi que ter um algoritmo de backoff no código não é a mesma coisa que possuir testes capazes de comprovar seu comportamento. E que definir configurações no Python não significa necessariamente que elas estarão disponíveis no container Docker.

Esses ajustes reforçaram minha preferência por soluções que sejam simples, mas que também tenham comportamento explícito, tratamento adequado de erros e testes coerentes com as decisões tomadas. Não considero necessário introduzir uma infraestrutura complexa para demonstrar esses conceitos. Prefiro entregar uma implementação compreensível e revisar seus limites conforme identifico problemas.

A principal mudança no meu raciocínio foi entender que **uma aplicação resiliente não deve simplesmente continuar respondendo a qualquer custo**. Ela precisa saber quando pode aproveitar resultados parciais, quando deve informar indisponibilidade e quando precisa expor um defeito interno para que ele seja corrigido.

Esse é o comportamento que procurei representar na versão revisada da Questão 4.

---

## 17. Estado atual e próximos passos

A implementação revisada está publicada na branch `feat/base-fastapi`. Os quatro pontos principais levantados na revisão receberam ajustes no código.

Ainda faltam registrar a execução integral dos testes da versão atualizada, confirmar o comportamento efetivo das variáveis no container e complementar o `.env.example`.

Essas pendências não alteram as decisões arquiteturais descritas neste documento, mas precisam ser consideradas antes de afirmar que a validação final está concluída.

Depois dessa confirmação, considero que poderemos encerrar a Questão 4 e avançar para a implementação real de Produtos e Estoque da Questão 6.
