# Superfície de ataque — estado corrigido local

Base original: `95d1369`; branch `chore/contexto-auditoria-producao`. Mapa gerado a partir de url_map e política central em security.py. Mesma clínica: admin e veterinária compartilham leitura clínica; não há multi-tenant ou isolamento por veterinário. Identificadores não substituem permissão de operação.

| Rota | Método | Acesso | Perfil | Operação | Dados pessoais/clínicos? | CSRF | Rate limit | Observação |
|---|---|---|---|---|---|---|---|---|
| / | GET,POST | Pública | — | Leitura/escrita | Não diretamente | Token no POST | 20/IP e 10/conta a cada 15 min (POST) | Cookie/sessão |
| /api/disponibilidade | GET | Autenticada | Admin/veterinária | Leitura | Não diretamente | N/A | 180/min/usuário | ID inexistente não concede privilégio |
| /api/estoque/movimentacoes | GET | Autenticada | Admin/veterinária | Leitura | Sim | N/A | 180/min/usuário | ID inexistente não concede privilégio |
| /api/estoque/produtos | GET | Autenticada | Admin/veterinária | Leitura | Não diretamente | N/A | 180/min/usuário | ID inexistente não concede privilégio |
| /api/estoque/resumo | GET | Autenticada | Admin/veterinária | Leitura | Não diretamente | N/A | 180/min/usuário | ID inexistente não concede privilégio |
| /api/racas | GET | Autenticada | Admin/veterinária | Leitura | Não diretamente | N/A | 180/min/usuário | ID inexistente não concede privilégio |
| /consultas | GET | Autenticada | Admin/veterinária | Leitura | Sim | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /consultas/<int:consulta_id>/editar | GET,POST | Autenticada | Admin/veterinária | Leitura/escrita | Sim | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /consultas/<int:consulta_id>/excluir | POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Sim | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /consultas/<int:consulta_id>/produtos | POST | Autenticada | Admin/veterinária | Leitura/escrita | Sim | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /consultas/dia/<data_iso> | GET | Autenticada | Admin/veterinária | Leitura | Sim | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /consultas/nova | GET,POST | Autenticada | Admin/veterinária | Leitura/escrita | Sim | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /conta/senha | GET,POST | Autenticada | Admin/veterinária | Leitura/escrita | Sim | Token no POST | 5/15min | ID inexistente não concede privilégio |
| /estoque | GET | Autenticada | Admin/veterinária | Leitura | Não diretamente | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/categorias | GET,POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/categorias/<int:categoria_id>/alternar | POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/categorias/<int:categoria_id>/editar | GET,POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/exportar/consumo.csv | GET | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura | Não diretamente | N/A | 10/min/usuário | ID inexistente não concede privilégio |
| /estoque/exportar/movimentacoes.csv | GET | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura | Sim | N/A | 10/min/usuário | ID inexistente não concede privilégio |
| /estoque/exportar/posicao.csv | GET | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura | Não diretamente | N/A | 10/min/usuário | ID inexistente não concede privilégio |
| /estoque/fornecedores | GET,POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/fornecedores/<int:fornecedor_id>/alternar | POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/fornecedores/<int:fornecedor_id>/editar | GET,POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/lotes | GET | Autenticada | Admin/veterinária | Leitura | Não diretamente | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/lotes/<int:lote_id>/ajuste | GET,POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/lotes/entrada | GET,POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/movimentacoes | GET | Autenticada | Admin/veterinária | Leitura | Sim | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/movimentacoes/<int:movimentacao_id>/estornar | POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Sim | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/produtos | GET | Autenticada | Admin/veterinária | Leitura | Não diretamente | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/produtos/<int:produto_id> | GET | Autenticada | Admin/veterinária | Leitura | Não diretamente | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/produtos/<int:produto_id>/alternar | POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/produtos/<int:produto_id>/editar | GET,POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/produtos/novo | GET,POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/relatorios | GET | Autenticada | Admin/veterinária | Leitura | Não diretamente | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /estoque/saidas | GET,POST | Autenticada | Admin/veterinária | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /health | GET | Pública | — | Leitura | Não diretamente | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /historico/<entidade>/<int:registro_id> | GET | Autenticada | Admin/veterinária | Leitura | Sim | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /login | GET,POST | Pública | — | Leitura/escrita | Não diretamente | Token no POST | 20/IP e 10/conta a cada 15 min (POST) | Cookie/sessão |
| /logout | POST | Autenticada | Admin/veterinária | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /pagina-inicial | GET | Autenticada | Admin/veterinária | Leitura | Não diretamente | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /pets | GET | Autenticada | Admin/veterinária | Leitura | Sim | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /pets/<int:pet_id>/condicoes | POST | Autenticada | Admin/veterinária | Leitura/escrita | Sim | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /pets/<int:pet_id>/editar | GET,POST | Autenticada | Admin/veterinária | Leitura/escrita | Sim | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /pets/<int:pet_id>/excluir | POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Sim | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /pets/<int:pet_id>/historico-clinico | GET | Autenticada | Admin/veterinária | Leitura | Sim | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /pets/novo | GET,POST | Autenticada | Admin/veterinária | Leitura/escrita | Sim | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /servicos | GET | Autenticada | Admin/veterinária | Leitura | Não diretamente | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /servicos/<int:servico_id>/editar | GET,POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /servicos/<int:servico_id>/excluir | POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /static/<path:filename> | GET | Pública | — | Leitura | Não diretamente | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /tutores | GET | Autenticada | Admin/veterinária | Leitura | Sim | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /tutores/<int:tutor_id>/editar | GET,POST | Autenticada | Admin/veterinária | Leitura/escrita | Sim | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /tutores/<int:tutor_id>/excluir | POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Sim | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /tutores/novo | GET,POST | Autenticada | Admin/veterinária | Leitura/escrita | Sim | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /veterinarios | GET | Autenticada | Admin/veterinária | Leitura | Não diretamente | N/A | Sem limite específico | ID inexistente não concede privilégio |
| /veterinarios/<int:veterinario_id>/editar | GET,POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |
| /veterinarios/<int:veterinario_id>/excluir | POST | Autenticada | Admin nas escritas/exportação; ambos na leitura | Leitura/escrita | Não diretamente | Token no POST | Sem limite específico | ID inexistente não concede privilégio |

HEAD acompanha GET. OPTIONS não habilita CORS. Sessão expirada, revogada ou desativada não autoriza: API retorna 401; HTML redireciona login. Reset administrativo exige troca de senha antes de acessar dados. Testes de IDOR cobrem alteração de IDs em operações administrativas por veterinária. Revisão de botões é UX; permissão é aplicada no servidor.
