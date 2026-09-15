# AGENTS.md

Diretrizes essenciais para agentes autônomos de IA que operam neste repositório.

## 🎯 Objetivo & Contexto
- **Perfil do Repositório:** Perfil de GitHub pessoal/portfólio (`leozaow/leozaow`), automações, badges e scripts.
- **Autonomia com Foco:** Atue de forma proativa e direta na resolução da tarefa solicitada.

## 🛠️ Regras de Execução
1. **Escopo Preciso:** Altere apenas arquivos pertinentes à tarefa solicitada. Não modifique configurações ou arquivos não relacionados.
2. **Qualidade & Sintaxe:** Valide marcação Markdown, integridade de links, caminhos de assets e sintaxe de scripts antes de concluir.
3. **Consistência:** Mantenha os padrões visuais, linguísticos (pt-BR para perfil/docs quando aplicável) e estrutura do projeto.

## 📝 Commits (Conventional Commits)
Siga estritamente o padrão [Conventional Commits](https://www.conventionalcommits.org/):

```
<tipo>(<escopo opcional>): <descrição no imperativo e em minúsculas>
```

- **Tipos comuns:**
  - `feat`: Nova funcionalidade, badge ou automação
  - `fix`: Correção de bug, link quebrado ou renderização
  - `docs`: Alterações em documentação (ex.: `README.md`, `AGENTS.md`)
  - `style`: Ajustes visuais, formatação ou layout sem alterar lógica
  - `refactor`: Refatoração de scripts ou organização sem mudar comportamento
  - `ci`: Alterações em workflows do GitHub Actions (`.github/workflows/`)
  - `chore`: Atualizações de rotina, dependências ou metadados

- **Exemplos:**
  - `docs: renomeia agentes.md para AGENTS.md e sintetiza diretrizes`
  - `fix(readme): corrige caminho do asset no dark mode`
  - `ci: ajusta cron do workflow de métricas`
