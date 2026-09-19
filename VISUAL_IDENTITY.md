# Identidade visual

## Posicionamento

**Tecnologia e Inovação na Administração Pública**  
**Automação · Dados · Inteligência Artificial**

A experiência com processos administrativos é o ponto de partida. A tecnologia é o meio de estruturar o trabalho e construir soluções práticas. Direito aparece na apresentação pessoal como formação; fornecedores e ferramentas ficam na seção instrumental do README.

## Conceito: fluxos organizados

Entradas distintas encontram uma estrutura comum e seguem para saídas organizadas. O símbolo combina caminhos contínuos, módulos retangulares e alinhamentos, sem atribuir cada nó a uma disciplina ou fornecedor. É uma abstração de processos, não um diagrama de arquitetura executável.

A assinatura horizontal curta sobre o nome, o verde mineral e os módulos de cantos discretamente arredondados formam o vocabulário reutilizável. Uma curva de fundo sugere cartografia, sem representar um lugar ou monumento específico. A referência ao Rio é apenas uma possibilidade de leitura, nunca necessária para entender a peça.

## Paleta

| Função | Claro | Escuro |
| --- | --- | --- |
| Fundo | `#F6F7F5` | `#111C23` |
| Texto principal | `#20343C` | `#EDF2EE` |
| Acento e pilares | `#226B66` | `#88C4B5` |
| Fluxos secundários | `#94B7AD` | `#528879` |
| Contornos e divisória | `#CAD5D2` | `#354B50` |
| Grid de fundo | `#E4EAE6` | `#203139` |
| Interior dos módulos | `#EDF1EE` | `#192930` |

O texto usa cores sólidas. O contraste dos fluxos secundários é intencionalmente menor: eles são decorativos e não carregam informação indispensável.

## Construção

- Prancheta do GitHub: 1200 × 370, margem horizontal de 64 e módulo de espaçamento de 8.
- Área verbal à esquerda; desenho à direita; pilares abaixo de uma divisória.
- Caminhos principais: 3 unidades; contornos dos módulos: 2; estrutura de fundo: 1.
- Cantos dos módulos: raio de 3–4 unidades. A borda externa de raio 12 é um acabamento do GitHub, não uma moldura obrigatória em outras redes.
- Tipografia: Segoe UI, Helvetica Neue, Arial, sans-serif. Pesos 600 para nome e mensagem principal; 500 para pilares. Sem fontes remotas ou texto convertido em curvas.
- Nome de 25 unidades com espaçamento de 3; mensagem de 40; pilares de 22. O posicionamento tem precedência visual sobre a assinatura.
- SVG estático, sem scripts, filtros, imagens externas ou animações. A Formiga de Langton conserva sua linguagem e implementação próprias na seção de contribuições.
- Até 600 pixels de largura de exibição, o desenho decorativo desaparece e os textos aumentam dentro do mesmo viewBox. As margens e a proporção permanecem. O texto alternativo e o parágrafo do README preservam o sentido fora da imagem.

## Adaptações futuras

As áreas abaixo são reservas conservadoras de composição, não garantias de recorte das plataformas. Validar cada capa na interface atual, em desktop e celular, antes de publicar. Não gerar capas esticando o hero.

| Peça | Preservar | Reorganizar ou retirar | Reserva para avatar |
| --- | --- | --- | --- |
| LinkedIn, aproximadamente 4:1 | Paleta, posicionamento, pilares e um fragmento do fluxo | Retirar moldura; reduzir grid; deslocar texto para centro-direita; nome pode ser omitido porque o perfil já o apresenta | Reservar aproximadamente os 25% da esquerda e 45% inferiores da altura para composição sem conteúdo essencial; testar a interseção com a foto em diferentes telas |
| X, aproximadamente 3:1 | Assinatura, paleta, duas linhas de posicionamento e módulos | Concentrar texto no centro e deslocar desenho para direita; retirar divisória e curva se a redução prejudicar a leitura | Reservar o quarto inferior esquerdo; manter nome e mensagens afastados das bordas superior e inferior |
| Outras capas horizontais | Mesma hierarquia e linguagem de fluxos | Recalcular quebras de linha, margens e quantidade de módulos conforme proporção e recorte reais | Mapear primeiro a sobreposição do avatar e dos controles da plataforma |
| Peças quadradas ou verticais | Verde mineral, assinatura curta, tipografia e fragmento modular | Usar composição vertical e menos texto; não comprimir o hero em um quadrado | Manter conteúdo essencial em região central compatível com eventual recorte circular |

Nenhuma capa de outra rede foi produzida nesta etapa. Este arquivo registra as decisões para que as próximas peças preservem a identidade mesmo quando as ferramentas de trabalho mudarem.
