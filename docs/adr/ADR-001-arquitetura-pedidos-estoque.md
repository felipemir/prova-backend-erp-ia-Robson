## Transparência sobre o uso de IA

Durante a elaboração deste ADR, utilizei o ChatGPT como ferramenta de apoio, principalmente para me ajudar a questionar minhas decisões, explorar alternativas técnicas e organizar melhor meus pensamentos.

Também utilizei a IA para auxiliar na escrita e estruturação deste documento. Como estou com um prazo curto para concluir a prova, escrever manualmente todos os registros de decisão consumiria um tempo considerável que também preciso dedicar à implementação.

Por isso, optei por utilizar o ChatGPT para agilizar a documentação.

Entretanto, mantive o controle sobre o conteúdo e as decisões apresentadas aqui. Durante as conversas, trouxe experiências do meu trabalho com Magento 2, questionei sugestões, considerei alternativas, mudei algumas opiniões e defini quais abordagens faziam mais sentido para o projeto.

A IA me ajudou a estudar, organizar e redigir essas ideias, mas as escolhas registradas representam o raciocínio que desenvolvi durante a resolução da prova.

---

# ADR-001 — Como fui pensando na arquitetura de Pedidos e Estoque

**Status:** Aceito — base arquitetural estabelecida (sujeita a evolução documentada).

## 1. Por onde eu comecei

Quando comecei a pensar nessa questão, a primeira coisa que eu quis fazer foi definir uma arquitetura que atendesse ao que o ERP precisa agora, mas sem criar uma estrutura extremamente complexa logo de cara.

Também não queria fazer algo tão básico que depois precisasse ser refeito por completo quando surgissem novos requisitos.

O problema é que o enunciado não fala quantos usuários o ERP tem, quantos pedidos ele processa por dia, quantas requisições recebe por segundo ou qual disponibilidade precisa garantir.

Então fiquei pensando: por que eu montaria uma arquitetura altamente distribuída sem saber se realmente existe necessidade disso?

Preferi ser mais cauteloso.

Para organizar minhas ideias, comecei a relacionar o cenário com coisas que já vi trabalhando com Magento 2, PHP e e-commerce.

A partir disso, separei algumas premissas.

**O que o sistema precisa fazer:**
- Criar e acompanhar pedidos.
- Consultar produtos e disponibilidade.
- Controlar reservas e movimentações de estoque.
- Consultar informações de Clientes.
- Receber informações do Financeiro.
- Executar tarefas que podem acontecer em segundo plano.

**O que eu considero importante para funcionar bem:**
- Não deixar o estoque ficar inconsistente.
- Ter autenticação e permissões.
- Conseguir se recuperar de falhas.
- Evitar processar a mesma operação duas vezes.
- Ter logs e métricas para investigar problemas.
- Manter uma estrutura organizada e fácil de modificar.
- Conseguir evoluir conforme o ERP crescer.

Esses pontos são premissas minhas. Não estou dizendo que a IPM forneceu todos esses requisitos.

## 2. Minha primeira ideia foi separar os microsserviços

De começo, pensei em criar um microsserviço de Pedidos e outro de Estoque.

Até fazia sentido, porque o ERP já trabalha com microsserviços de Clientes e Financeiro.

Cada serviço poderia ter sua responsabilidade e ser atualizado ou escalado separadamente.

Mas aí comecei a pensar em como isso funcionaria na prática.

Lembrei do Magento 2, principalmente do MSI, das reservas e da Salable Quantity.

Uma coisa que essa experiência me ensinou é que ter dez unidades físicas de um produto não significa necessariamente que as dez estão disponíveis para novas vendas.

Parte dessas unidades pode estar comprometida com pedidos.

Também lembrei das situações em que precisamos acompanhar o saldo das reservas e entender por que a quantidade vendável não corresponde exatamente ao estoque físico.

Aí pensei em outro cenário.

Imagina que só existe uma unidade disponível e dois clientes tentam comprar ao mesmo tempo.

Se os dois consultarem a disponibilidade antes de uma reserva ser confirmada, ambos podem acreditar que conseguem comprar.

Agora imagina que Pedidos e Estoque estejam em microsserviços diferentes. Além da concorrência, preciso pensar no que acontece se a comunicação falhar no meio da operação.

Foi aí que comecei a questionar minha primeira ideia.

Não estou dizendo que separar os serviços seria errado. Só comecei a achar que isso poderia trazer uma complexidade que talvez não precisássemos enfrentar agora.

Por isso, preferi manter Pedidos e Estoque na mesma aplicação, mas como módulos separados.

Ou seja, um **monólito modular**, integrado aos microsserviços que já existem no ERP.

## 3. Como eu dividiria as responsabilidades

Mesmo mantendo Pedidos e Estoque juntos, não quero misturar todas as regras.

O módulo de Pedidos cuidaria da criação dos pedidos, acompanhamento dos estados, cancelamentos e comunicação com o Financeiro.

O módulo de Estoque cuidaria das quantidades, disponibilidade, reservas, liberações e movimentações.

