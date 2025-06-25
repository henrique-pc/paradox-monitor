import time
import os
import requests
import json
import hashlib
import pyodbc
from datetime import datetime
from typing import Dict, List, Any, Optional

class ParadoxReader:
    """Classe para ler dados do Paradox via ODBC"""
    
    def __init__(self, db_directory: str):
        self.db_directory = db_directory
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Estabelece conexão ODBC com Paradox"""
        connection_strings = [
            f"Driver={{Microsoft Paradox Driver (*.db )}};DefaultDir={self.db_directory};",
            f"Driver={{Microsoft dBASE Driver (*.dbf)}};DefaultDir={self.db_directory};",
            f"DRIVER={{Microsoft Paradox Driver (*.db )}};DBQ={self.db_directory};",
        ]
        
        for conn_str in connection_strings:
            try:
                # Ao invés de:
                # self.connection = pyodbc.connect(conn_str)

                # Teste:
                try:
                self.connection = pyodbc.connect(conn_str, autocommit=False)
                except:
                # Fallback sem parâmetros
                self.connection = pyodbc.connect(conn_str)
                # Fim do Teste
            
                print(f"✅ Conectado via ODBC: {self.db_directory}")
                return
            except Exception as e:
                continue
        
        raise Exception(f"Não foi possível conectar ao diretório: {self.db_directory}")
    
    def read_table(self, table_name: str, where_clause: str = "") -> List[Dict]:
        """Lê todos os registros de uma tabela"""
        if not self.connection:
            self._connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Tenta diferentes formatos de nome da tabela
            table_formats = [table_name, f"{table_name}.db", f'"{table_name}"']
            
            for table_format in table_formats:
                try:
                    query = f"SELECT * FROM {table_format}"
                    if where_clause:
                        query += f" WHERE {where_clause}"
                    
                    cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    
                    records = []
                    for row in cursor.fetchall():
                        records.append(dict(zip(columns, row)))
                    
                    return records
                    
                except Exception as e:
                    continue
            
            raise Exception(f"Não foi possível ler a tabela: {table_name}")
            
        except Exception as e:
            print(f"Erro ao ler tabela {table_name}: {e}")
            return []
    
    def read_single_record(self, table_name: str, key_field: str, key_value: Any) -> Optional[Dict]:
        """Lê um único registro baseado em chave"""
        where_clause = f"{key_field} = '{key_value}'" if isinstance(key_value, str) else f"{key_field} = {key_value}"
        records = self.read_table(table_name, where_clause)
        return records[0] if records else None
    
    def close(self):
        """Fecha conexão"""
        if self.connection:
            self.connection.close()

class EnhancedParadoxMonitor:
    def __init__(self, config: Dict):
        """
        config = {
            'main_table': {
                'directory': 'C:/path/to/main',
                'name': 'contratos',
                'primary_key': 'id',
                'file_path': 'C:/path/to/main/contratos.db'
            },
            'related_tables': [
                {
                    'directory': 'C:/path/to/clients',
                    'name': 'clientes',
                    'join_field': 'codigo_cliente',  # campo na tabela principal
                    'key_field': 'codigo',           # campo na tabela relacionada
                    'fields_to_include': ['nome', 'telefone', 'email'],
                    'alias': 'cliente'
                }
            ],
            'webhook_url': 'https://seu-endpoint.com/webhook',
            'check_interval': 5
        }
        """
        self.config = config
        self.main_reader = ParadoxReader(config['main_table']['directory'])
        self.related_readers = {}
        
        # Inicializa readers para tabelas relacionadas
        for related in config['related_tables']:
            dir_path = related['directory']
            if dir_path not in self.related_readers:
                self.related_readers[dir_path] = ParadoxReader(dir_path)
        
        self.last_snapshot = {}
        self.last_file_modified = 0
        
        # Carrega snapshot inicial
        self.update_snapshot()
    
    def get_record_hash(self, record: Dict) -> str:
        """Cria hash de um registro para detectar mudanças"""
        record_str = json.dumps(record, sort_keys=True, default=str)
        return hashlib.md5(record_str.encode()).hexdigest()
    
    def enrich_record(self, record: Dict) -> Dict:
        """Enriquece um registro com dados de tabelas relacionadas"""
        enriched = record.copy()
        
        for related_config in self.config['related_tables']:
            try:
                # Pega o valor da chave de join
                join_value = record.get(related_config['join_field'])
                if not join_value:
                    continue
                
                # Busca registro relacionado
                reader = self.related_readers[related_config['directory']]
                related_record = reader.read_single_record(
                    related_config['name'],
                    related_config['key_field'],
                    join_value
                )
                
                if related_record:
                    # Adiciona campos especificados
                    alias = related_config['alias']
                    enriched[alias] = {}
                    
                    for field in related_config['fields_to_include']:
                        if field in related_record:
                            enriched[alias][field] = related_record[field]
                
            except Exception as e:
                print(f"Erro ao enriquecer registro com {related_config['alias']}: {e}")
                continue
        
        return enriched
    
    def update_snapshot(self):
        """Atualiza o snapshot atual dos dados"""
        try:
            main_config = self.config['main_table']
            records = self.main_reader.read_table(main_config['name'])
            
            self.last_snapshot = {}
            
            for record in records:
                key = str(record.get(main_config['primary_key'], ''))
                if key:
                    # Enriquece o registro com dados relacionados
                    enriched_record = self.enrich_record(record)
                    
                    self.last_snapshot[key] = {
                        'data': enriched_record,
                        'hash': self.get_record_hash(record)  # Hash só do registro principal
                    }
            
            self.last_file_modified = os.path.getmtime(main_config['file_path'])
            print(f"Snapshot atualizado: {len(self.last_snapshot)} registros enriquecidos")
            
        except Exception as e:
            print(f"Erro ao atualizar snapshot: {e}")
    
    def detect_changes(self) -> Dict[str, List]:
        """Detecta mudanças detalhadas nos dados"""
        try:
            main_config = self.config['main_table']
            
            # Verifica se arquivo foi modificado
            current_modified = os.path.getmtime(main_config['file_path'])
            if current_modified <= self.last_file_modified:
                return {'new': [], 'modified': [], 'deleted': []}
            
            # Lê dados atuais
            current_records = self.main_reader.read_table(main_config['name'])
            current_snapshot = {}
            
            for record in current_records:
                key = str(record.get(main_config['primary_key'], ''))
                if key:
                    # Enriquece o registro com dados relacionados
                    enriched_record = self.enrich_record(record)
                    
                    current_snapshot[key] = {
                        'data': enriched_record,
                        'hash': self.get_record_hash(record)  # Hash só do registro principal
                    }
            
            # Detecta mudanças
            changes = {
                'new': [],
                'modified': [],
                'deleted': []
            }
            
            # Novos registros
            for key, record_info in current_snapshot.items():
                if key not in self.last_snapshot:
                    changes['new'].append(record_info['data'])
            
            # Registros modificados
            for key, record_info in current_snapshot.items():
                if (key in self.last_snapshot and 
                    record_info['hash'] != self.last_snapshot[key]['hash']):
                    changes['modified'].append({
                        'old': self.last_snapshot[key]['data'],
                        'new': record_info['data'],
                        'key': key
                    })
            
            # Registros deletados
            for key, record_info in self.last_snapshot.items():
                if key not in current_snapshot:
                    changes['deleted'].append(record_info['data'])
            
            # Atualiza snapshot
            self.last_snapshot = current_snapshot
            self.last_file_modified = current_modified
            
            return changes
            
        except Exception as e:
            print(f"Erro ao detectar mudanças: {e}")
            return {'new': [], 'modified': [], 'deleted': []}
    
    def send_webhook(self, changes: Dict[str, List]):
        """Envia webhook com as mudanças detectadas (dados enriquecidos)"""
        if not any(changes.values()):
            return  # Nenhuma mudança
        
        payload = {
            'timestamp': datetime.now().isoformat(),
            'database': self.config['main_table']['name'],
            'changes': {
                'summary': {
                    'new_records': len(changes['new']),
                    'modified_records': len(changes['modified']),
                    'deleted_records': len(changes['deleted'])
                },
                'details': changes
            }
        }
        
        try:
            response = requests.post(
                self.config['webhook_url'], 
                json=payload, 
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f"Webhook enviado: {response.status_code}")
            print(f"Resumo: {payload['changes']['summary']}")
            
            if response.status_code != 200:
                print(f"Erro no webhook: {response.text}")
                
        except Exception as e:
            print(f"Erro ao enviar webhook: {e}")
    
    def run(self):
        """Executa o monitoramento contínuo"""
        main_table = self.config['main_table']['name']
        print(f"Iniciando monitoramento enriquecido de: {main_table}")
        print(f"Tabelas relacionadas: {[r['alias'] for r in self.config['related_tables']]}")
        print(f"Intervalo: {self.config['check_interval']}s")
        print(f"Webhook: {self.config['webhook_url']}")
        print("-" * 50)
        
        while True:
            try:
                changes = self.detect_changes()
                
                if any(changes.values()):
                    self.send_webhook(changes)
                else:
                    print(".", end="", flush=True)  # Indica que está funcionando
                
                time.sleep(self.config['check_interval'])
                
            except KeyboardInterrupt:
                print("\nMonitoramento interrompido pelo usuário")
                break
            except Exception as e:
                print(f"Erro no monitoramento: {e}")
                time.sleep(self.config['check_interval'])
    
    def close(self):
        """Fecha todas as conexões"""
        self.main_reader.close()
        for reader in self.related_readers.values():
            reader.close()

# Exemplo de uso
if __name__ == "__main__":
    import sys
    import os
    
    # Tenta carregar config.json do mesmo diretório do executável
    if getattr(sys, 'frozen', False):
        # Executável
        application_path = os.path.dirname(sys.executable)
    else:
        # Script Python
        application_path = os.path.dirname(__file__)
    
    config_path = os.path.join(application_path, 'config.json')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Arquivo de configuração não encontrado: {config_path}")
        print("Criando arquivo de exemplo...")
        
        # Cria config de exemplo
        exemplo_config = {
            "main_table": {
                "directory": "C:/dados/contratos",
                "name": "contratos", 
                "primary_key": "id",
                "file_path": "C:/dados/contratos/contratos.db"
            },
            "related_tables": [],
            "webhook_url": "https://seu-endpoint.com/webhook",
            "check_interval": 5
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(exemplo_config, f, indent=2, ensure_ascii=False)
        
        print(f"Configure o arquivo {config_path} e execute novamente.")
        input("Pressione Enter para sair...")
        sys.exit(1)
    
    # Inicia monitoramento
    monitor = EnhancedParadoxMonitor(config)

# Opção 1 - Autocommit Falso
def connect_to_paradox(directory):
    conn_str = f"DRIVER={{Microsoft Paradox Driver (*.db )}};DBQ={directory};"
    
    try:
        # Conectar SEM autocommit automático
        connection = pyodbc.connect(conn_str, autocommit=False)
        print("✅ Conexão bem-sucedida!")
        return connection
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return None
# Fim Opção 1

# Opção 2
def connect_to_paradox_manual(directory):
    conn_str = f"DRIVER={{Microsoft Paradox Driver (*.db )}};DBQ={directory};"
    
    try:
        # Conectar sem configurações automáticas
        connection = pyodbc.connect(conn_str)
        
        # Configurar manualmente se necessário
        # connection.autocommit = False  # Só se necessário
        
        print("✅ Conexão bem-sucedida!")
        return connection
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return None
# Fim Opção 2

# Opção 3

def test_alternative_connections(directory):
    # Testar diferentes configurações de conexão
    test_configs = [
        # Sem autocommit
        (f"DRIVER={{Microsoft Paradox Driver (*.db )}};DBQ={directory};", {"autocommit": False}),
        
        # Com timeout
        (f"DRIVER={{Microsoft Paradox Driver (*.db )}};DBQ={directory};", {"timeout": 30}),
        
        # Sem parâmetros extras
        (f"DRIVER={{Microsoft Paradox Driver (*.db )}};DBQ={directory};", {}),
        
        # Com readonly
        (f"DRIVER={{Microsoft Paradox Driver (*.db )}};DBQ={directory};ReadOnly=1;", {})
    ]
    
    for i, (conn_str, params) in enumerate(test_configs, 1):
        print(f"\nTestando configuração {i}:")
        print(f"String: {conn_str}")
        print(f"Parâmetros: {params}")
        
        try:
            if params:
                connection = pyodbc.connect(conn_str, **params)
            else:
                connection = pyodbc.connect(conn_str)
            
            print(f"✅ Configuração {i} FUNCIONOU!")
            
            # Testar consulta simples
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM LocNotaF LIMIT 1")
            print("✅ Consulta teste bem-sucedida!")
            
            connection.close()
            return conn_str, params
            
        except Exception as e:
            print(f"❌ Configuração {i} falhou: {e}")
    
    return None, None

# Execute o teste
working_conn, working_params = test_alternative_connections("C:/TeitechTraje/Dados")

# Fim Opção 3

# Opção 3 Corrigida
# Teste a correção
conn_str = "DRIVER={Microsoft Paradox Driver (*.db )};DBQ=C:/TeitechTraje/Dados;"

try:
    connection = pyodbc.connect(conn_str, autocommit=False)
    print("✅ CONEXÃO CORRIGIDA FUNCIONOU!")
    
    # Teste uma consulta
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM LocNotaF")
    row = cursor.fetchone()
    print(f"✅ Dados encontrados: {row}")
    
    connection.close()
    
except Exception as e:
    print(f"❌ Ainda com erro: {e}")
# Fim opção 3 corrigida
    
    try:
        monitor.run()
    finally:
        #monitor.close()
