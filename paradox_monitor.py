import os
import winreg
import win32com.client

def setup_bde_complete():
    print("=== SETUP BDE COMPLETO ===\n")
    
    # 1. Verificar BDE
    print("1. Verificando instalação BDE...")
    if not check_bde_installation():
        print("❌ BDE não encontrado. Instale o Borland Database Engine primeiro.")
        return False
    
    # 2. Criar alias
    print("\n2. Criando alias BDE...")
    alias_name = "TeitechDB"
    db_path = r"C:\TeitechTraje\Dados"
    
    if not create_bde_alias_registry(alias_name, db_path):
        print("❌ Falha ao criar alias. Execute como administrador.")
        return False
    
    # 3. Testar conexão
    print("\n3. Testando conexão...")
    if connect_via_bde_ado(alias_name):
        print("✅ Setup BDE concluído com sucesso!")
        return True
    else:
        print("❌ Falha na conexão. Verifique configurações.")
        return False

def check_bde_installation():
    """Verifica se BDE está instalado"""
    try:
        key_paths = [
            r"SOFTWARE\Borland\Database Engine",
            r"SOFTWARE\WOW6432Node\Borland\Database Engine"
        ]
        
        for key_path in key_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                    print("✅ BDE encontrado no registro")
                    return True
            except FileNotFoundError:
                continue
        
        print("❌ BDE não encontrado no registro")
        return False
        
    except Exception as e:
        print(f"Erro ao verificar BDE: {e}")
        return False

def create_bde_alias_registry(alias_name, db_path):
    """Cria alias BDE no registro"""
    try:
        # Tentar diferentes localizações do BDE
        base_paths = [
            r"SOFTWARE\Borland\Database Engine\Settings\DATABASES",
            r"SOFTWARE\WOW6432Node\Borland\Database Engine\Settings\DATABASES"
        ]
        
        success = False
        for base_path in base_paths:
            try:
                alias_path = f"{base_path}\\{alias_name.upper()}"
                
                with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, alias_path) as alias_key:
                    winreg.SetValueEx(alias_key, "TYPE", 0, winreg.REG_SZ, "PARADOX")
                    winreg.SetValueEx(alias_key, "PATH", 0, winreg.REG_SZ, db_path)
                    winreg.SetValueEx(alias_key, "DEFAULT DRIVER", 0, winreg.REG_SZ, "PARADOX")
                    winreg.SetValueEx(alias_key, "ENABLE BCD", 0, winreg.REG_SZ, "FALSE")
                    
                print(f"✅ Alias '{alias_name}' criado em: {base_path}")
                success = True
                break
                
            except Exception as e:
                print(f"Tentativa falhou em {base_path}: {e}")
                continue
        
        return success
        
    except Exception as e:
        print(f"❌ Erro ao criar alias: {e}")
        return False

def connect_via_bde_ado(alias_name):
    """Conecta usando alias BDE via ADO"""
    try:
        conn = win32com.client.Dispatch("ADODB.Connection")
        
        # Diferentes strings de conexão para testar
        connection_strings = [
            f"Provider=MSDASQL;DSN={alias_name};",
            f"Provider=Microsoft.Jet.OLEDB.4.0;Data Source=C:\\TeitechTraje\\Dados;Extended Properties='Paradox 5.x;';",
            f"Provider=MSDASQL;Driver={{Microsoft Paradox Driver (*.db )}};DBQ=C:\\TeitechTraje\\Dados;",
        ]
        
        for i, conn_str in enumerate(connection_strings, 1):
            try:
                print(f"Testando conexão {i}: {conn_str}")
                conn.Open(conn_str)
                print(f"✅ Conexão {i} bem-sucedida!")
                
                # Testar consulta
                rs = win32com.client.Dispatch("ADODB.Recordset")
                rs.Open("SELECT * FROM LocNotaF", conn)
                
                if not rs.EOF:
                    print("✅ Dados encontrados na tabela!")
                    
                    # Mostrar informações da primeira linha
                    field_count = rs.Fields.Count
                    print(f"Campos encontrados: {field_count}")
                    
                    # Mostrar alguns campos
                    row_info = []
                    for field_idx in range(min(3, field_count)):  # Mostrar só 3 campos
                        field_name = rs.Fields(field_idx).Name
                        field_value = rs.Fields(field_idx).Value
                        row_info.append(f"{field_name}={field_value}")
                    
                    print(f"Amostra de dados: {' | '.join(row_info)}")
                else:
                    print("⚠️ Tabela existe mas está vazia")
                
                rs.Close()
                conn.Close()
                return True
                
            except Exception as e:
                print(f"❌ Conexão {i} falhou: {e}")
                continue
        
        print("❌ Todas as tentativas de conexão falharam")
        return False
        
    except Exception as e:
        print(f"❌ Erro geral na conexão: {e}")
        return False

def list_bde_aliases():
    """Lista aliases BDE existentes"""
    try:
        print("\n=== ALIASES BDE EXISTENTES ===")
        
        base_paths = [
            r"SOFTWARE\Borland\Database Engine\Settings\DATABASES",
            r"SOFTWARE\WOW6432Node\Borland\Database Engine\Settings\DATABASES"
        ]
        
        found_aliases = []
        
        for base_path in base_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_path) as key:
                    i = 0
                    while True:
                        try:
                            alias_name = winreg.EnumKey(key, i)
                            found_aliases.append(alias_name)
                            i += 1
                        except WindowsError:
                            break
            except FileNotFoundError:
                continue
        
        if found_aliases:
            print("Aliases encontrados:")
            for alias in found_aliases:
                print(f"  - {alias}")
        else:
            print("Nenhum alias BDE encontrado")
            
        return found_aliases
        
    except Exception as e:
        print(f"Erro ao listar aliases: {e}")
        return []

# Execute o setup completo
if __name__ == "__main__":
    # Primeiro listar aliases existentes
    list_bde_aliases()
    
    # Executar setup
    setup_bde_complete()
