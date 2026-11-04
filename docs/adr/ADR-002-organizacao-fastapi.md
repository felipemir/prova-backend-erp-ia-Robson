## Transparência sobre o uso de IA

Durante a elaboração deste ADR, utilizei o ChatGPT como ferramenta de apoio, principalmente para me ajudar a questionar minhas decisões, explorar alternativas técnicas e organizar melhor meus pensamentos.

Também utilizei a IA para auxiliar na escrita e estruturação deste documento. Como estou com um prazo curto para concluir a prova, escrever manualmente todos os registros de decisão consumiria um tempo considerável que também preciso dedicar à implementação.

Por isso, optei por utilizar o ChatGPT para agilizar a documentação.

Entretanto, mantive o controle sobre o conteúdo e as decisões apresentadas aqui. Durante as conversas, trouxe experiências do meu trabalho com Magento 2, questionei sugestões, considerei alternativas, mudei algumas opiniões e defini quais abordagens faziam mais sentido para o projeto.

A IA me ajudou a estudar, organizar e redigir essas ideias, mas as escolhas registradas representam o raciocínio que desenvolvi durante a resolução da prova.

---

# ADR-002 — Como escolhi organizar o projeto FastAPI

**Status:** Aceito — base arquitetural estabelecida (sujeita a evolução documentada).

## 1. Primeiro quis entender como o FastAPI trabalha

Quando começamos a Questão 2, minha primeira ideia foi utilizar o MVC, porque já conheço esse padrão do Java e do Spring Boot.

Mas aí pensei: antes de sair escolhendo MVC, como o FastAPI normalmente trabalha?

Quis entender isso primeiro para não tentar colocar um padrão do Java no Python sem saber se fazia sentido.

Fui entendendo que o FastAPI possui recursos como `APIRouter`, `Depends` e Pydantic, mas não obriga a seguir uma arquitetura específica.

Isso me deixou mais confortável para adaptar algo que já conheço.

Minha ideia não é fazer uma cópia do Spring Boot.

Quero aproveitar a separação de responsabilidades que aprendi no Java e utilizar os recursos que o FastAPI já oferece.

Como Python trabalha com tipagem dinâmica, também quero manter os contratos claros, utilizando type hints e Pydantic para validar os dados.

Acho que isso ajuda bastante no entendimento e na manutenção do código.

## 2. Por que pensei em Router, Service e Repository?

Quero conseguir olhar para um arquivo e entender qual é sua responsabilidade.

Não gosto da ideia de ter um endpoint fazendo tudo: recebendo a requisição, validando as regras, consultando o banco e ainda executando outras operações.

Então pensei em separar assim:

- **Router:** recebe as requisições e encaminha as operações.
- **Service:** cuida das regras de negócio.
- **Repository:** concentra o acesso ao banco.
- **Model:** representa as entidades persistidas.
- **Schema:** define os dados que entram e saem da API.

Também quero utilizar o `Depends` para injetar dependências, aproveitando algo que já conheço do Spring.

## 3. Eu quase deixei as consultas no Service

Essa parte foi interessante porque minha primeira preferência não era criar um Repository separado.

Eu pensei que seria mais fácil abrir o ProductService e encontrar ali a regra e a consulta SQL.

Na minha cabeça, isso deixaria o código mais direto.

E ainda acho que, para algo bem pequeno, essa abordagem pode funcionar.

Mas depois começamos a conversar sobre manutenção.

Imaginei que precisávamos buscar um produto e que essa consulta estivesse apresentando um problema.

Minha primeira reação seria tentar descobrir por que diabos ela está falhando.

Será que foi timeout? Algum lock? A consulta está errada? O banco está sobrecarregado?

Também iria querer saber se o erro acontece sempre ou se foi algo pontual.

Isso me lembrou do Magento, onde trabalhamos com módulos e mecanismos de extensão, tentando evitar mudanças desnecessárias em partes que já funcionam.

Comecei a perceber que, se as consultas ficarem espalhadas pelos Services, talvez uma mudança futura seja mais trabalhosa do que parece agora.

