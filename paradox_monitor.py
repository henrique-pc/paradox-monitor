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
