import serial
import requests
import time
import json
from datetime import datetime
import serial.tools.list_ports

# --- CONFIGURAÇÃO ---
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
            response = requests.post(url, json=dados, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Dados salvos no Firebase: {dados['temperatura']}°C, {dados['umidade']}%")
                self.ultimo_sucesso = time.time()
                return True
            else:
                print(f"❌ Erro HTTP {response.status_code} ao salvar no Firebase")
                return False
                
        except requests.exceptions.ConnectionError:
            print("❌ Erro: Não foi possível conectar ao Firebase - verifique a internet")
            return False
        except requests.exceptions.Timeout:
            print("❌ Erro: Timeout ao conectar com Firebase")
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

class GerenciadorPortas:
    def __init__(self, baud_rate):
        self.baud_rate = baud_rate
        self.porta_atual = None
        self.serial_connection = None
    
    def listar_portas_disponiveis(self):
        """Lista todas as portas COM disponíveis"""
        print("\n🔎 Escaneando portas COM disponíveis...")
        portas = []
        
        for porta in serial.tools.list_ports.comports():
            portas.append({
                'device': porta.device,
                'description': porta.description,
                'hwid': porta.hwid
            })
            print(f"   📍 {porta.device} - {porta.description}")
        
        return portas
    
    def detectar_porta_arduino(self):
        """Tenta detectar automaticamente a porta do Arduino"""
        print("\n🎯 Procurando Arduino...")
        
        # Padrões comuns de descrição do Arduino
        padroes_arduino = [
            'arduino', 'Arduino', 'CH340', 'USB Serial', 'USB-to-Serial',
            'Serial-USB', 'USB2.0-Serial', 'FT232R', 'CP210'
        ]
        
        for porta in serial.tools.list_ports.comports():
            descricao = porta.description.upper()
            dispositivo = porta.device
            
            # Verifica se a descrição contém algum padrão do Arduino
            for padrao in padroes_arduino:
                if padrao.upper() in descricao:
                    print(f"✅ Arduino detectado: {dispositivo} - {porta.description}")
                    return dispositivo
        
        # Se não encontrou por descrição, retorna a primeira porta disponível
        portas = [porta.device for porta in serial.tools.list_ports.comports()]
        if portas:
            print(f"⚠️  Arduino não detectado automaticamente. Usando primeira porta: {portas[0]}")
            return portas[0]
        
        return None
    
    def testar_porta(self, porta):
        """Testa se a porta é válida e responde como Arduino"""
        print(f"🧪 Testando porta: {porta}")
        
        try:
            ser = serial.Serial(porta, self.baud_rate, timeout=2)
            time.sleep(2)  # Espera o Arduino reinicializar
            
            # Limpa buffer serial
            ser.reset_input_buffer()
            
            # Aguarda dados por um tempo limitado
            inicio_tempo = time.time()
            while time.time() - inicio_tempo < 5:  # Timeout de 5 segundos
                if ser.in_waiting > 0:
                    linha = ser.readline().decode('utf-8', errors='ignore').strip()
                    if linha and linha.startswith('UMD:'):
                        print(f"✅ Porta {porta} válida! Recebido: {linha}")
                        ser.close()
                        return True
                time.sleep(0.1)
            
            ser.close()
            print(f"❌ Porta {porta} não respondeu com dados DHT11")
            return False
            
        except serial.SerialException as e:
            print(f"❌ Erro na porta {porta}: {e}")
            return False
    
    def conectar_automaticamente(self):
        """Conecta automaticamente à porta do Arduino"""
        portas_disponiveis = self.listar_portas_disponiveis()
        
        if not portas_disponiveis:
            print("❌ Nenhuma porta COM encontrada!")
            print("   Verifique:")
            print("   - Se o Arduino está conectado via USB")
            print("   - Se o driver CH340/FTDI está instalado")
            print("   - Se a porta não está sendo usada por outro programa")
            return None
        
        # Tenta detectar Arduino automaticamente
        porta_arduino = self.detectar_porta_arduino()
        
        if porta_arduino:
            if self.testar_porta(porta_arduino):
                try:
                    self.serial_connection = serial.Serial(porta_arduino, self.baud_rate, timeout=1)
                    time.sleep(2)
                    self.porta_atual = porta_arduino
                    print(f"🎉 Conectado com sucesso à porta: {porta_arduino}")
                    return self.serial_connection
                except serial.SerialException as e:
                    print(f"❌ Erro ao conectar com {porta_arduino}: {e}")
        
        # Se não encontrou automaticamente, testa todas as portas
        print("\n🔍 Testando todas as portas disponíveis...")
        for porta_info in portas_disponiveis:
            porta = porta_info['device']
            if self.testar_porta(porta):
                try:
                    self.serial_connection = serial.Serial(porta, self.baud_rate, timeout=1)
                    time.sleep(2)
                    self.porta_atual = porta
                    print(f"🎉 Conectado com sucesso à porta: {porta}")
                    return self.serial_connection
                except serial.SerialException as e:
                    print(f"❌ Erro ao conectar com {porta}: {e}")
        
        print("❌ Não foi possível conectar a nenhuma porta")
        return None
    
    def reconectar(self):
        """Tenta reconectar se a conexão foi perdida"""
        print("\n🔄 Tentando reconectar...")
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        
        time.sleep(2)
        return self.conectar_automaticamente()

def processar_dados_serial(linha):
    """Processa a linha recebida do Arduino e extrai os dados"""
    try:
        if linha.startswith('UMD:'):
            linha_limpa = linha.strip()
            dados_split = linha_limpa.split('|')
            
            if len(dados_split) >= 2:
                umidade_str = dados_split[0].replace('UMD:', '').strip()
                temperatura_str = dados_split[1].replace('TMP:', '').strip()
                
                umidade = float(umidade_str)
                temperatura = float(temperatura_str)
                
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
    
    print("🚀 Iniciando Proxy Arduino-Firebase com Detecção Automática")
    print("=" * 60)
    
    # Inicializa gerenciadores
    firebase = FirebaseManager(FIREBASE_URL, FIREBASE_SECRET)
    gerenciador_portas = GerenciadorPortas(BAUD_RATE)
    
    # Testa conexão com Firebase
    if not firebase.testar_conexao():
        print("❌ Não foi possível conectar ao Firebase.")
        return
    
    # Conecta automaticamente ao Arduino
    ser = gerenciador_portas.conectar_automaticamente()
    if not ser:
        print("❌ Não foi possível conectar ao Arduino. Verifique:")
        print("   - Se o Arduino está conectado via USB")
        print("   - Se o sketch está rodando no Arduino")
        print("   - Se a taxa de Baud está correta (9600)")
        return
    
    contador_leitura = 0
    contador_erros_firebase = 0
    contador_sem_dados = 0
    max_sem_dados = 10  # Reconecta se ficar muito tempo sem dados
    
    print("\n📊 Iniciando captura de dados...")
    print("-" * 50)

    try:
        while True:
            if ser.in_waiting > 0:
                comando_bruto = ser.readline().decode('utf-8', errors='ignore').strip()
                contador_sem_dados = 0  # Reset contador
                
                if comando_bruto and comando_bruto.startswith('UMD:'):
                    contador_leitura += 1
                    
                    temperatura, umidade = processar_dados_serial(comando_bruto)
                    
                    if temperatura is not None and umidade is not None:
                        print(f"📊 [Leitura {contador_leitura}] T: {temperatura:.1f}°C | U: {umidade:.1f}%")
                        
                        sucesso = firebase.salvar_dados_sensor(temperatura, umidade)
                        
                        if sucesso:
                            ser.write(b'ACK\n')
                            contador_erros_firebase = 0
                        else:
                            contador_erros_firebase += 1
                            print(f"⚠️  Falha ao salvar no Firebase (erro {contador_erros_firebase})")
                            
                            if contador_erros_firebase >= 3:
                                print("🔍 Testando reconexão com Firebase...")
                                if firebase.testar_conexao():
                                    contador_erros_firebase = 0
            else:
                contador_sem_dados += 1
                # Se ficou muito tempo sem dados, tenta reconectar
                if contador_sem_dados > max_sem_dados * 10:  # Aprox. 10 segundos
                    print("🔄 Muito tempo sem dados. Tentando reconectar...")
                    ser = gerenciador_portas.reconectar()
                    if not ser:
                        break
                    contador_sem_dados = 0
            
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n🛑 Proxy encerrado pelo usuário")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("🔌 Porta serial fechada")

# Função para teste rápido das portas
def teste_rapido_portas():
    """Função para testar rapidamente as portas disponíveis"""
    gerenciador = GerenciadorPortas(BAUD_RATE)
    gerenciador.listar_portas_disponiveis()
    porta = gerenciador.detectar_porta_arduino()
    if porta:
        print(f"\n🎯 Porta sugerida: {porta}")
        if gerenciador.testar_porta(porta):
            print("✅ Porta testada com sucesso!")
        else:
            print("❌ Porta não respondeu")

if __name__ == "__main__":
    # Descomente a linha abaixo para testar apenas a detecção de portas
    # teste_rapido_portas()
    
    iniciar_proxy()