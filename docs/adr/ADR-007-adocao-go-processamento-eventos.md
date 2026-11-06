# ADR-007 — Avaliação da adoção de Go para processamento de eventos (Questão 10)

**Status:** proposta e posicionamento técnico documentados; **nenhuma implementação em Go realizada**.

**Questão:** 10 — reflexão sobre trabalhar com Go, adequação técnica, como argumentar uma discordância e como aprender a linguagem mantendo a qualidade.

**Origem da decisão:** discussão guiada com apoio do ChatGPT, com respostas e preferências do autor. Cenários numéricos apresentados a seguir são **hipotéticos**, não métricas do ERP implementado nesta prova.

## 1. Contexto

A stack principal do cenário é Python, mas uma parte do ERP poderia processar um volume elevado de eventos com requisitos rigorosos de latência e throughput. A equipe considera Go para esse componente. Quero avaliar a escolha tecnicamente, sem assumir que uma nova linguagem resolve automaticamente o gargalo e sem confundir interesse pessoal em Go com justificativa de arquitetura.

O projeto existente nas Questões anteriores usa FastAPI/Python, PostgreSQL, Redis e trabalho em background. O objetivo aqui é **descrever uma abordagem profissional**, e não migrar ou implementar um novo serviço no repositório.

## 2. Como eu reagiria ao convite para trabalhar com Go

Aceitaria a oportunidade com interesse. Tenho vontade de aprender Go e considero positiva a experiência de contribuir em uma tecnologia nova. Vejo isso como desafio de desenvolvimento profissional e ampliação de repertório técnico.

Entretanto, disposição para aprender não equivale a estar pronto para assumir sem suporte um serviço crítico. Buscaria entender o problema, estudar os padrões da equipe, iniciar por entregas pequenas, solicitar revisões e demonstrar confiabilidade antes de ampliar minhas responsabilidades.

**Decisão:** aceitar o desafio, aprendendo e contribuindo de forma incremental, com atenção à qualidade e apoio técnico quando necessário.

### Meu raciocínio ao aprender uma linguagem que ainda não domino

Distingo **capacidade de aprender e entregar** de **justificativa para escolher uma tecnologia**. Posso aceitar uma tarefa em Go sem alegar experiência anterior: começaria pelas regras de negócio, pelo formato dos eventos e pelos critérios de aceitação. Em seguida, aprenderia os recursos da linguagem necessários para uma entrega pequena, testável e revisada. Essa abordagem evita passar semanas só estudando sintaxe sem produzir feedback técnico.

Se a equipe já decidiu usar Go por razões consistentes, meu papel é contribuir para a execução, aprender com o time e evoluir gradualmente a responsabilidade. Se ainda estamos decidindo entre Go e Python, primeiro compararia evidências e alternativas. Assim, **estar aberto à linguagem não significa escolher Go por entusiasmo**, nem usar a falta de experiência como motivo para rejeitá-la.

Um exemplo de sequência de aprendizado e entrega é: compreender um evento e seus efeitos no estoque → definir entradas, saídas e condições de erro → implementar uma versão simples em Go com teste automatizado → obter revisão de código → adicionar tratamento de duplicações, timeout e cancelamento → comparar resultados com o consumidor Python. Eu só proporia operação crítica depois de demonstrar as garantias necessárias e entender como a equipe sustentaria o serviço.

## 3. Go é razoável para um processador de eventos?

**Sim, pode ser uma escolha razoável**, especialmente para um consumidor com alta concorrência, muitas operações simultâneas, forte exigência de latência e eficiência de CPU/memória. Go oferece goroutines, channels, mecanismos de sincronização, compilação para binário e ferramentas maduras de testes e profiling.

Porém, o desempenho depende do **perfil real de trabalho**:

- Em aplicações **I/O-bound** (espera em banco, rede, broker e APIs externas), Python pode escalar bem com async I/O, workers e dimensionamento apropriado; Go não elimina a latência das dependências.
- Em aplicações **CPU-bound**, Go pode apresentar vantagens de execução e uso de recursos, mas é necessário medir com um workload representativo. Em Python, também cabem otimizações, paralelismo por processos ou bibliotecas apropriadas.
- Gargalos no PostgreSQL, na fila, em transações, no payload e em integrações precisam ser tratados onde realmente ocorrem.
- Manter uma segunda linguagem implica novos padrões de build, observabilidade, dependências, treinamento, monitoramento e suporte operacional.

O exemplo de **100 mil eventos por minuto** equivale a aproximadamente **1.667 eventos por segundo**. Esse volume, isoladamente, não demonstra que Python é inadequado; tamanho dos eventos, garantias de entrega, tempo de processamento, infraestrutura e SLOs fazem diferença.

## 4. Como validaria a necessidade antes de migrar

Meu primeiro pedido seria instrumentar a solução atual e definir objetivos mensuráveis antes de defender qualquer reescrita.

| Área | Sinais e métricas |
| --- | --- |
| Vazão | eventos processados/s, pico e capacidade sustentada |
| Latência | p50/p95/p99, tempo total da fila até a conclusão e SLO |
| Fila / broker | backlog, idade da mensagem mais antiga, taxa de consumo, redelivery |
| Recursos | CPU, memória, número de workers, saturação e limites de container |
| Dependências | latência e erros em banco, broker e APIs externas |
| Qualidade | erros, retries, DLQ, duplicação/perda de eventos, consistência do resultado |
| Custos | infraestrutura, esforço de desenvolvimento, implantação e manutenção |

Criaria testes de carga e de estresse com eventos próximos dos reais para descobrir **onde ocorre a primeira saturação**, incluindo comportamento sob falha e retomada. Também avaliaria otimizações na implementação Python existente antes de introduzir uma nova stack.