Foi aí que passei a achar o Repository mais interessante.

Se o problema estiver no acesso ao banco, consigo investigar e corrigir essa parte.

Se estiver na regra de negócio, investigo o Service.

No fim, preferi separar os dois.

Mas não quero criar uma quantidade absurda de classes e interfaces só para dizer que estou seguindo um padrão.

Quero manter isso simples.

## 4. Como escolhi organizar as pastas

Depois tivemos outra dúvida: organizar os arquivos por camada ou por domínio?

Uma opção seria criar uma pasta para todos os Routers, outra para Services e outra para Repositories.

Não vejo nada de errado nisso.

Mas comecei a pensar na Questão 1.

Lá eu já tinha decidido utilizar uma arquitetura modular.

Então, por que mudaria completamente essa linha de raciocínio agora?

Preferi manter os arquivos relacionados próximos.

Por exemplo, dentro do módulo de Produtos, quero encontrar seu Router, Service, Repository, Models e Schemas.

Dentro de Estoque, a mesma ideia.

Assim, quando precisar investigar uma funcionalidade, já sei por onde começar.

Também achei essa organização mais próxima da experiência que tenho trabalhando com módulos no Magento.

Por isso, escolhi a organização por domínio.

Não porque a outra esteja errada, mas porque essa faz mais sentido para o projeto que estamos construindo.

## 5. Onde o SOLID entra?

Eu já tive contato com SOLID no Java, embora não tenha estudado todos os princípios profundamente.

Durante a conversa, pensamos em um exemplo envolvendo alertas de estoque baixo.

A pergunta era se o StockService deveria cuidar também de toda a formatação e envio dos e-mails.

Na minha cabeça, não fazia sentido nenhum.

O StockService tem uma responsabilidade relacionada ao estoque.

Formatar e enviar e-mails é outra coisa.

Então prefiro que ele identifique quando o estoque está baixo e delegue a notificação para outro componente.

Isso me parece muito mais organizado.

Se depois precisarmos mudar a notificação, não quero ter que modificar as regras de estoque só por causa disso.

Foi aí que relacionei essa escolha com o princípio da responsabilidade única, o SRP.

Também comecei a entender melhor como separar dependências pode facilitar os testes.

Mas continuo com a mesma ideia: não quero implementar interfaces, classes ou padrões apenas para deixar o projeto aparentemente sofisticado.

Quero utilizar o que realmente fizer sentido.

## 6. E Clean Architecture e DDD?

Aqui também preferi não complicar demais.

Não quero dizer que vou implementar Clean Architecture completa ou DDD completo se não existe necessidade disso.

Mas alguns conceitos são interessantes para nosso projeto.

Da Clean Architecture, quero aproveitar a ideia de não misturar regras de negócio com detalhes do framework ou do banco.

Do DDD, quero aproveitar a organização por domínio e a separação das responsabilidades.

Isso combina com a escolha que já fiz na Questão 1.

## 7. A estrutura que estou pensando em utilizar

Depois dessas discussões, cheguei nesta organização inicial:

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

Proposta de arquitetura.

Conforme a implementação avançar, vou ajustar o que for necessário.

## 8. Por que fiquei com essa estrutura?

No fim, minha escolha foi utilizar uma arquitetura em camadas inspirada no MVC do Java, mas adaptada ao FastAPI.

Quero manter Router, Service e Repository separados e organizar essas camadas dentro de cada domínio.

Acho que isso deixa a aplicação mais fácil de entender e também mantém a mesma linha de raciocínio que comecei a construir na Questão 1.

O que eu quero evitar é tanto uma aplicação onde tudo fica misturado quanto uma estrutura cheia de abstrações que só tornam a manutenção mais difícil.

Prefiro começar com uma base clara, organizada e que possa evoluir conforme o projeto realmente precisar.

E quero manter este ADR como um registro das minhas decisões, inclusive das ideias que tive no começo e depois resolvi mudar.
