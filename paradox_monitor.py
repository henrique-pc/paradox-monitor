import adodbapi

def connect_via_bde_alias():
    try:
        # Usar alias BDE
        conn_str = "Provider=MSDASQL;DSN=MonitorarTraje;"
        
        connection = adodbapi.connect(conn_str)
        print("✅ Conexão via BDE Alias funcionou!")
        return connection
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return None


#####teste 2

import adodbapi  # ou win32com.client

class ParadoxMonitor:
    def __init__(self, config):
        self.config = config
        self.connection = None
    
    def connect(self):
        try:
            directory = self.config['main_table']['directory'].replace('/', '\\')
            
            conn_str = (
                "Provider=Microsoft.Jet.OLEDB.4.0;"
                f"Data Source={directory};"
                "Extended Properties='Paradox 5.x;HDR=No;';"
            )
            
            self.connection = adodbapi.connect(conn_str)
            print("✅ Conectado via BDE!")
            return True
            
        except Exception as e:
            print(f"❌ Erro na conexão BDE: {e}")
            return False
    
    def execute_query(self, query):
        if not self.connection:
            return None
            
        cursor = self.connection.cursor()
        cursor.execute(query)
        return cursor.fetchall()
