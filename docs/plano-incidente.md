# Plano de incidentes — proposta operacional

Acionar o responsável da clínica e um responsável técnico; nomes e contatos devem ficar em canal privado. Registrar horário, versão afetada, tipo de incidente e medidas, sem CPF/prontuário/senha/cookie. Não publicar evidências brutas em GitHub.

| Incidente | Contenção autorizada | Recuperação e verificação |
|---|---|---|
| Senha vazada/conta comprometida | Desativar conta ou reset privado por CLI; sessões são revogadas | Conferir eventos e operações do período, emitir senha temporária privada, exigir troca |
| SECRET_KEY vazada | Trocar segredo no ambiente do serviço mediante autorização | Todos precisam entrar novamente; revisar origem da exposição e cópias no Git/logs |
| Banco perdido | Suspender escrita e preservar instância/artefatos existentes | Restaurar cópia validada para destino novo; conferir contagens, FKs, saldo e prontuário antes de trocar conexão |
| Sistema indisponível | Voltar ao processo anterior da clínica | Checar serviço/commit/logs e banco; rollback de código somente com schema compatível |
| Dado alterado indevidamente | Preservar histórico e restringir conta suspeita | Conciliar registros com responsável clínico; correção rastreada, sem editar banco às cegas |
| Backup falhou | Alertar responsável e não considerar operação recuperável | Reparar destino/permissões, produzir cópia e testar restore; registrar janela sem cobertura |
| Arquivo privado no histórico Git | Restringir compartilhamento e inventariar refs/cópias | Planejar saneamento com autorização específica; commit de exclusão não remove versões antigas |

Encerrar incidente somente após evidências preservadas, causa identificada, correção testada e decisão dos responsáveis. Comunicação com titulares/autoridades e análise de LGPD requerem orientação adequada; não são automatizadas por este projeto. Não há promessa de recuperação de dados não presentes em backup ou trilha disponível.
