import adodbapi

def connect_via_bde():
    try:
        # String de conexão BDE para Paradox
        conn_str = (
            "Provider=Microsoft.Jet.OLEDB.4.0;"
            "Data Source=C:/TeitechTraje/Dados;"
            "Extended Properties='Paradox 5.x;HDR=No;IMEX=1;';"
        )
        
        connection = adodbapi.connect(conn_str)
        print("✅ Conexão BDE bem-sucedida!")
        
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM LocNotaF")
        
        row = cursor.fetchone()
        print(f"✅ Dados encontrados: {row}")
        
        return connection
        
    except Exception as e:
        print(f"❌ Erro BDE: {e}")
        return None

# Teste
connection = connect_via_bde()



import win32com.client

def connect_bde_com():
    try:
        # Criar conexão ADO
        conn = win32com.client.Dispatch("ADODB.Connection")
        
        conn_str = (
            "Provider=Microsoft.Jet.OLEDB.4.0;"
            "Data Source=C:/TeitechTraje/Dados;"
            "Extended Properties='Paradox 5.x;';"
        )
        
        conn.Open(conn_str)
        print("✅ Conexão COM/BDE bem-sucedida!")
        
        # Executar consulta
        rs = win32com.client.Dispatch("ADODB.Recordset")
        rs.Open("SELECT * FROM LocNotaF", conn)
        
        if not rs.EOF:
            # Ler primeiro registro
            fields = []
            for i in range(rs.Fields.Count):
                fields.append(rs.Fields(i).Value)
            print(f"✅ Dados: {fields}")
        
        rs.Close()
        conn.Close()
        return True
        
    except Exception as e:
        print(f"❌ Erro COM: {e}")
        return False

# Teste
connect_bde_com()