**Decisão:** migrar apenas se os dados demonstrarem um ganho que atenda necessidades reais e justifique o custo operacional.

## 5. Estratégia: protótipo e migração gradual

Não reescreveria todo o processador inicialmente. Selecionaria **um tipo representativo de evento**, por exemplo atualização de estoque, e faria um pequeno consumidor em Go para compará-lo à implementação Python.

Para um benchmark justo:

1. Fixar o contrato de entrada/saída e as mesmas regras de negócio.
2. Usar cargas equivalentes, recursos de infraestrutura comparáveis e ambientes controlados.
3. Executar cenários repetidos com aquecimento adequado e registrar vazão, latência, CPU, memória e custo por evento.
4. Verificar integridade: idempotência, duplicações, ordem quando necessária, confirmação (*ack*), retry, timeout, backpressure e encaminhamento à DLQ.
5. Comparar comportamento em recuperação de falhas, não só o melhor throughput observado.
6. Documentar os resultados e decidir com a equipe por manter Python, otimizar a solução atual ou migrar gradualmente um componente isolado.

Um processador mais rápido que perde mensagens, atualiza estoque incorretamente ou não é recuperável **não representa uma melhoria válida**. Um eventual rollout deveria ocorrer de modo controlado, com observabilidade, plano de rollback e sem consumir/confirmar duas vezes eventos de produção por acidente.

## 6. Se eu discordasse da escolha

Apresentaria a discordância de forma respeitosa, baseada em evidências. Questionaria se o gargalo é de fato a aplicação Python, compararia alternativas menos disruptivas, consideraria criticidade, SLO, ganhos demonstrados e custo total de operação.

Se o gestor propusesse Go, sugeriria um **protótipo mensurável**, em vez de uma rejeição baseada em familiaridade com Python. Mesmo que o protótipo apresentasse, por exemplo, **40% de ganho de desempenho (hipotético)**, não trataria o número isolado como autorização automática para migrar.

Precisaria avaliar se o ganho faz diferença para os objetivos do negócio e se a equipe conseguirá sustentar o novo componente. A concentração do conhecimento em poucos especialistas aumenta o risco operacional (*bus factor*): férias, ausências e rotatividade podem tornar incidentes difíceis de resolver.

Medidas para reduzir esse risco: pareamento, revisão de código por pessoas experientes, documentação, runbooks, treinamento, padrões de projeto e revezamento de responsabilidades. A decisão final deve ser compartilhada com a equipe e os responsáveis pelo serviço.

## 7. Plano de aprendizado prático de duas semanas

O plano equilibra estudo com construção desde o primeiro dia, em vez de dedicar uma semana inteira somente à sintaxe.

### Semana 1 — Fundamentos e projeto pequeno

- Sintaxe e tipos, `struct`, interfaces, módulos, `error`, tratamento explícito de falhas e biblioteca padrão.
- Ferramentas básicas: `go mod`, `go fmt`, `go vet`, `go test`; leitura de código idiomático.
- Criar um pequeno consumidor de **eventos fictícios** do ERP que valide a entrada, aplique uma regra simples e gere uma saída estruturada.
- Exercitar testes unitários e revisão de código desde o início.

**Entrega de aprendizado:** protótipo simples que eu consiga explicar, executar e testar, sem prometer prontidão para produção.

### Semana 2 — Concorrência, confiabilidade e integração

- Goroutines, channels, `context.Context`, cancelamento, timeouts, mutexes e limites de concorrência (por exemplo, worker pool).
- Evoluir o consumidor com processamento paralelo **limitado**, respeito a backpressure e encerramento gracioso.
- Simular falhas, mensagens duplicadas e indisponibilidade de dependências; aplicar retry controlado, idempotência e observabilidade básica.
- Acrescentar testes de concorrência (incluindo `go test -race`), testes de integração quando houver ambiente, benchmarks e profiling.
- Buscar code review, feedback sobre idiomatismo e segurança antes de qualquer uso crítico.

**Entrega de aprendizado:** demonstração reproduzível, documentada e revisada; o plano não garante, por si só, expertise na linguagem em 14 dias.

## 8. Qualidade e critérios para uma adoção real

A implementação futura de um consumidor Go dependeria de:

- Regras de negócio e contratos de eventos documentados e equivalentes ao serviço atual.
- Testes unitários, de integração, de concorrência, de carga e recuperação sob falhas.
- Garantias explícitas de entrega/duplicação e idempotência; sem prometer *exactly-once* apenas por trocar de linguagem.
- Métricas/tracing/logs adequados, alertas para backlog, erros e latência.
- Pipeline de build e CI, verificação de dependências, revisão, documentação operacional e rollback.
- Pelo menos uma estratégia viável de sustentação do serviço pela equipe.

## 9. Consequências e decisão final

**Benefícios potenciais:** eficiência, concorrência, menor overhead em determinados workloads e aprendizagem da equipe.

**Custos e riscos:** stack adicional, curva de aprendizagem, novos procedimentos operacionais, manutenção e dependência de poucos conhecedores.

**Decisão:** aceitaria trabalhar com Go, mas defenderia o uso da linguagem somente quando métricas e um protótipo comparável comprovassem benefícios relevantes para o ERP, acompanhados de um plano de sustentação pela equipe. Aprenderia construindo, com revisão e testes desde cedo.

**Limite de evidência:** esta é uma **resposta teórica à Questão 10**, não houve implementação em Go, medições do ERP real nem migração nesta etapa. A aplicação FastAPI e seus testes da Questão 8 continuam como descritos no README.