Uma coisa que considero importante é o módulo de Pedidos não sair modificando os dados de Estoque diretamente, ignorando as regras desse módulo.

Prefiro que ele utilize operações bem definidas.

Quanto aos microsserviços existentes, quero manter a responsabilidade de cada um.

Clientes continua cuidando dos dados cadastrais.

Financeiro continua cuidando das operações financeiras.

Não quero que nosso novo módulo consulte diretamente as tabelas internas desses serviços. Acho mais coerente utilizar APIs ou eventos que eles disponibilizem.

## 4. Mas e se o sistema crescer?

Essa foi outra coisa que fiquei pensando.

Eu sei que um monólito modular também tem suas limitações.

Pedidos e Estoque compartilham recursos e implantação. Então, se um dos módulos começar a consumir muitos recursos, isso pode acabar afetar o outro.

Mas não acho que qualquer aumento de movimento seja motivo para sair criando um microsserviço novo.

Por exemplo, se Estoque começar a receber muitas operações de Compras ou Almoxarifado, minha primeira atitude seria investigar o que realmente está acontecendo.

Será que temos consultas lentas? Índices ruins? Muitas operações concorrentes? Algum processamento desnecessário?

Eu começaria por essas questões.

Se conseguirmos resolver o problema otimizando consultas, índices ou processamento, não vejo por que aumentar a complexidade.

Agora, se chegar um momento em que Estoque realmente precise ser implantado ou escalado de maneira independente, aí sim faria sentido reconsiderar a separação.

Foi por isso que achei importante manter os módulos organizados desde o começo.

## 5. REST ou mensageria?

Aqui eu fiquei pensando em como nosso módulo conversaria com Clientes e Financeiro.

De início, considerei as duas alternativas: comunicação síncrona e assíncrona.

Depois percebi que não precisava escolher uma só para tudo.

Se eu preciso consultar uma informação e não consigo continuar a operação sem a resposta, REST faz bastante sentido.

Por exemplo, validar alguma informação cadastral do cliente durante a criação do pedido.

Nesse caso, quero receber a resposta e decidir se posso continuar.

Mas também preciso considerar que o serviço de Clientes pode ficar indisponível ou demorar demais.

Então colocaria timeout e tratamento de erro. Não quero interpretar uma falha de comunicação como se o cliente tivesse sido validado.

Agora, para coisas como notificações e atualização de relatórios, acho mais interessante trabalhar com processamento assíncrono.

Não vejo sentido em fazer o cliente esperar pelo envio de um e-mail para receber a confirmação de um pedido que já foi concluído.

Então, nesse caso, uma fila ou evento faz mais sentido.

## 6. A parte dos pagamentos me fez mudar de ideia

Um cenário que me preocupou foi o seguinte:

E se o Financeiro aprovar um pagamento, mas o módulo de Pedidos não receber essa confirmação?

O pagamento estaria aprovado, mas o pedido poderia continuar pendente.

Minha primeira ideia foi fazer consultas periódicas para verificar os pagamentos.

Só que depois comecei a pensar na quantidade de consultas que isso poderia gerar.

Por que consultar todos os pagamentos o tempo inteiro, inclusive os que já estão resolvidos?

Então mudei essa ideia.

Prefiro que o Financeiro publique um evento, como `PagamentoAprovado`, e que Pedidos utilize esse evento para atualizar o estado.

Mas também quero ter uma maneira de recuperar situações em que a confirmação não chegou.

Nesse caso, um processo de reconciliação poderia identificar pedidos pendentes e consultar o Financeiro por REST.

Assim, não preciso consultar tudo constantemente.

Outra coisa que discutimos foi a possibilidade de receber a mesma mensagem mais de uma vez.

Não quero que uma mensagem duplicada no processamento provoque operações duplicadas no pedido.

Por isso, preciso pensar em idempotência.

Também fiquei pensando no que acontece se o Financeiro atualizar o banco, mas falhar antes de publicar o evento.

Foi aí que conheci melhor a ideia de **Transactional Outbox**.

Achei interessante porque ela ajuda a registrar o evento junto da alteração persistida, para que a publicação possa ser retomada depois.

Não significa que já implementei isso, mas é um mecanismo que eu consideraria para eventos críticos.

## 7. Por que PostgreSQL?

Minha preferência foi PostgreSQL principalmente por causa da consistência dos dados.

Pensando nas reservas do estoque, eu não quero depender de uma consulta simples que diz que o produto está disponível e depois tentar reservar sem nenhuma proteção.

Nesse intervalo, outra requisição pode ter consumido o mesmo estoque.

Por isso, considero importante utilizar transações, atualizações condicionais e os mecanismos de concorrência do PostgreSQL.

Também não quero deixar uma transação aberta enquanto espero alguém pagar um pedido.

A reserva precisa acontecer de maneira consistente, mas a confirmação financeira pode levar muito mais tempo.

Se o pagamento não acontecer dentro do prazo definido pelas regras de negócio, podemos ter um processo que identifique e libere a reserva.

Também pensei na questão de desempenho.

Se o banco começar a ficar lento, não quero assumir imediatamente que precisamos trocar de tecnologia ou criar outro serviço.

