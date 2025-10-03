import serial
import requests
import time
import json
from datetime import datetime

# --- CONFIGURAÇÃO ---
PORTA_SERIAL = 'COM11'  # Substitua pela porta COM do seu Arduino
BAUD_RATE = 9600

# CONFIGURE ESTAS VARIÁVEIS COM SEUS DADOS REAIS!
FIREBASE_URL = "https://testiot-a31e9-default-rtdb.firebaseio.com/"  # Substitua pela URL real
FIREBASE_SECRET = "3QYP7HgcCqTTVbocyzYkQYo2o3ni2TamaXSaa6It"  # Substitua pela chave secreta real

# Caminho no Firebase onde os dados serão salvos
FIREBASE_PATH = "/sensores/dht11"
# --------------------

class FirebaseManager:
    def __init__(self, base_url, secret_key):
        self.base_url = base_url.rstrip('/')
        self.secret_key = secret_key
        self.ultimo_sucesso = None
    
    def testar_conexao(self):
        """Testa a conexão com o Firebase"""
        print("🔍 Testando conexão com Firebase...")
        
        test_data = {"teste": "conexao", "timestamp": datetime.now().isoformat()}
        url = f"{self.base_url}/teste_conexao.json?auth={self.secret_key}"
        
        try:
            response = requests.put(url, json=test_data, timeout=10)
            print(f"📡 Status do teste: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Conexão com Firebase: OK")
                return True
            else:
                print(f"❌ Falha no teste. Status: {response.status_code}")
                print(f"📄 Resposta: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão: {e}")
            return False
    
    def salvar_dados(self, caminho, dados):
        """Salva dados no Firebase Realtime Database"""
        url = f"{self.base_url}{caminho}.json?auth={self.secret_key}"
        
        try:
            response = requests.post(url, json=dados, timeout=10)  # Mudei para POST para criar lista
            
            if response.status_code == 200:
                print(f"✅ Dados salvos no Firebase: {dados['temperatura']}°C, {dados['umidade']}%")
                self.ultimo_sucesso = time.time()
                return True
            else:
                print(f"❌ Erro HTTP {response.status_code} ao salvar no Firebase")
                print(f"📄 Resposta: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            print("❌ Erro: Não foi possível conectar ao Firebase - verifique a internet")
            return False
        except requests.exceptions.Timeout:
            print("❌ Erro: Timeout ao conectar com Firebase")
            return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de requisição: {e}")
            return False
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
            return False
    
    def salvar_dados_sensor(self, temperatura, umidade):
        """Salva dados do sensor com timestamp"""
        timestamp = datetime.now().isoformat()
        
        dados = {
            "temperatura": round(temperatura, 2),
            "umidade": round(umidade, 2),
            "timestamp": timestamp,
            "timestamp_unix": time.time(),
            "unidade_temperatura": "°C",
            "unidade_umidade": "%",
            "sensor": "DHT11"
        }
        
        return self.salvar_dados(FIREBASE_PATH, dados)

def processar_dados_serial(linha):
    """Processa a linha recebida do Arduino e extrai os dados"""
    try:
        if linha.startswith('UMD:'):
            # Remove possíveis caracteres inválidos
            linha_limpa = linha.strip()
            dados_split = linha_limpa.split('|')
            
            if len(dados_split) >= 2:
                # Extrai umidade (vem primeiro)
                umidade_str = dados_split[0].replace('UMD:', '').strip()
                # Extrai temperatura (vem depois do |)
                temperatura_str = dados_split[1].replace('TMP:', '').strip()
                
                umidade = float(umidade_str)
                temperatura = float(temperatura_str)
                
                # Validação básica dos dados
                if 0 <= umidade <= 100 and -40 <= temperatura <= 80:
                    return temperatura, umidade
                else:
                    print(f"⚠️  Dados fora da faixa esperada: T={temperatura}, U={umidade}")
                    return None, None
        
        return None, None
        
    except ValueError as e:
        print(f"❌ Erro ao converter dados: {e} - Linha: {linha}")
        return None, None
    except Exception as e:
        print(f"❌ Erro inesperado ao processar dados: {e}")
        return None, None

def verificar_configuracao():
    """Verifica se as configurações estão corretas"""
    problemas = []
    
    if FIREBASE_URL.startswith("https://seu-projeto") or "SEU-PROJETO" in FIREBASE_URL:
        problemas.append("FIREBASE_URL não configurado")
    
    if FIREBASE_SECRET == "SUA_CHAVE_SECRETA_AQUI" or FIREBASE_SECRET == "sua_chave_secreta":
        problemas.append("FIREBASE_SECRET não configurado")
    
    if problemas:
        print("❌" * 50)
        print("ERRO DE CONFIGURAÇÃO:")
        for problema in problemas:
            print(f"  - {problema}")
        print("\n📝 COMO CONFIGURAR:")
        print("1. Acesse: https://console.firebase.google.com/")
        print("2. Crie um projeto ou selecione um existente")
        print("3. Vá em: Build > Realtime Database > Criar banco de dados")
        print("4. Escolha 'modo teste' para início")
        print("5. Vá em: Configurações do projeto (⚙️) > Contas de serviço")
        print("6. Em 'Segredos do banco de dados', clique em 'Gerar novo segredo'")
        print("7. Copie a URL do banco de dados e o segredo para as variáveis no código")
        print("❌" * 50)
        return False
    
    return True

def iniciar_proxy():
    """Inicia a conexão serial e o loop do proxy."""
    
    if not verificar_configuracao():
        return
    
    print(f"🚀 Iniciando proxy Arduino-Firebase")
    print(f"📡 Porta: {PORTA_SERIAL}, Baud: {BAUD_RATE}")
    print(f"🔥 Firebase: {FIREBASE_URL}")
    
    # Inicializa o gerenciador do Firebase
    firebase = FirebaseManager(FIREBASE_URL, FIREBASE_SECRET)
    
    # Testa conexão com Firebase
    if not firebase.testar_conexao():
        print("❌ Não foi possível conectar ao Firebase. Verifique:")
        print("   - Sua conexão com a internet")
        print("   - A URL e chave secreta do Firebase")
        print("   - As regras de segurança do banco de dados")
        return
    
    contador_leitura = 0
    contador_erros_firebase = 0
    
    try:
        # Abre a porta serial
        ser = serial.Serial(PORTA_SERIAL, BAUD_RATE, timeout=1)
        time.sleep(2)  # Espera para inicializar
        print("✅ Conexão serial estabelecida")
        print("📊 Escutando dados do Arduino...")
        print("-" * 50)

        while True:
            if ser.in_waiting > 0:
                comando_bruto = ser.readline().decode('utf-8', errors='ignore').strip()
                
                if comando_bruto and comando_bruto.startswith('UMD:'):
                    contador_leitura += 1
                    
                    # Extrai temperatura e umidade
                    temperatura, umidade = processar_dados_serial(comando_bruto)
                    
                    if temperatura is not None and umidade is not None:
                        print(f"📊 [Leitura {contador_leitura}] T: {temperatura:.1f}°C | U: {umidade:.1f}%")
                        
                        # Tenta salvar no Firebase
                        sucesso = firebase.salvar_dados_sensor(temperatura, umidade)
                        
                        if sucesso:
                            # Envia ACK para o Arduino
                            ser.write(b'ACK\n')
                            contador_erros_firebase = 0  # Reset contador de erros
                        else:
                            contador_erros_firebase += 1
                            print(f"⚠️  Falha ao salvar no Firebase (erro {contador_erros_firebase})")
                            
                            # Se muitos erros consecutivos, testa conexão
                            if contador_erros_firebase >= 3:
                                print("🔍 Testando reconexão com Firebase...")
                                if firebase.testar_conexao():
                                    contador_erros_firebase = 0
                    else:
                        print(f"❌ Dados inválidos: {comando_bruto}")
            
            time.sleep(0.1)

    except serial.SerialException as e:
        print(f"❌ Erro serial: {e}")
        print("   Verifique:")
        print("   - Se a porta COM está correta")
        print("   - Se o Arduino está conectado")
        print("   - Se outra aplicação não está usando a porta")
    except KeyboardInterrupt:
        print("\n\n🛑 Proxy encerrado pelo usuário")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("🔌 Porta serial fechada")

if __name__ == "__main__":
    iniciar_proxy()