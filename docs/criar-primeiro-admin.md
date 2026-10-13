# Conta individual — procedimento preparado

Estado: 21/09/2026. **Não criar conta real enquanto a clínica não estiver homologada.** DrFernanda não criada.

Procedimento atualizado e comandos em [runbook-producao.md](runbook-producao.md#contas-e-primeiro-acesso). Configurar explicitamente ambiente e banco novo; produção nunca recebe seed demo.

`admin_cli.py` gera senha temporária aleatória de 32 caracteres (24 bytes de entropia), armazenada somente como hash Werkzeug. Bootstrap, criação e reset exigem troca. Senha não é argumento e não é mais solicitada por getpass. O comando recusa stdout/stdin não interativos; mostra o segredo uma vez no terminal do operador. Não usar terminal gravado, screenshots, tee ou sessão do agente para gerar a senha real.

Na aplicação: senha atual + nova + confirmação; 12–128 caracteres, pelo menos 6 distintos, frases-senha permitidas. Não pode repetir a temporária. Primeiro acesso troca, revoga sessões anteriores, rotaciona sessão e abre dashboard. Reset concorrente não pode ser sobrescrito por uma troca que começou antes dele.

Admin faz cadastros/estoque/exportações/operações administrativas. Veterinária consulta pacientes, agenda/prontuário e registra uso de produtos; autorização no servidor. Administração de contas fica na CLI local confiável, não existe painel remoto de usuários.

Criação recusa duplicidade; bootstrap recusa se já existe administrador ativo; desativação não remove autoria nem permite desativar último admin. Não há recuperação por e-mail/serviço pago. Rotação de SECRET_KEY invalida cookies. Cada ambiente deve ter segredo e banco próprios.
