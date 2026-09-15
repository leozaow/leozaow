# 🤖 Diretrizes e Instruções para Agentes de IA

Este documento define padrões e instruções básicas para agentes autônomos e assistentes de IA que operam neste repositório.

---

## 🎯 Objetivo
Garantir que as interações, alterações e automações realizadas por agentes mantenham a consistência, integridade e qualidade do repositório.

---

## 📋 Regras Gerais

1. **Escopo e Precisão**
   - Execute estritamente o que foi solicitado pelo usuário ou definido na tarefa.
   - Evite alterar arquivos ou refatorar códigos fora do escopo sem solicitação explícita.
   - Preserve formatações, comentários e documentações existentes.

2. **Segurança e Privacidade**
   - **Nunca** exponha credenciais, tokens, segredos de API ou informações sensíveis em arquivos, logs ou mensagens de commit.
   - Utilize variáveis de ambiente ou arquivos `.env` ignorados no `.gitignore`.

3. **Padrão de Código e Estrutura**
   - Respeite as convenções de estilo e formatação já presentes no projeto.
   - Mantenha caminhos e links relativos sempre que aplicável.

---

## 🔄 Fluxo de Git e Commits

- **Mensagens de Commit:**
  - Utilize mensagens claras, descritivas e objetivas (preferencialmente seguindo [Conventional Commits](https://www.conventionalcommits.org/)).
  - Exemplos:
    - `feat: adiciona nova automação para geração de métricas`
    - `fix: corrige caminho do asset no README`
    - `docs: adiciona diretrizes para agentes no agentes.md`
- **Verificação:**
  - Sempre verifique o status com `git status` e valide as alterações antes de commitar.
  - Não commite arquivos temporários, caches ou artefatos não rastreados.

---

## 🚀 Boas Práticas de Execução

- **Validação:** Valide a sintaxe e a integridade de qualquer script ou arquivo markdown gerado.
- **Transparência:** Documente resumidamente no PR ou na resposta o que foi modificado e o porquê.
