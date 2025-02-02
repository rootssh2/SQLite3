import sqlite3
import os
from typing import List, Tuple, Optional
from pathlib import Path
import platform
import re
from itertools import islice

class DatabaseError(Exception):
    pass

class FileError(Exception):
    pass

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_database()
    
    def _ensure_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    login TEXT NOT NULL,
                    senha TEXT NOT NULL
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_url ON credentials(url)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_login ON credentials(login)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_senha ON credentials(senha)')
    
    def insert_credentials_batch(self, credentials_generator, batch_size=1000):
        total_count = 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                while True:
                    batch = list(islice(credentials_generator, batch_size))
                    if not batch:
                        break
                    cursor.executemany(
                        'INSERT INTO credentials (url, login, senha) VALUES (?, ?, ?)',
                        batch
                    )
                    total_count += len(batch)
                    if total_count % 100000 == 0:
                        print(f"Processados {total_count} registros...")
                return total_count
        except sqlite3.Error as e:
            raise DatabaseError(f"Erro ao inserir credenciais: {str(e)}")

    def search_credentials(self, search_term: str, batch_size=1000):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT url, login, senha FROM credentials 
                    WHERE url LIKE ? OR login LIKE ? OR senha LIKE ?
                """, ('%' + search_term + '%',) * 3)
                
                while True:
                    results = cursor.fetchmany(batch_size)
                    if not results:
                        break
                    for row in results:
                        yield row
        except sqlite3.Error as e:
            raise DatabaseError(f"Erro na busca: {str(e)}")

class FileProcessor:
    @staticmethod
    def parse_lines_generator(file_obj):
        for line in file_obj:
            line = line.strip()
            if not line or line.startswith("Thank you for using"):
                continue

            for separator in [':', '|']:
                if separator in line:
                    parts = line.split(separator, 2)
                    if len(parts) >= 2:
                        url = parts[0].strip()
                        login = parts[1].strip()
                        senha = parts[2].strip() if len(parts) > 2 else ''
                        yield (url, login, senha)
                    break

    @staticmethod
    def process_large_file(filepath: str, encoding='utf-8', chunk_size=8192):
        try:
            with open(filepath, 'r', encoding=encoding, buffering=chunk_size) as file:
                yield from FileProcessor.parse_lines_generator(file)
        except UnicodeDecodeError:
            for alt_encoding in ['latin-1', 'utf-16', 'utf-16le', 'utf-16be']:
                try:
                    with open(filepath, 'r', encoding=alt_encoding, buffering=chunk_size) as file:
                        yield from FileProcessor.parse_lines_generator(file)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise FileError(f"Não foi possível determinar a codificação do arquivo: {filepath}")

    @staticmethod
    def clean_wordlist(content: str, tipo_filtro: str = 'padrao') -> List[str]:
        patterns = {
            'email': re.compile(r'[\w\.-]+@[\w\.-]+', re.IGNORECASE),
            'iptv': re.compile(r'([\w\.-]+)/get\.php\?username=([\w\d]+)&password=([\w\d]+)', re.IGNORECASE),
            'number': re.compile(r'^\+?\d+$'),
            'strong_password': re.compile(r'.{1,}')
        }

        cleaned_lines = []
        
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue

            parts = line.split(':')

            if tipo_filtro == 'email':
                for part in parts:
                    email_match = patterns['email'].search(part)
                    if email_match:
                        email = email_match.group(0)
                        email_index = parts.index(part)
                        if email_index < len(parts) - 1:
                            password = parts[email_index + 1].strip()
                            cleaned_lines.append(f"{email}:{password}")
                        break

            elif tipo_filtro == 'iptv':
                match = patterns['iptv'].search(line)
                if match:
                    username = match.group(2)
                    password = match.group(3)
                    cleaned_lines.append(f"{username}:{password}")

            elif tipo_filtro == 'number' and len(parts) >= 2:
                login = None
                senha = None
                
                for part in parts:
                    part = part.strip()
                    if patterns['number'].match(part):
                        login = part
                        idx = parts.index(part)
                        if idx < len(parts) - 1:
                            senha = parts[idx + 1].strip()
                            break
                
                if login and senha:
                    cleaned_lines.append(f"{login}:{senha}")

            elif tipo_filtro == 'login' and len(parts) >= 2:
                invalid_pattern = re.compile(r'UNKNOWN|NOT_SAVED|^[^:]+:ENC\d+\*', re.IGNORECASE)
                if not invalid_pattern.search(line):
                    senha = parts[-1].strip()
                    login = parts[-2].strip()
                    cleaned_lines.append(f"{login}:{senha}")

        return cleaned_lines

    @staticmethod
    def remove_duplicates(lines: List[str], separator: str = ':') -> List[str]:
        unique_lines = set()
        cleaned_lines = []
        
        for line in lines:
            if ':' in line:
                login, senha = line.split(':', 1)
                formatted_line = f"{login.strip()}{separator}{senha.strip()}"
                if formatted_line not in unique_lines:
                    unique_lines.add(formatted_line)
                    cleaned_lines.append(formatted_line)
        
        return cleaned_lines

class FileManager:
    ENCODINGS = [
        ('utf-8', '\n'), ('utf-8', '\r\n'), ('utf-8', '\r'),
        ('utf-16le', '\n'), ('utf-16le', '\r\n'), ('utf-16le', '\r'),
        ('utf-16be', '\n'), ('utf-16be', '\r\n'), ('utf-16be', '\r'),
        ('utf-32le', '\n'), ('utf-32le', '\r\n'), ('utf-32le', '\r'),
        ('utf-32be', '\n'), ('utf-32be', '\r\n'), ('utf-32be', '\r'),
        ('latin-1', '\n'), ('latin-1', '\r\n'), ('latin-1', '\r')
    ]

    @staticmethod
    def read_file(filepath: str) -> str:
        content = None
        errors = []

        for encoding, newline in FileManager.ENCODINGS:
            try:
                with open(filepath, 'r', encoding=encoding, newline=newline) as file:
                    content = file.read()
                    print(f"Arquivo lido com sucesso usando encoding: {encoding}, newline: {repr(newline)}")
                    return content
            except UnicodeError as e:
                errors.append(f"Erro com encoding {encoding}, newline {repr(newline)}: {str(e)}")
                continue
            except Exception as e:
                errors.append(f"Erro inesperado com encoding {encoding}, newline {repr(newline)}: {str(e)}")
                continue

        if content is None:
            error_msg = "\n".join(errors)
            raise FileError(f"Erro ao ler arquivo {filepath}. Tentativas:\n{error_msg}")

        return content

    @staticmethod
    def write_file(filepath: str, content: str):
        try:
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(content)
        except Exception as e:
            raise FileError(f"Erro ao escrever arquivo {filepath}: {str(e)}")

    @staticmethod
    def process_output_in_chunks(filepath: str, results_generator, chunk_size=1000):
        try:
            with open(filepath, 'w', encoding='utf-8', buffering=chunk_size) as file:
                for chunk in results_generator:
                    file.write(f"{chunk[0]}:{chunk[1]}:{chunk[2]}\n")
        except Exception as e:
            raise FileError(f"Erro ao escrever arquivo {filepath}: {str(e)}")

class CredentialsManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_dir = os.path.join(self.base_dir, 'txt_to_db')
        self.results_dir = os.path.join(self.base_dir, 'resultados')
        self.wordlist_dir = os.path.join(self.base_dir, 'wordlist')
        
        for directory in [self.db_dir, self.results_dir, self.wordlist_dir]:
            os.makedirs(directory, exist_ok=True)
        
        self.db_path = os.path.join(self.db_dir, 'dados.db')
        self.db_manager = DatabaseManager(self.db_path)

    def process_txt_file(self, filepath: str) -> int:
        try:
            credentials_generator = FileProcessor.process_large_file(filepath)
            count = self.db_manager.insert_credentials_batch(credentials_generator)
            print(f"{count} registros de {os.path.basename(filepath)} foram inseridos com sucesso.")
            return count
        except (FileError, DatabaseError) as e:
            print(f"Erro ao processar {os.path.basename(filepath)}: {str(e)}")
            return 0

    def search_and_save(self, search_term: str):
        try:
            output_path = os.path.join(self.results_dir, f"{search_term}.txt")
            results_generator = self.db_manager.search_credentials(search_term)
            FileManager.process_output_in_chunks(output_path, results_generator)
            print(f"Resultados salvos em: {output_path}")
        except (DatabaseError, FileError) as e:
            print(f"Erro na busca: {str(e)}")

    def clean_wordlist_file(self, input_path: str, output_name: str, tipo_filtro: str = 'padrao', separator: str = ':'):
        try:
            content = FileManager.read_file(input_path)
            cleaned_lines = FileProcessor.clean_wordlist(content, tipo_filtro)
            final_lines = FileProcessor.remove_duplicates(cleaned_lines, separator)
            output_path = os.path.join(self.wordlist_dir, output_name)
            FileManager.write_file(output_path, '\n'.join(final_lines))
            print(f"Arquivo limpo salvo em: {output_path}")
            print(f"Total de linhas processadas: {len(final_lines)}")
        except FileError as e:
            print(f"Erro ao limpar wordlist: {str(e)}")

    def process_all_txt_files(self) -> int:
        total_count = 0
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='credentials'")
                if cursor.fetchone() is None:
                    print("Tabela 'credentials' não existe. Criando...")
                    self.db_manager._ensure_database()
                else:
                    print("Tabela 'credentials' já existe.")
        except sqlite3.Error as e:
            print(f"Erro ao conectar ou verificar tabela no banco de dados: {str(e)}")
            return 0

        txt_files = [f for f in os.listdir(self.db_dir) if f.endswith('.txt')]
        for file in txt_files:
            filepath = os.path.join(self.db_dir, file)
            count = self.process_txt_file(filepath)
            total_count += count
        print(f"Total de registros inseridos: {total_count}")
        input("\nPressione Enter para continuar...")
        return total_count

def clear_screen():
    os_name = platform.system().lower()
    if os_name == 'windows':
        os.system('cls')
    else:
        os.system('clear')

def print_blue_banner():
    banner_text = '''
   _____ ____    __    _ __      _____
  / ___// __ \  / /   (_) /____ |__  /
  \__ \/ / / / / /   / / __/ _ \ /_ < 
 ___/ / /_/ / / /___/ / /_/  __/__/ / 
/____/\___\_\/_____/_/\__/\___/____/ V6 
                                      
 Telegram: https://t.me/Root2022'''
    print("\033[94m" + banner_text + "\033[0m")

def main():
    manager = CredentialsManager()
    while True:
        clear_screen()
        print_blue_banner()
        print("\nMenu Principal:")
        print("\033[94m[1]\033[0m. Adicionar arquivos .txt ao DB")
        print("\033[94m[2]\033[0m. Consultar logins")
        print("\033[94m[3]\033[0m. Limpar wordlist")
        print("\033[94m[4]\033[0m. Sair")
        
        escolha = input("Escolha uma opção: ").strip()
        
        if escolha == '1':
            txt_files = [f for f in os.listdir(manager.db_dir) if f.endswith('.txt')]
            if not txt_files:
                print("Nenhum arquivo .txt encontrado.")
                input("\nPressione Enter para continuar...")
                continue
            
            print("\nArquivos disponíveis:")
            for i, file in enumerate(txt_files, 1):
                print(f"{i}. {file}")
            
            escolha_arquivo = input("Digite o número do arquivo ou 'todos': ").strip()
            
            if escolha_arquivo.lower() == 'todos':
                manager.process_all_txt_files()
            else:
                try:
                    idx = int(escolha_arquivo) - 1
                    if 0 <= idx < len(txt_files):
                        filepath = os.path.join(manager.db_dir, txt_files[idx])
                        count = manager.process_txt_file(filepath)
                        if count > 0:
                            print(f"{count} registros de {txt_files[idx]} foram inseridos com sucesso.")
                        else:
                            print("Nenhum registro foi inserido.")
                        input("\nPressione Enter para continuar...")
                    else:
                        print("Número de arquivo inválido.")
                        input("\nPressione Enter para continuar...")
                except ValueError:
                    print("Entrada inválida. Por favor, escolha um número válido ou 'todos'.")
                    input("\nPressione Enter para continuar...")
        
        elif escolha == '2':
            termo_busca = input("Digite o termo de busca: ").strip()
            if termo_busca:
                manager.search_and_save(termo_busca)
                input("\nPressione Enter para continuar...")
        
        elif escolha == '3':
            arquivos = [f for f in os.listdir(manager.results_dir) if f.endswith('.txt')]
            if not arquivos:
                print("Nenhum arquivo .txt encontrado.")
                input("\nPressione Enter para continuar...")
                continue
            
            print("\nArquivos disponíveis:")
            for i, arquivo in enumerate(arquivos, 1):
                print(f"{i}. {arquivo}")
            
            try:
                idx = int(input("Escolha o arquivo para limpar: ").strip()) - 1
                if 0 <= idx < len(arquivos):
                    input_path = os.path.join(manager.results_dir, arquivos[idx])
                    print("\nEscolha o tipo de filtro:")
                    print("\033[94m[1]\033[0m Email")
                    print("\033[94m[2]\033[0m Iptv")
                    print("\033[94m[3]\033[0m Number")
                    print("\033[94m[4]\033[0m Login")
                    print("\033[94m[0]\033[0m Voltar ao menu")
                    
                    opcao_filtro = input("Digite o número da opção: ").strip()
                    
                    if opcao_filtro == '0':
                        continue

                    tipo_filtro = {
                        '1': 'email',
                        '2': 'iptv',
                        '3': 'number',
                        '4': 'login'
                    }.get(opcao_filtro, 'email')  
                    
                    separador = input("Separador (: ou |, deixe em branco para padrão ':'): ").strip() or ':'
                    output_name = f"limpo_{arquivos[idx]}"
                    manager.clean_wordlist_file(input_path, output_name, tipo_filtro, separador)
                    input("\nPressione Enter para continuar...")
            except ValueError:
                print("Entrada inválida.")
                input("\nPressione Enter para continuar...")
        
        elif escolha == '4':
            break
        
        else:
            print("Opção inválida.")
            input("\nPressione Enter para continuar...")

if __name__ == "__main__":
    main()