# Piloto controlado — ainda não autorizado para dados reais

Entrada: zerar bloqueadores do checklist, provar persistência no serviço escolhido, restore do ambiente-alvo, HTTPS, segredo privado, contas individuais, CSRF/autorização, estoque consistente e testes verdes. Resultado local ou POC não equivale a cumprir estes critérios na clínica.

Proposta a validar com responsáveis: duas contas individuais (admin e veterinária), treinamento com dados fictícios, depois duas semanas de piloto de escopo pequeno. Manter o processo anterior em paralelo e reconciliação diária; não depender exclusivamente do UniVet durante o piloto.

Backup diário e antes de manutenção, com cópias fora da instância; testar restauração antes do primeiro dado real e semanalmente no piloto. Nomear responsável por backup, suporte e decisão clínica. Registrar bugs com versão, horário e passos redigidos; feedback sem dados identificáveis em issue pública.

Interromper escrita real se houver perda/divergência de saldo ou prontuário, acesso indevido, falta de backup válido, indisponibilidade que prejudique atendimento ou bloqueador de segurança. Preservar evidências e usar plano de incidente.

Critério de saída proposto: período acordado concluído, sem bloqueadores e sem divergência não resolvida, feedback formal da clínica, responsáveis/rotina de backup estabelecidos e recuperação ensaiada. Somente então avaliar “apto para uso operacional”. Datas, metas de disponibilidade, prazo de recuperação e perda tolerável precisam ser acordados; não inventar aprovação da clínica.
