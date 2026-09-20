# Langton's Ant × GitHub Contributions — Especificação de Implementação

> Especificação executável para a implementação, validação e publicação da animação autoral da Formiga de Langton no perfil `leozaow/leozaow`.

## 1. Objetivo

Criar uma visualização de perfil tecnicamente correta, elegante e incomum em que a **grade real de contribuições do GitHub participa da condição inicial da Formiga de Langton**, em vez de servir apenas como plano de fundo decorativo.

O resultado deve transmitir, em poucos segundos, três ideias: **regras simples**, **agente autônomo** e **comportamento emergente**.

A implementação deve ser própria, determinística, atualizada automaticamente e adequada ao GitHub Profile README. Não transformar o projeto em um simulador web, jogo interativo ou framework genérico nesta primeira versão.

## 2. Originalidade: posicionamento correto

A pesquisa preliminar encontrou muitos simuladores/animadores de Langton's Ant e várias animações de contribution graph (Snake, Pac-Man etc.), mas **não encontrou precedente público/indexado de uma Profile README animation em que o calendário real de contribuições seja usado como semente/estado da Formiga de Langton**.

Não declarar “primeiro do mundo”, “inédito no mundo” ou equivalentes. Se houver texto explicativo, prefira algo factual como: **“uma implementação autoral que usa minhas contribuições reais como condição inicial do autômato”**.

Referências úteis para inspeção, não para cópia cega:

- `Platane/snk` — arquitetura madura de SVG animado para contribution graph, compressão de keyframes e light/dark.
- `abozanona/pacman-contribution-graph` — coleta do calendário via GitHub GraphQL e publicação para Profile README.
- Wolfram MathWorld / literatura sobre Langton's Ant — regra, comportamento emergente e highway de período 104 na configuração vazia clássica.

## 3. Princípio conceitual não negociável

A animação **não pode ser apenas uma formiga seguindo um caminho arbitrário sobre quadrados verdes**.

A trajetória precisa ser calculada por uma implementação real do autômato.

### 3.1 Regra clássica

Usar a versão binária `RL` da Formiga de Langton. Adotar e documentar uma convenção consistente — preferencialmente:

1. célula branca/0 → gira 90° à direita;
2. célula preta/1 → gira 90° à esquerda;
3. inverte o estado da célula;
4. avança uma célula.

A convenção espelhada é matematicamente equivalente para o objetivo visual, mas não misturar convenções entre código, testes e documentação.

### 3.2 Contribuições como semente

O calendário real deve inicializar o plano binário:

- `contributionCount == 0` → estado 0;
- `contributionCount > 0` → estado 1.

A intensidade original (`contributionLevel`/contagem) continua disponível para o **visual**: tons, brilho, peso da célula ou intensidade da reação. Assim, o estado binário governa o autômato e a intensidade conserva a informação do GitHub.

### 3.3 Não usar wrap-around

Não fazer a grade 53×7 “dar a volta” nas bordas. Isso cria um toro finito e muda a dinâmica.

Simular o autômato em um **plano esparso virtualmente infinito**, inicializado com a grade de contribuições no centro. O SVG mostra o calendário como viewport principal; o plano externo existe para manter a regra correta.

## 4. Escolha inteligente do ponto inicial

Uma única escolha fixa de origem/direção pode produzir uma animação visualmente fraca para determinados calendários. Resolver isso **sem alterar a regra RL**.

Gerar candidatos determinísticos a partir dos próprios dados, por exemplo:

- contribuição ativa mais recente;
- célula ativa mais próxima do centróide ponderado por `log1p(count)`;
- centro geométrico do calendário;
- célula da região 3×3/5×3 com maior densidade de atividade.

Para cada candidato, testar as quatro orientações. Simular um horizonte curto/moderado e escolher a combinação com melhor score visual.

Score sugerido, ajustável após inspeção real:

- cobertura de células únicas dentro do calendário;
- cobertura ponderada de células com contribuição;
- fração do tempo dentro/ao redor do viewport;
- diversidade de giros e ausência de ciclos triviais muito precoces;
- penalidade para fuga imediata da área visível.

O algoritmo de escolha deve ser **100% determinístico**, com desempate estável. Mesmos dados → mesmo SVG byte a byte.

