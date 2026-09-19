"""Administração local explícita; senhas somente por prompt privado."""
import argparse
import getpass
from pathlib import Path
import sqlite3

from security import password_hash


def manage(database, action, login, name='', role='veterinaria', password=None):
    path = Path(database).resolve()
    if not path.is_file():
        raise ValueError('Banco inexistente. Execute a migração explicitamente primeiro.')
    if role not in ('admin', 'veterinaria') or not login.strip() or len(login) > 100:
        raise ValueError('Usuário ou perfil inválido.')
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    try:
        conn.execute('BEGIN IMMEDIATE')
        user = conn.execute('SELECT * FROM usuarios WHERE login=?', (login,)).fetchone()
        if action in ('bootstrap', 'create-user'):
            if action == 'bootstrap' and conn.execute("SELECT 1 FROM usuarios WHERE perfil='admin' AND ativo=1").fetchone():
                raise ValueError('Já existe administrador ativo.')
            if user:
                raise ValueError('Usuário já existe; nenhuma alteração realizada.')
            cursor = conn.execute('INSERT INTO usuarios(login,nome,perfil,senha_hash,ativo,must_change_password) VALUES (?,?,?,?,1,?)',
                                 (login, name.strip() or login, 'admin' if action == 'bootstrap' else role,
                                  password_hash(password or ''), int(action != 'bootstrap')))
            user_id = cursor.lastrowid
        else:
            if not user:
                raise ValueError('Usuário inexistente.')
            user_id = user['id']
            if action == 'deactivate':
                if user['ativo'] and user['perfil'] == 'admin' and conn.execute("SELECT count(*) FROM usuarios WHERE perfil='admin' AND ativo=1").fetchone()[0] <= 1:
                    raise ValueError('Não desative o último administrador ativo.')
                conn.execute('UPDATE usuarios SET ativo=0,session_version=session_version+1 WHERE id=?', (user_id,))
            elif action == 'reset-password':
                conn.execute('UPDATE usuarios SET senha_hash=?,session_version=session_version+1,must_change_password=1 WHERE id=?',
                             (password_hash(password or ''), user_id))
            else:
                raise ValueError('Operação inválida.')
            conn.execute('DELETE FROM auth_sessions WHERE usuario_id=?', (user_id,))
        conn.execute('INSERT INTO security_events(usuario_id,evento) VALUES (?,?)', (user_id, 'local-cli:' + action))
        conn.commit()
        return user_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Operador local confiável; nenhum acesso remoto. Senhas não são argumentos.')
    parser.add_argument('--database', required=True)
    parser.add_argument('action', choices=['bootstrap','create-user','reset-password','deactivate'])
    parser.add_argument('--login', required=True)
    parser.add_argument('--name', default='')
    parser.add_argument('--role', choices=['admin','veterinaria'], default='veterinaria')
    args = parser.parse_args()
    password = None
    if args.action != 'deactivate':
        password = getpass.getpass('Senha privada (mínimo 12 caracteres): ')
        if password != getpass.getpass('Confirme: '):
            parser.error('Senhas não conferem.')
    try:
        manage(args.database, args.action, args.login, args.name, args.role, password)
    except (ValueError, sqlite3.Error):
        parser.exit(1, 'Operação recusada. Confira usuário, política de senha e schema do banco; nada foi confirmado.\n')
    print('Operação concluída. Senha não registrada em log.')


if __name__ == '__main__':
    main()
