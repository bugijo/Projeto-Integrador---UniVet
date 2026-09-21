# Privacidade — inventário técnico e pendências

## Separação de ambientes — 21/09/2026

**DEMO = somente dados fictícios. PRODUÇÃO = futura base exclusiva da clínica, ainda não liberada.** Código compartilhado não implica compartilhar dados: serviços/URLs, bancos, chaves, usuários, cookies e backups distintos. Não importar dumps da clínica em desenvolvimento/demo, nem usar registros reais em testes, screenshots ou relatórios. A marca interna recusa abrir banco de outro ambiente; operadores continuam responsáveis por não copiar dados manualmente entre bases.

DrFernanda não criada. Senha temporária futura somente no terminal interativo não gravado do administrador e entrega privada; nunca neste documento/chat/Git/log. Primeiro acesso exige troca. Contas desativadas preservam autoria. Consultas canceladas não são apagadas; condições clínicas e atendimentos concluídos impedem exclusões perigosas. Edição/adendos e retenção continuam exigindo política clínica.

Sem destino externo de backup, responsáveis e recuperação do alvo confirmados, SEC-15 permanece pendente. Dados pessoais continuam minimizados nos logs técnicos; documentação não constitui conformidade jurídica ou autorização de uso real.

## Inventário técnico original

19/09/2026, base `95d1369`. Documento de engenharia, não parecer jurídico. Revisão usa schema/código e dados fictícios; não inspeciona registros reais.

| Dado | Finalidade | Obrigatório? | Onde fica | Acesso | Log? | Exportado? | Retenção sugerida |
|---|---|---|---|---|---|---|---|
| Nome/CPF/telefone tutor | Identificação e contato | Sim no cadastro atual; necessidade de CPF deve ser discutida | SQLite, forms e histórico | Admin/veterinária da mesma clínica | Não em log técnico; pode constar de histórico | Sem CSV específico atual | Definir com clínica/orientador; minimizar CPF |
| Endereço tutor | Atendimento domiciliar | Não | Cadastro/histórico | Equipe autorizada | Histórico, não log técnico | Não necessário à API de estoque | Coletar apenas quando necessário; definir revisão |
| Pet, consultas, diagnóstico, condições | Continuidade clínica | Vínculo obrigatório; textos opcionais | SQLite/prontuário/histórico | Admin/veterinária | Histórico é parte do registro | CSV de movimentos pode incluir nome do pet | Política clínica de preservação/adendos a definir |
| Login/nome/perfil/hash | Conta individual e autoria | Sim | Banco, sessão assinada e eventos | Usuário próprio/operador de contas; equipe vê autoria | Eventos contêm ID/ação, não senha | Autoria em movimentações | Desativar preservando autoria; prazo a definir |
| E-mail/telefone/documento fornecedor | Contato comercial | Nome obrigatório; demais opcionais | Banco/cadastro | Equipe; admin altera | Não intencionalmente | API de estoque não exporta cadastro completo | Revisar relevância e necessidade |
| Preços e movimentos | Rastrear estoque e consumo | Quantidades/vínculos obrigatórios | Banco/API/CSV | Equipe lê; admin exporta/cadastra/ajusta/estorna | Movimentação rastreável | Sim, CSV e API | Conciliar com política administrativa |
| Histórico JSON | Rastreabilidade | Automático em operações cobertas | Banco | Equipe autorizada | É registro persistente, não log técnico | Não em CSV específico | Excluir cadastro não elimina histórico; definir regra |
| Cópias e exportações | Recuperação/relatórios | Backup necessário para uso real | Destino externo à instância | Responsável designado | Só metadados de operação/hash | Compartilhar privadamente | Proposta 7 diárias/4 semanais; validar minimização |
| Requisições de fontes Google | Tipografia | Não essencial à função | Navegador/terceiro | Provedor da fonte | Provedor pode registrar requisição | Não pelo UniVet | Considerar fonte local e discutir terceiro |

Antes do uso real, a clínica deve definir responsável, finalidade, base aplicável de tratamento, quem acessa, canal de solicitações, prazo de retenção por tipo, tratamento de backups e processo de incidentes. Não inventar prazos legais. Alunos devem usar dados fictícios em desenvolvimento, testes, screenshots, issues e relatórios públicos.

Evitar senhas, tokens, cookies e conteúdo clínico em logs. Em evidências de falha, registrar identificadores fictícios, endpoint, horário e erro técnico redigido. Artefatos brutos estão ignorados e não devem ser publicados automaticamente. Verificar restrições de acesso no local onde backups forem armazenados.

Pendências técnicas relacionadas: sessão/autorizações (SEC-03), cache e cookies (SEC-07), cópia/restore (SEC-10/15), retenção de histórico (SEC-13). Exposição do conteúdo dos PDFs antigos não foi analisada; presença no Git foi comprovada em SEC-12. Qualquer avaliação do conteúdo deve ocorrer privadamente.