Importante: o scoring seleciona apenas **posição e orientação iniciais**. Depois disso, a trajetória é governada exclusivamente pela regra de Langton.

## 5. Direção visual

A estética deve combinar com o perfil atual: técnica, limpa e premium. Evitar excesso de elementos “gamer”, sprites infantis, textos grandes ou efeitos que prejudiquem leitura.

### 5.1 Camadas recomendadas

1. **Calendário real** — células arredondadas, preservando os 5 níveis visuais do GitHub.
2. **Estado do autômato** — overlay sutil que permita perceber flips sem apagar a informação de intensidade original.
3. **Trilha** — path fino com fade/afterglow, como “memória”/rastro do agente.
4. **Formiga** — glyph vetorial autoral, pequeno, legível e orientado para N/E/S/W; pode ser estilizado como agente computacional, não precisa ser um desenho literal/cartunesco.
5. **Reação da célula** — pulso curto/glow quando visitada, proporcional à intensidade da contribuição.
6. **Microlegenda opcional** — discreta: `LANGTON / RL / CONTRIBUTION-SEEDED` ou equivalente. Só manter se melhorar o conjunto.

### 5.2 Light e dark

Gerar obrigatoriamente:

- `langton-contribution-graph.svg`
- `langton-contribution-graph-dark.svg`

O README deve usar `<picture>` com `prefers-color-scheme`, seguindo o padrão já utilizado no repositório.

### 5.3 Movimento

Objetivo: loop hipnótico de aproximadamente 12–20 s, não frenético.

Preferir CSS/SVG nativo. Não depender de JavaScript executado no SVG, CDN, fonte externa ou runtime no cliente.

O movimento da formiga deve refletir a sequência real pré-computada de células e orientação. Compressão de keyframes é desejável: remover estados/interpolações redundantes e limitar o tamanho do arquivo.

A trilha pode usar `stroke-dasharray`/`stroke-dashoffset`, keyframes ou técnica equivalente. A interação das células pode ser simplificada visualmente desde que **a simulação interna seja correta**.

### 5.4 Reduced motion e acessibilidade

- Incluir `<title>` e `<desc>` úteis em cada SVG.
- README com `alt` descritivo em pt-BR.
- Se viável de forma confiável em SVG externo, respeitar `prefers-reduced-motion`; caso contrário, garantir que o primeiro frame já seja visualmente completo e compreensível.
- Não depender exclusivamente de cor para indicar a formiga/trilha.

## 6. Arquitetura recomendada

Manter a solução pequena e auditável. O repositório já usa Python 3.12 + stdlib para dados do GitHub; preferir a mesma linha salvo motivo técnico forte.

Estrutura esperada (nomes podem variar se houver justificativa melhor):

```text
scripts/
  generate_langton.py

tests/
  test_langton.py
  fixtures/
    contributions.json

.github/workflows/
  langton-ant.yml
  pacman.yml

README.md
LANGTON_ANT_SPEC.md
```

Evitar dependências de terceiros se a stdlib for suficiente (`urllib`, `json`, `xml`, dataclasses etc.). Não refatorar `generate_streak.py` apenas para compartilhar poucas linhas; preservar o que já funciona.

### 6.1 CLI do gerador

O gerador deve conseguir rodar de duas formas:

**Produção**

```bash
GITHUB_TOKEN=... GITHUB_REPOSITORY_OWNER=leozaow python scripts/generate_langton.py
```

**Fixture/local**

```bash
python scripts/generate_langton.py \
  --input tests/fixtures/contributions.json \
  --output-dir /tmp/langton \
  --username leozaow
```

Opções como `--steps`, `--debug-json` e `--dry-run` são bem-vindas se realmente ajudarem testes/diagnóstico, sem transformar a CLI em excesso de configuração.

### 6.2 Coleta GitHub

Usar GitHub GraphQL `contributionsCollection { contributionCalendar { weeks { contributionDays { date contributionCount contributionLevel }}}}` com `GITHUB_TOKEN`.

Requisitos:

- timeout explícito;
- erros GraphQL tratados;
- usuário inexistente / payload incompleto deve falhar claramente;
- só publicar novos SVGs depois que geração + validação terminarem com sucesso;
- nunca incluir token em arquivo, log ou SVG.

### 6.3 Modelo de dados

Separar claramente:

