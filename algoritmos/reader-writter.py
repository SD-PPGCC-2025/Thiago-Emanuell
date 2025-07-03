"""
=====================================================
TRABALHO DE MESTRADO DA UNIVERSIDADE FEDERAL DE GOIÁS
=====================================================
Disciplina: Sistemas Distribuídos
Aluno: Thiago Emanuell Vieira Moura
Sistema: Leitores-Escritores com Controle de Acesso e Persistência de Dados
"""

# =============================================
# BIBLIOTECAS NECESSÁRIAS
# =============================================
import threading  # Para executar múltiplas tarefas simultaneamente
import time       # Para controle de tempo e pausas
import random     # Para gerar números aleatórios
import os         # Para operações com arquivos e sistema
import signal     # Para tratamento de sinais (ex: Ctrl+C)
from datetime import datetime  # Para trabalhar com datas/horas

# =============================================
# CONFIGURAÇÕES PRINCIPAIS DO SISTEMA
# =============================================
ARQUIVO = "dados.txt"            # Nome do arquivo compartilhado
MAX_LEITORES = 10                # Número máximo de leitores simultâneos
MAX_ESCRITORES = 4               # Número máximo de escritores simultâneos
TEMPO_LEITURA = (0.3, 1.2)       # Tempo mínimo e máximo de leitura (em segundos)
TEMPO_ESCRITA = (1.0, 2.5)       # Tempo mínimo e máximo de escrita
INTERVALO_OPERACOES = (0.2, 0.7) # Intervalo entre operações de cada usuário

# =============================================
# VARIÁVEIS GLOBAIS DE CONTROLE
# =============================================
# Variável para controle de execução do sistema
running = True  # Quando False, todas as threads param

# Contadores para gerenciamento de acesso
leitura_ativa = 0        # Quantidade de leitores acessando o arquivo
leitores_esperando = 0   # Leitores na fila de espera
escritores_esperando = 0 # Escritores na fila de espera

# Mecanismos de sincronização:
mutex_leitura = threading.Lock()  # Controla o acesso à variável leitura_ativa
recurso = threading.Lock()        # Garante exclusividade para escritores
fila_escritores = threading.Lock()# Controla a fila de escritores (evita starvation)
print_lock = threading.Lock()     # Sincroniza a saída no console