Primeiro investigaria as consultas, os índices e o comportamento do banco.

## 8. Onde o Redis entra?

Pensei no Redis principalmente para cache e tarefas em segundo plano.

No cache, a ideia seria evitar consultas repetidas ao PostgreSQL para dados que são acessados com frequência.

Minha primeira preferência foi atualizar o cache depois de atualizar o banco.

Mas aí comecei a perceber que isso também pode dar problema.

E se o PostgreSQL atualizar e o Redis falhar?

E se duas operações concorrentes atualizarem o cache em uma ordem diferente da esperada?

Foi aí que percebi que precisava pensar melhor na política de invalidação.

Não quero que o Redis seja a fonte de verdade do estoque.

Para confirmar uma reserva, prefiro utilizar os mecanismos de consistência do PostgreSQL.

E, se o Redis ficar indisponível, quero que as consultas compatíveis continuem funcionando diretamente no banco, mesmo que isso deixe a aplicação um pouco mais lenta.

Também pensei em utilizar locks distribuídos no Redis.

Mas, pelo menos nesse primeiro momento, não vi necessidade de adicionar isso se o PostgreSQL já consegue proteger as operações críticas.

## 9. E as tarefas em segundo plano?

Aqui pensei em utilizar Redis com workers.

Um exemplo seria gerar alertas quando determinado produto estivesse com estoque baixo.

Não vejo necessidade de executar toda a notificação dentro da requisição HTTP.

Também começamos a pensar no que aconteceria se a tarefa falhasse.

Minha ideia inicial foi tentar novamente algumas vezes, com intervalos progressivos.

Considerei um intervalo de aproximadamente cinco minutos depois de uma falha e depois uma espera maior, entre quinze e trinta minutos.

Depois de três tentativas sem sucesso, prefiro registrar o problema e sinalizar que precisa de investigação, em vez de repetir para sempre.

Ainda precisamos definir os detalhes disso na implementação.

Uma coisa importante que aprendi nessa discussão foi que Redis Pub/Sub não é a mesma coisa que uma fila durável.

Para eventos financeiros críticos, eu precisaria avaliar uma solução com garantias adequadas de entrega e recuperação, como RabbitMQ ou SQS.

## 10. Por que considerei Kong?

Quando comecei a pensar na entrada das requisições, achei interessante ter um API Gateway.

Considerei o Kong porque ele poderia concentrar o roteamento, algumas validações de autenticação e políticas como rate limiting.

Mas teve uma coisa que eu não quis fazer: colocar todas as regras de autorização no gateway.

Um usuário pode estar autenticado e mesmo assim não ter permissão para executar determinada operação.

Por isso, prefiro deixar as validações gerais no gateway e manter as permissões específicas dentro dos serviços.

Também considero importante proteger as APIs internas para que elas não possam ser acessadas diretamente por fora da arquitetura prevista.

## 11. Como eu descobriria que alguma coisa está dando errado?

Aqui comecei a pensar em observabilidade.

Não adianta muito a aplicação funcionar se, quando ela ficar lenta ou começar a apresentar falhas, eu não conseguir descobrir o motivo.

Por isso, considerei Prometheus e Grafana para acompanhar métricas.

Quero conseguir observar tempo de resposta, taxa de erros, consumo de recursos, filas pendentes e problemas nas integrações.

Durante nossa conversa, pensei em priorizar alertas de lentidão e sobrecarga da API.

O motivo é que uma API muito lenta pode afetar várias operações ao mesmo tempo.

Mas também percebi que não posso deixar de acompanhar inconsistências como pagamentos aprovados que continuam pendentes.

Outra coisa que ficou clara pra mim é que olhar um gráfico não é suficiente para descobrir a causa de um problema.

Se o Grafana mostrar que uma requisição está demorando demais, ainda preciso investigar onde está acontecendo a demora.

É aí que entram os traces.

E, depois de localizar a etapa problemática, os logs estruturados ajudam a entender os erros e o contexto.

Por isso, considerei utilizar métricas, logs e tracing juntos.

## 12. Onde cheguei depois dessas decisões

Depois de discutir todas essas alternativas, continuei preferindo uma arquitetura simples e evolutiva.

Não quero complicar o ERP sem necessidade, mas também não quero deixar de pensar em consistência, segurança e recuperação de falhas.

Minha ideia é começar com Pedidos e Estoque bem organizados dentro da mesma aplicação, mantendo a integração com Clientes e Financeiro.

PostgreSQL fica como fonte de verdade.

Redis entra como apoio para cache e workers.

REST e mensageria são utilizados conforme a necessidade de cada operação.

E a observabilidade ajuda a identificar quando alguma dessas escolhas precisa ser reavaliada.

Ainda temos algumas coisas para definir melhor, como a invalidação do cache, a configuração exata das tarefas e os mecanismos de recuperação.

Não quero fingir que já resolvi esses detalhes.

O objetivo deste ADR é registrar como cheguei à proposta, inclusive as dúvidas e mudanças de ideia que aconteceram no caminho.