- dados de contribuição;
- estado binário do autômato;
- posição/direção da formiga;
- frames/trajectory;
- renderização SVG.

A lógica do autômato deve ser função pura o suficiente para testes determinísticos.

## 7. Publicação e GitHub Actions

Criar `.github/workflows/langton-ant.yml` com:

- `schedule` diário em horário diferente do workflow de streak;
- `workflow_dispatch`;
- `push` restrito aos arquivos do gerador/testes/workflow, se útil;
- `permissions: contents: write`;
- Python 3.12;
- testes antes da geração;
- geração light + dark;
- validação dos SVGs;
- publicação apenas quando houver mudança.

### 7.1 Branch `output`

Continuar usando a branch `output` para não criar commits diários na `main`.

**Preservar os SVGs antigos do Pac-Man** na `output` para rollback. O novo processo deve atualizar somente os artefatos Langton, sem apagar arquivos não relacionados.

Pode usar git diretamente no workflow ou uma Action bem mantida, mas o comportamento `keep existing files` precisa ser inequívoco.

### 7.2 Pac-Man temporariamente desativado

Não apagar a implementação do Pac-Man.

Alterar `.github/workflows/pacman.yml` para manter apenas `workflow_dispatch` durante o experimento, removendo/suspendendo o `schedule`. Dessa forma:

- não sobrescreve/gera diariamente;
- continua disponível manualmente;
- rollback é trivial.

O README deixa de referenciar o Pac-Man e passa a usar os dois SVGs Langton da branch `output`.

## 8. README

Substituir somente a seção atual de contribuições/Pac-Man. Não redesenhar o restante do perfil.

Sugestão de heading:

```md
### 🐜 Contribuições · Formiga de Langton
```

Usar algo próximo de:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/leozaow/leozaow/output/langton-contribution-graph-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/leozaow/leozaow/output/langton-contribution-graph.svg">
  <img alt="Formiga de Langton interagindo com meu calendário real de contribuições no GitHub" src="https://raw.githubusercontent.com/leozaow/leozaow/output/langton-contribution-graph.svg" width="100%">
