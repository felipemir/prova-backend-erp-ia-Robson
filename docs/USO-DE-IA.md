# Uso de Inteligência Artificial — Registro de apoio

## Ferramenta utilizada

Utilizei o ChatGPT como apoio durante a análise e a preparação documental das questões de arquitetura da prova.

## Como utilizei a ferramenta

Usei a IA principalmente como apoio para estudar, discutir alternativas, fazer questionamentos sobre minhas decisões e organizar minha linha de raciocínio.

Durante a Questão 1, conversei sobre responsabilidades entre serviços, comunicação síncrona e assíncrona, concorrência, PostgreSQL, Redis, processamento de eventos, segurança e observabilidade.

Durante a Questão 2, utilizei a ferramenta para revisar conceitos do FastAPI, comparar sua organização com padrões que conheço do Java e discutir separação de responsabilidades e princípios SOLID.

Também utilizei a IA para ajudar na **redação e estruturação dos ADRs e do README**. Como o prazo da prova está curto e preciso reservar tempo para implementar e testar a solução, escrevi e revisei esses documentos com o auxílio do ChatGPT para agilizar a documentação. Mantive o controle sobre as escolhas, o conteúdo e o que seria aceito.

## Quais decisões partiram de mim

Minha preferência por começar com uma arquitetura simples e evolutiva surgiu da preocupação em não adicionar complexidade sem requisitos que a justificassem.

Trouxe como referência minha experiência com Magento 2, especialmente MSI, quantidade vendável e reservas de estoque.

Optei por investigar e otimizar gargalos antes de separar imediatamente novos microsserviços.

Na Questão 2, propus utilizar como referência o MVC do ecossistema Java, com o qual já tive contato.

Inicialmente, considerei manter consultas diretamente no Service para facilitar a leitura. Depois das discussões sobre manutenção, decidi separar Service e Repository.

Também escolhi organizar os arquivos por domínio, mantendo coerência com a modularização proposta na Questão 1.

Na discussão sobre SOLID, defendi que as regras de estoque e o processamento de notificações deveriam possuir responsabilidades separadas.

## Quais contribuições recebi da IA

A ferramenta apresentou alternativas arquiteturais, explicou conceitos técnicos e apontou possíveis limitações das minhas escolhas.

Entre os tópicos discutidos estão consistência transacional, idempotência, Transactional Outbox, cache, recuperação de mensagens, injeção de dependências no FastAPI e separação de responsabilidades.

Também recebi exemplos e perguntas para avaliar o comportamento da arquitetura diante de falhas e crescimento do sistema.

A redação inicial dos documentos foi gerada com apoio da IA, a partir das discussões e orientações que forneci.

## O que aceitei, questionei ou alterei

Não aceitei todas as alternativas como decisões definitivas.

Reconsiderei a ideia de consultar continuamente todos os pagamentos e preferi eventos como mecanismo principal, com reconciliação direcionada.

Discuti locks distribuídos e preferi começar com mecanismos transacionais do PostgreSQL.

Na Questão 2, comecei favorecendo consultas no Service e depois escolhi separá-las em Repository, considerando os efeitos na manutenção.

Solicitei que os ADRs fossem escritos como um diário pessoal de raciocínio e que o README permanecesse compacto.

## Limites deste registro

Até este ponto, o apoio descrito se refere principalmente ao estudo, à discussão arquitetural e à preparação da documentação.

As propostas conceituais não devem ser confundidas com componentes implementados, testados ou disponibilizados em produção.

O uso de IA nas próximas etapas de programação, testes, depuração e documentação deverá ser registrado conforme realmente ocorrer.

A revisão técnica, a validação das decisões e a responsabilidade pelo material submetido permanecem comigo.

### Preparação da infraestrutura Docker

Usei o ChatGPT para estruturar os arquivos de Docker/Compose e as configurações de FastAPI, PostgreSQL, Redis e worker RQ. A decisão de antecipar a conteinerização e exigir inicialização via `docker compose up` foi minha. A execução real dos containers e os testes de integração serão registrados quando forem realizados no meu ambiente.