# =============================================
# FUNÇÃO: INICIALIZAR ARQUIVO
# =============================================
def inicializar_arquivo():
    """
    Função responsável por:
    1. Criar o arquivo se não existir
    2. Validar o conteúdo do arquivo existente
    3. Garantir que o arquivo esteja acessível
    
    Fluxo:
    - Verifica se o arquivo existe
    - Se não existe: cria com cabeçalho padrão
    - Se existe: verifica se está válido
    - Se corrompido: recria o arquivo
    """
    if not os.path.exists(ARQUIVO):
        # Cria novo arquivo com estrutura inicial
        with open(ARQUIVO, "w", encoding="utf-8") as f:
            f.write("=== REGISTRO DA REDE ===\n")
            f.write(f"Sistema criado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write("="*40 + "\n\n")
        # Define permissões de leitura/escrita seguras
        os.chmod(ARQUIVO, 0o644)
    else:
        # Verifica integridade do arquivo existente
        try:
            with open(ARQUIVO, "r", encoding="utf-8") as f:
                # Se arquivo está vazio, gera erro
                if not f.read().strip():
                    raise ValueError("Arquivo vazio")
        except (IOError, ValueError):
            # Recria arquivo inválido/corrompido
            os.remove(ARQUIVO)
            inicializar_arquivo()

# =============================================
# FUNÇÃO: OBTER ESTADO DO SISTEMA
# =============================================
def obter_estado():
    """
    Retorna uma string formatada com o estado atual do sistema
    Mostra:
    - Leitores ativos
    - Leitores e escritores na fila de espera
    
    Exemplo: [Leitores Ativos: 3 | Em Espera: Leit. --> 2 / Escr. --> 1]
    """
    return (f"[Leitores Ativos: {leitura_ativa} | "
            f"Em Espera: Leit. --> {leitores_esperando} / Escr. --> {escritores_esperando}]")

# =============================================
# FUNÇÃO: REGISTRO DE LOGS (MENSAGENS)
# =============================================
def log(mensagem, tipo="INFO"):
    """
    Exibe mensagens coloridas no console com:
    - Timestamp preciso
    - Codificação por cores
    - Sincronização para evitar sobreposição
    
    Parâmetros:
    - mensagem: texto a ser exibido
    - tipo: determina a cor (LEITURA, ESCRITA, ERRO, SISTEMA)
    """
    # Códigos de cores ANSI
    cores = {
        "LEITURA": "\033[94m",  # Azul
        "ESCRITA": "\033[92m",  # Verde
        "ERRO": "\033[91m",     # Vermelho
        "SISTEMA": "\033[95m",  # Magenta
        "RESET": "\033[0m"      # Resetar cores
    }
    
    # Obtém hora atual formatada
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Exibe mensagem sincronizada
    with print_lock:
        print(f"{cores.get(tipo, '')}{timestamp} ▸ {mensagem}{cores['RESET']}")

# =============================================
# FUNÇÃO: OPERAÇÃO DE LEITURA (THREAD)
# =============================================
def leitor_worker(id_leitor):
    """
    Simula o comportamento de um leitor:
    1. Solicita acesso
    2. Lê o conteúdo
    3. Libera recursos
    4. Repete após intervalo
    
    Fluxo detalhado:
    1. Entra na fila de espera
    2. Adquire permissão de leitura
    3. Lê o arquivo
    4. Libera recursos
    5. Aguarda intervalo aleatório
    """
    global leitura_ativa, leitores_esperando, running

    # Loop principal do leitor
    while running:
        try:
            # ETAPA 1: SOLICITAR ACESSO
            leitores_esperando += 1
            log(f"Leitor #{id_leitor} solicitou acesso {obter_estado()}", "LEITURA")
            
            # Respeita a prioridade dos escritores na fila
            fila_escritores.acquire()
            fila_escritores.release()

            # ETAPA 2: ACESSAR RECURSO
            with mutex_leitura:  # Bloqueio para controle seguro
                leitura_ativa += 1
                leitores_esperando -= 1
                
                # Primeiro leitor bloqueia escritores
                if leitura_ativa == 1:
                    recurso.acquire()
                
                log(f"Leitor #{id_leitor} iniciou leitura {obter_estado()}", "LEITURA")

            # ETAPA 3: LER CONTEÚDO
            with open(ARQUIVO, "r", encoding="utf-8") as f:
                conteudo = f.read()  # Lê todo o arquivo
                
                # Simula tempo de processamento
                time.sleep(random.uniform(*TEMPO_LEITURA))
                
                # Extrai e exibe última atualização
                linhas = conteudo.splitlines()
                if linhas:
                    ultima_atualizacao = linhas[-1].strip()
                    log(f"Leitor #{id_leitor} visualizou: '{ultima_atualizacao}'", "LEITURA")
                
        except Exception as e:
            log(f"Erro na leitura #{id_leitor}: {str(e)}", "ERRO")
        finally:
            # ETAPA 4: LIBERAR RECURSOS
            with mutex_leitura:
                if leitura_ativa > 0:
                    leitura_ativa -= 1
                    log(f"Leitor #{id_leitor} concluiu {obter_estado()}", "LEITURA")
                    
                    # Último leitor libera para escritores
                    if leitura_ativa == 0:
                        recurso.release()
            
            # Intervalo antes de nova operação
            time.sleep(random.uniform(*INTERVALO_OPERACOES))

# =============================================
# FUNÇÃO: OPERAÇÃO DE ESCRITA (THREAD)
# =============================================
def escritor_worker(id_escritor):
    """
    Simula o comportamento de um escritor:
    1. Solicita acesso exclusivo
    2. Escreve no arquivo
    3. Libera recursos
    4. Repete após intervalo
    
    Fluxo detalhado:
    1. Entra na fila de espera
    2. Adquire bloqueio exclusivo
    3. Escreve no arquivo
    4. Libera recursos
    5. Aguarda intervalo aleatório
    """
    global escritores_esperando, running

    # Loop principal do escritor
    while running:
        try:
            # ETAPA 1: SOLICITAR ACESSO EXCLUSIVO
            escritores_esperando += 1
            log(f"Escritor ${id_escritor} solicitou acesso {obter_estado()}", "ESCRITA")
            
            # Adquire controle da fila e recurso
            fila_escritores.acquire()
            recurso.acquire()
            escritores_esperando -= 1
            log(f"Escritor ${id_escritor} iniciou escrita {obter_estado()}", "ESCRITA")

            # ETAPA 2: ESCREVER NO ARQUIVO
            timestamp = datetime.now().strftime("%d/%m %H:%M:%S")
            conteudo = f"{timestamp} | Escritor ${id_escritor} | Revisão: {random.randint(1000, 9999)}"
            
            with open(ARQUIVO, "a", encoding="utf-8") as f:
                f.write(conteudo + "\n")  # Adiciona nova linha
                
                # Simula tempo de processamento
                time.sleep(random.uniform(*TEMPO_ESCRITA))
                
            log(f"Escritor ${id_escritor} atualizou registro: '{conteudo}'", "ESCRITA")
            
        except Exception as e:
            log(f"Erro na escrita ${id_escritor}: {str(e)}", "ERRO")
        finally:
            # ETAPA 3: LIBERAR RECURSOS
            if recurso.locked():
                recurso.release()
            if fila_escritores.locked():
                fila_escritores.release()
            
            log(f"Escritor ${id_escritor} concluiu {obter_estado()}", "ESCRITA")
            time.sleep(random.uniform(*INTERVALO_OPERACOES))

# =============================================
# FUNÇÃO: GERENCIAR TÉRMINO DO PROGRAMA
# =============================================
def gerenciar_termino(signum, frame):
    """
    Manipula o sinal de interrupção (Ctrl+C):
    1. Altera a flag 'running' para False
    2. Permite término gracioso das threads
    3. Exibe mensagem de status
    """
    global running
    log("Finalizando operações... Aguarde", "SISTEMA")
    running = False

# =============================================
# FUNÇÃO PRINCIPAL
# =============================================
def main():
    """
    Função principal que coordena todo o sistema:
    1. Configura ambiente
    2. Inicia threads
    3. Gerencia execução
    4. Realiza limpeza final
    """
    global running

    # Configuração inicial
    os.system('cls' if os.name == 'nt' else 'clear')  # Limpa console
    signal.signal(signal.SIGINT, gerenciar_termino)   # Configura Ctrl+C
    
    try:
        # Inicialização do sistema
        running = True
        inicializar_arquivo()
        log("Sistema de rede operacional iniciado", "SISTEMA")
        log(f"Arquivo de dados: {os.path.abspath(ARQUIVO)}", "SISTEMA")
        log("Pressione Ctrl+C para encerrar", "SISTEMA")
        print("\n" + "="*60)

        # Criação das threads
        workers = []
        # Cria threads para leitores
        for i in range(MAX_LEITORES):
            t = threading.Thread(target=leitor_worker, args=(i+1,), daemon=True)
            workers.append(t)
            t.start()

        # Cria threads para escritores
        for i in range(MAX_ESCRITORES):
            t = threading.Thread(target=escritor_worker, args=(i+1,), daemon=True)
            workers.append(t)
            t.start()

        # Loop principal de execução
        while running:
            time.sleep(0.5)  # Reduz uso da CPU

    except Exception as e:
        log(f"Erro crítico: {str(e)}", "ERRO")
    finally:
        # Fase de encerramento
        running = False
        # Aguarda término de todas as threads
        for t in threading.enumerate():
            if t is not threading.main_thread():
                t.join(timeout=1)  # Timeout para evitar deadlocks
        
        # Mensagens finais
        log("Sistema encerrado com sucesso", "SISTEMA")
        log(f"Tamanho do arquivo: {os.path.getsize(ARQUIVO)} bytes", "SISTEMA")

# =============================================
# INÍCIO DA EXECUÇÃO
# =============================================
if __name__ == "__main__":
    main()