</picture>
```

Uma única linha explicativa curta pode ser adicionada se o visual não for autoexplicativo. O perfil é intencionalmente enxuto; não adicionar uma aula sobre autômatos no README.

## 9. Testes obrigatórios

No mínimo:

1. **Regras RL** — posições, direções e flips dos primeiros passos de um caso pequeno conhecido.
2. **Plano infinito/esparso** — coordenadas negativas e saída do retângulo do calendário funcionam sem wrap-around.
3. **Mapeamento do calendário** — semanas/dias em coordenadas corretas e preservação de `contributionCount`/nível.
4. **Seed** — `count > 0` gera estado 1; zero gera 0.
5. **Seleção determinística** — mesma fixture escolhe a mesma origem/orientação/trajectory.
6. **Renderização** — SVG light/dark XML válido, contém `<title>/<desc>`, não contém `<script>` nem token.
7. **Tamanho** — definir teto razoável e falhar se uma alteração explodir o SVG. Meta preferencial: cada arquivo < 350 KiB; limite máximo inicial pode ser maior se justificado.
8. **Determinismo byte a byte** — duas gerações com a mesma fixture devem produzir hash idêntico.
9. **Caso vazio/esparso** — calendário sem atividade ou quase vazio ainda produz visual válido.

Se implementar detecção de highway, adicionar teste próprio. Não usar “highway” como afirmação sobre a seed de contribuições sem detectar de fato.

## 10. Qualidade visual verificável

Além dos testes unitários, o agente deve gerar uma amostra local e inspecioná-la.

Critérios:

- formiga visível sem dominar o gráfico;
- trajetória não parece um path arbitrário desconectado das células;
- contribuição permanece reconhecível como calendário do GitHub;
- light/dark têm contraste adequado;
- sem clipping inesperado;
- sem texto ilegível em viewport móvel;
- loop sem salto visual grosseiro;
- arquivo carrega sem recursos externos.

Se houver acesso a browser/screenshot, usar. Caso não haja, validar SVG estruturalmente e abrir/inspecionar o arquivo com as ferramentas disponíveis.

## 11. Ideias avançadas — implementar somente se melhorarem o resultado

### 11.1 Highway detector honesto

Opcional: analisar a trajetória procurando periodicidade por translação. Se uma sequência compatível com highway for realmente detectada, exibir um microindicador discreto (`EMERGENT HIGHWAY`) ou usar isso para selecionar o melhor trecho. Se não houver detecção, não exibir.

### 11.2 Trail com memória de contribuição

A intensidade do glow/trail ao visitar uma célula pode depender de `log1p(contributionCount)`, preservando a relação com atividade real sem alterar a regra do autômato.

### 11.3 “Agent telemetry” mínima

Opcionalmente renderizar microtexto técnico como `RL · step 184 · N/E/S/W` por animação. Só usar se continuar elegante e sem inflar muito o SVG.

### 11.4 Assinatura autoral

Adicionar em comentário/metadata do SVG algo como `Generated by leozaow/leozaow Langton contribution renderer`, sem marketing visual intrusivo.

## 12. Antipadrões proibidos

- caminho da formiga desenhado manualmente;
- randomização não determinística;
- wrap-around do calendário;
- JavaScript embutido necessário para a animação funcionar;
- dependência de serviço externo para renderização diária;
- alterar artificialmente o histórico de contribuições;
- criar commits falsos para “desenhar” padrões no contribution graph;
- apagar os artefatos/fluxo do Pac-Man durante o experimento;
- afirmar originalidade absoluta sem evidência;
- refatorar partes não relacionadas do perfil;
- sacrificar fidelidade técnica só para produzir um efeito visual mais chamativo.

## 13. Protocolo autônomo de execução

Ao receber a ordem de implementação:

1. Ler `AGENTS.md`, este arquivo, `README.md`, workflows e scripts existentes.
2. Confirmar o estado atual de `main` e sincronizar com `origin/main` antes de editar.
3. Inspecionar rapidamente `Platane/snk` e `abozanona/pacman-contribution-graph` apenas para padrões úteis de coleta/renderização; não copiar arquitetura desnecessária.
4. Implementar o núcleo da simulação e seus testes antes de polir o SVG.
5. Gerar fixture/preview, medir cobertura, duração e tamanho; ajustar automaticamente parâmetros visuais/scoring se necessário.
6. Implementar workflow e troca do README.
7. Suspender somente o agendamento automático do Pac-Man; preservar rollback.
8. Rodar todos os testes e validações locais disponíveis.
9. Revisar `git diff` integralmente e remover artefatos temporários/debug.
10. Fazer commits pequenos/coerentes em Conventional Commits ou um único commit atômico se a mudança estiver fortemente acoplada.
11. Fazer `git push origin main` sem pedir confirmação adicional, desde que todos os critérios estejam satisfeitos.
12. Disparar/acompanhar `langton-ant.yml` se a ferramenta/credencial disponível permitir; verificar que os SVGs chegaram à `output` e que os raw URLs respondem.
13. Se o workflow falhar, investigar e corrigir; não deixar o README apontando para artefato inexistente. Se não for possível validar publicação, preservar o estado anterior do README até existir um artefato válido.
14. Encerrar com relatório objetivo: arquivos alterados, testes, commit SHA, status do workflow/publicação e qualquer limitação real.

## 14. Definição de pronto

A tarefa só está concluída quando:

- a trajetória é calculada por uma implementação real e testada da Formiga de Langton;
- o calendário real participa da condição inicial;
- não há wrap-around;
- light/dark foram gerados;
- atualização diária funciona;
- `output` preserva os arquivos antigos do Pac-Man;
- Pac-Man ficou disponível manualmente, mas sem cron;
- README exibe Langton em vez do Pac-Man;
- testes passam;
- geração é determinística;
- SVGs são autocontidos e de tamanho aceitável;
- commit/push foram feitos;
- a publicação foi validada, ou a mudança do README foi retida até que pudesse ser validada.

## 15. Prioridade de decisão

Quando houver conflito entre alternativas, decidir nesta ordem:

1. correção do autômato;
2. integridade das contribuições reais;
3. confiabilidade no GitHub Profile README;
4. legibilidade e impacto visual;
5. simplicidade operacional;
6. tamanho/performance do SVG;
7. recursos extras.

O objetivo é que o resultado seja impressionante **porque a ideia e a execução são tecnicamente boas**, não porque há muitos efeitos.