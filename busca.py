import csv
import os
import random
import statistics

CAMPOS = ["matricula", "nome", "cpf", "idade", "curso", "telefone"]

NOMES = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Gabriela", "Hugo",
         "Isabela", "João", "Karina", "Lucas", "Mariana", "Nicolas", "Olivia",
         "Pedro", "Rafael", "Sofia", "Thiago", "Victor"]
SOBRENOMES = ["Silva", "Costa", "Souza", "Alves", "Lima", "Dias", "Martins",
              "Rocha", "Pereira", "Nunes", "Gomes", "Barros", "Teixeira"]
CURSOS = ["Ciência da Computação", "Engenharia de Software", "Engenharia Elétrica",
          "Direito", "Medicina", "Administração", "Psicologia", "Física",
          "Matemática", "Design", "Economia"]

FATOR_ESPACO = 0.3  # 30% de cada bloco nasce vazio, reservado pra inserções futuras
FATOR_CARGA = 0.75  # ocupação máxima da tabela hash (chaves / posições disponíveis)


def gerar_matricula(ano, semestre, sequencial):
    aa = str(ano)[-2:].zfill(2)
    seq = str(sequencial).zfill(5)
    return f"{aa}{semestre}0{seq}"


# ---- CPF: a chave secundária da base ----

def so_digitos(texto):
    return "".join(c for c in texto if c.isdigit())


def formatar_cpf(digitos):
    return f"{digitos[:3]}.{digitos[3:6]}.{digitos[6:9]}-{digitos[9:]}"


def digito_verificador(digitos, peso_inicial):
    soma = sum(int(d) * peso for d, peso in zip(digitos, range(peso_inicial, 1, -1)))
    resto = (soma * 10) % 11
    return 0 if resto == 10 else resto


def cpf_valido(cpf):
    digitos = so_digitos(cpf)
    if len(digitos) != 11 or digitos == digitos[0] * 11:
        return False
    d1 = digito_verificador(digitos[:9], 10)
    d2 = digito_verificador(digitos[:9] + str(d1), 11)
    return digitos[9:] == f"{d1}{d2}"


def gerar_cpf(usados=None):
    """Sorteia um CPF com dígitos verificadores válidos. Se receber o conjunto
    de CPFs já usados, garante que o novo não repete nenhum deles."""
    while True:
        nove = "".join(str(random.randint(0, 9)) for _ in range(9))
        d1 = digito_verificador(nove, 10)
        d2 = digito_verificador(nove + str(d1), 11)
        digitos = f"{nove}{d1}{d2}"
        if usados is None:
            return formatar_cpf(digitos)
        if digitos not in usados:
            usados.add(digitos)
            return formatar_cpf(digitos)


def gerar_base(qtd=400, ano_inicio=2016, ano_fim=2024):
    base = []
    contador = {}
    cpfs_usados = set()
    for _ in range(qtd):
        ano = random.randint(ano_inicio, ano_fim)
        semestre = random.choice([1, 2])
        contador[(ano, semestre)] = contador.get((ano, semestre), 0) + 1

        base.append({
            "matricula": gerar_matricula(ano, semestre, contador[(ano, semestre)]),
            "nome": f"{random.choice(NOMES)} {random.choice(SOBRENOMES)}",
            "cpf": gerar_cpf(cpfs_usados),
            "idade": random.randint(17, 35),
            "curso": random.choice(CURSOS),
            "telefone": f"(61) 9{random.randint(1000,9999)}-{random.randint(1000,9999)}",
        })
    random.shuffle(base)
    return base


def salvar_csv(base, caminho):
    with open(caminho, "w", newline="", encoding="utf-8") as arq:
        escritor = csv.DictWriter(arq, fieldnames=CAMPOS)
        escritor.writeheader()
        escritor.writerows(base)


def carregar_csv(caminho):
    with open(caminho, "r", newline="", encoding="utf-8") as arq:
        base = list(csv.DictReader(arq))
    for registro in base:
        registro["idade"] = int(registro["idade"])
    return base


def completar_cpfs(base):
    """Bases geradas antes da coluna de CPF existir chegam aqui sem a chave
    secundária. Sorteia um CPF válido e inédito pra quem estiver sem, e devolve
    quantos foram preenchidos (pra avisar que o CSV precisa ser regravado)."""
    usados = {so_digitos(r["cpf"]) for r in base if r.get("cpf")}
    faltando = [r for r in base if not r.get("cpf")]
    for registro in faltando:
        registro["cpf"] = gerar_cpf(usados)
    return len(faltando)


def tamanho_bloco_disco(caminho="."):
    try:
        return os.statvfs(caminho).f_bsize
    except AttributeError:
        import ctypes
        setores = ctypes.c_ulonglong(0)
        bytes_setor = ctypes.c_ulonglong(0)
        livres = ctypes.c_ulonglong(0)
        total = ctypes.c_ulonglong(0)
        raiz = os.path.splitdrive(os.path.abspath(caminho))[0] + "\\"
        ok = ctypes.windll.kernel32.GetDiskFreeSpaceW(
            ctypes.c_wchar_p(raiz), ctypes.pointer(setores), ctypes.pointer(bytes_setor),
            ctypes.pointer(livres), ctypes.pointer(total)
        )
        return setores.value * bytes_setor.value if ok else 4096
    except OSError:
        return 4096


def registros_por_bloco(base, bloco_disco):
    media = statistics.mean(len(",".join(str(r[c]) for c in CAMPOS)) for r in base[:50])
    return max(1, int(bloco_disco // media))


# ---- tabela organizada (blocos com espaço vazio pra inserção futura) ----

def montar_blocos(base, capacidade):
    """Ordena a base e divide em blocos. Cada bloco só nasce parcialmente
    cheio - o resto fica com None, reservado pra quando chegar gente nova
    (assim não precisa reordenar tudo a cada aluno novo)."""
    ordenada = sorted(base, key=lambda r: r["matricula"])
    ocupacao = max(1, int(capacidade * (1 - FATOR_ESPACO)))

    blocos = []
    for i in range(0, len(ordenada), ocupacao):
        pedaco = ordenada[i:i + ocupacao]
        pedaco += [None] * (capacidade - len(pedaco))
        blocos.append(pedaco)
    return blocos


def montar_indice(blocos):
    # kindex: primeira matrícula (real, nunca vazia) de cada bloco + a posição
    return [(bloco[0]["matricula"], i) for i, bloco in enumerate(blocos)]


def extrair_base(blocos):
    return [r for bloco in blocos for r in bloco if r is not None]


def busca_binaria(indice, matricula):
    inicio, fim = 0, len(indice) - 1
    bloco = 0
    comparacoes = 0
    while inicio <= fim:
        meio = (inicio + fim) // 2
        comparacoes += 1
        if indice[meio][0] <= matricula:
            bloco = indice[meio][1]
            inicio = meio + 1
        else:
            fim = meio - 1
    return bloco, comparacoes


def busca_sequencial(bloco, matricula):
    comparacoes = 0
    for registro in bloco:
        if registro is None:
            break  # dali pra frente só tem espaço vazio, não tem mais o que olhar
        comparacoes += 1
        if registro["matricula"] == matricula:
            return registro, comparacoes
    return None, comparacoes


def buscar(blocos, indice, matricula):
    idx_bloco, comp_bin = busca_binaria(indice, matricula)
    registro, comp_seq = busca_sequencial(blocos[idx_bloco], matricula)
    return registro, comp_bin, comp_seq


# ---- tabela hash pela chave secundária (CPF) ----

def eh_primo(n):
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    divisor = 3
    while divisor * divisor <= n:
        if n % divisor == 0:
            return False
        divisor += 2
    return True


def proximo_primo(n):
    candidato = max(3, n | 1)  # primeiro ímpar >= n
    while not eh_primo(candidato):
        candidato += 2
    return candidato


def hash_cpf(cpf, tamanho):
    """Vai acumulando h = h * 31 + dígito (Horner) e fecha com o módulo pelo
    tamanho da tabela, que é primo justamente pra espalhar melhor as chaves.
    Só os dígitos entram na conta, então tanto faz digitar com ou sem pontuação."""
    h = 0
    for c in cpf:
        if c.isdigit():
            h = (h * 31 + (ord(c) - 48)) % tamanho
    return h


def montar_hash(base):
    """Monta a tabela com tratamento de colisão por encadeamento separado: cada
    posição guarda uma lista de pares (cpf, matrícula). O que fica guardado é a
    matrícula (a chave primária), e não a posição do registro - assim o índice
    continua valendo mesmo depois dos blocos serem reorganizados."""
    tamanho = proximo_primo(int(len(base) / FATOR_CARGA) + 1)
    tabela = [None] * tamanho
    for registro in base:
        inserir_hash(tabela, registro["cpf"], registro["matricula"])
    return tabela


def inserir_hash(tabela, cpf, matricula):
    posicao = hash_cpf(cpf, len(tabela))
    if tabela[posicao] is None:
        tabela[posicao] = []  # a lista só nasce quando a posição é usada de fato
    tabela[posicao].append((so_digitos(cpf), matricula))


def remover_hash(tabela, cpf):
    posicao = hash_cpf(cpf, len(tabela))
    chave = so_digitos(cpf)
    for i, (guardado, _) in enumerate(tabela[posicao] or []):
        if guardado == chave:
            tabela[posicao].pop(i)
            return True
    return False


def buscar_hash(tabela, cpf):
    """Cai direto na posição calculada e só percorre a lista que estiver lá."""
    posicao = hash_cpf(cpf, len(tabela))
    chave = so_digitos(cpf)
    comparacoes = 0
    for guardado, matricula in tabela[posicao] or []:
        comparacoes += 1
        if guardado == chave:
            return matricula, comparacoes
    return None, comparacoes


def redimensionar_hash(tabela, base):
    """Depois de muita inserção o fator de carga sobe, as listas encadeadas
    crescem e o hash começa a virar busca sequencial. Passando do limite, a
    tabela é refeita com mais posições e as chaves são reespalhadas."""
    if len(base) / len(tabela) <= FATOR_CARGA:
        return False
    tabela[:] = montar_hash(base)
    return True


def sortear_cpf_livre(tabela):
    """CPF sorteado que ainda não está na tabela (usado nos cadastros novos)."""
    cpf = gerar_cpf()
    while buscar_hash(tabela, cpf)[0] is not None:
        cpf = gerar_cpf()
    return cpf


def buscar_por_cpf(blocos, indice, tabela, cpf):
    """CPF -> matrícula pela tabela hash, e aí matrícula -> registro pelo kindex."""
    matricula, comp_hash = buscar_hash(tabela, cpf)
    if matricula is None:
        return None, comp_hash, 0, 0
    registro, comp_bin, comp_seq = buscar(blocos, indice, matricula)
    return registro, comp_hash, comp_bin, comp_seq


def estatisticas_hash(tabela):
    tamanhos = [len(lista) for lista in tabela if lista]
    chaves = sum(tamanhos)
    return {
        "tamanho": len(tabela),
        "chaves": chaves,
        "ocupadas": len(tamanhos),
        "colisoes": chaves - len(tamanhos),
        "maior_lista": max(tamanhos) if tamanhos else 0,
        "media_lista": chaves / len(tamanhos) if tamanhos else 0,
        "fator_carga": chaves / len(tabela),
    }


def inserir_no_bloco(bloco, registro):
    """Insere usando um dos espaços vazios do bloco. Retorna False se o
    bloco já está cheio (sem nenhum None sobrando)."""
    ocupados = [r for r in bloco if r is not None]
    if len(ocupados) >= len(bloco):
        return False

    ocupados.append(registro)
    ocupados.sort(key=lambda r: r["matricula"])
    vazios = [None] * (len(bloco) - len(ocupados))
    bloco[:] = ocupados + vazios
    return True


def maiores_sequenciais(blocos):
    """Maior sequencial já usado em cada prefixo de matrícula (ano + semestre)."""
    maiores = {}
    for bloco in blocos:
        for registro in bloco:
            if registro is not None:
                prefixo = registro["matricula"][:4]
                seq = int(registro["matricula"][-5:])
                if seq > maiores.get(prefixo, 0):
                    maiores[prefixo] = seq
    return maiores


def renumerar_lote(novos_alunos, maiores):
    """Um lote novo sempre começa a contar do 1, então as matrículas dele
    bateriam com as de quem já está cadastrado. Aqui cada uma continua da
    última usada naquele ano/semestre, pra matrícula seguir sendo chave única."""
    for aluno in novos_alunos:
        prefixo = aluno["matricula"][:4]
        maiores[prefixo] = maiores.get(prefixo, 0) + 1
        aluno["matricula"] = prefixo + str(maiores[prefixo]).zfill(5)


def inserir_lote(blocos, indice, novos_alunos):
    """Insere uma lista nova (ex: matrículas de um semestre que acabou de
    entrar, fora de ordem) um por um nos blocos certos. Se algum bloco
    encher no meio do caminho, devolve o que sobrou pra reconstruir."""
    for i, aluno in enumerate(novos_alunos):
        idx_bloco, _ = busca_binaria(indice, aluno["matricula"])
        if inserir_no_bloco(blocos[idx_bloco], aluno):
            indice[idx_bloco] = (blocos[idx_bloco][0]["matricula"], idx_bloco)
        else:
            return novos_alunos[i:]
    return []


def adicionar_aluno(blocos, indice, tabela, capacidade, caminho_csv):
    nome = input("Nome: ").strip()
    cpf = input("CPF (enter para sortear um): ").strip()
    if cpf:
        if not cpf_valido(cpf):
            print("\nCPF inválido - confira os dígitos verificadores.\n")
            return
        if buscar_hash(tabela, cpf)[0] is not None:
            print("\nJá tem aluno cadastrado com esse CPF.\n")
            return
        cpf = formatar_cpf(so_digitos(cpf))
    else:
        cpf = sortear_cpf_livre(tabela)
    idade = int(input("Idade: ").strip())
    curso = input("Curso: ").strip()
    telefone = input("Telefone: ").strip()
    ano = int(input("Ano de ingresso: ").strip())
    semestre = int(input("Semestre (1 ou 2): ").strip())

    prefixo = gerar_matricula(ano, semestre, 0)[:4]
    maior = maiores_sequenciais(blocos).get(prefixo, 0)
    matricula = gerar_matricula(ano, semestre, maior + 1)

    aluno = {"matricula": matricula, "nome": nome, "cpf": cpf, "idade": idade,
             "curso": curso, "telefone": telefone}

    idx_bloco, _ = busca_binaria(indice, matricula)
    if inserir_no_bloco(blocos[idx_bloco], aluno):
        indice[idx_bloco] = (blocos[idx_bloco][0]["matricula"], idx_bloco)
    else:
        print("Bloco cheio, reconstruindo a tabela...")
        base = extrair_base(blocos) + [aluno]
        blocos[:] = montar_blocos(base, capacidade)
        indice[:] = montar_indice(blocos)

    inserir_hash(tabela, cpf, matricula)
    base_atual = extrair_base(blocos)
    redimensionar_hash(tabela, base_atual)
    salvar_csv(base_atual, caminho_csv)
    print(f"\nAluno cadastrado com matrícula {matricula} e CPF {cpf}\n")


def remover_aluno(blocos, indice, tabela, caminho_csv):
    matricula = input("Matrícula a remover: ").strip()
    idx_bloco, _ = busca_binaria(indice, matricula)
    bloco = blocos[idx_bloco]

    ocupados_antes = [r for r in bloco if r is not None]
    removidos = [r for r in ocupados_antes if r["matricula"] == matricula]
    ocupados_depois = [r for r in ocupados_antes if r["matricula"] != matricula]

    if not removidos:
        print("\nMatrícula não encontrada.\n")
        return

    for registro in removidos:
        remover_hash(tabela, registro["cpf"])  # tira também do índice secundário

    vazios = [None] * (len(bloco) - len(ocupados_depois))
    bloco[:] = ocupados_depois + vazios

    if bloco[0] is not None:
        indice[idx_bloco] = (bloco[0]["matricula"], idx_bloco)

    salvar_csv(extrair_base(blocos), caminho_csv)
    print(f"\nAluno {matricula} removido.\n")


def main():
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alunos.csv")

    if os.path.exists(caminho):
        dados_iniciais = carregar_csv(caminho)
        sem_cpf = completar_cpfs(dados_iniciais)
        if sem_cpf:
            print(f"Base sem a coluna de CPF: sorteando CPF para {sem_cpf} aluno(s) e regravando o CSV...")
            salvar_csv(dados_iniciais, caminho)
    else:
        dados_iniciais = gerar_base(400)
        salvar_csv(dados_iniciais, caminho)

    bloco_disco = tamanho_bloco_disco()
    capacidade = registros_por_bloco(dados_iniciais, bloco_disco)
    blocos = montar_blocos(dados_iniciais, capacidade)
    indice = montar_indice(blocos)
    tabela = montar_hash(dados_iniciais)

    while True:
        print("=" * 55)
        print("  SISTEMA DE ALUNOS - BUSCA INDEXADA + HASH")
        print("=" * 55)
        print("1. Buscar aluno por matrícula")
        print("2. Buscar aluno por CPF (tabela hash)")
        print("3. Ver informações do índice/blocos/hash")
        print("4. Gerar nova base de dados (escolher quantidade)")
        print("5. Listar 10 matrículas de exemplo")
        print("6. Comparar dois tamanhos de bloco diferentes")
        print("7. Adicionar aluno")
        print("8. Remover aluno")
        print("9. Simular entrada de um novo semestre (lote de alunos)")
        print("10. Sair")
        opcao = input("Escolha uma opção: ").strip()

        if opcao == "1":
            matricula = input("Digite a matrícula: ").strip()
            registro, comp_bin, comp_seq = buscar(blocos, indice, matricula)
            if registro:
                print(f"\nAchado: {registro['nome']} | CPF {registro['cpf']} | {registro['idade']} anos | {registro['curso']}")
            else:
                print("\nNão encontrado.")
            print(f"Comparações -> binária no índice: {comp_bin} | sequencial no bloco: {comp_seq}\n")

        elif opcao == "2":
            cpf = input("Digite o CPF (com ou sem pontuação): ").strip()
            if not cpf_valido(cpf):
                print("\nCPF inválido - confira os dígitos verificadores.\n")
                continue
            registro, comp_hash, comp_bin, comp_seq = buscar_por_cpf(blocos, indice, tabela, cpf)
            if registro:
                print(f"\nAchado: {registro['nome']} | matrícula {registro['matricula']} | "
                      f"{registro['idade']} anos | {registro['curso']}")
                print(f"Comparações -> hash: {comp_hash} | binária no índice: {comp_bin} | "
                      f"sequencial no bloco: {comp_seq}\n")
            else:
                print(f"\nNão encontrado. (comparações no hash: {comp_hash})\n")

        elif opcao == "3":
            vazios = sum(1 for bloco in blocos for r in bloco if r is None)
            total = len(extrair_base(blocos))
            print(f"\nBloco do disco : {bloco_disco} bytes")
            print(f"Capacidade por bloco: {capacidade}")
            print(f"Quantidade de blocos: {len(blocos)}")
            print(f"Entradas no índice (kindex): {len(indice)}")
            print(f"Espaços vazios reservados: {vazios}")
            print(f"Total de alunos: {total}")
            info = estatisticas_hash(tabela)
            print(f"\nTabela hash (CPF) - posições: {info['tamanho']} (primo)")
            print(f"Chaves guardadas: {info['chaves']}")
            print(f"Posições ocupadas: {info['ocupadas']} | fator de carga: {info['fator_carga']:.2f}")
            print(f"Colisões (chaves além da 1ª de cada posição): {info['colisoes']}")
            print(f"Maior lista encadeada: {info['maior_lista']} | média das ocupadas: {info['media_lista']:.2f}\n")

        elif opcao == "4":
            qtd = input("Quantos alunos a nova base deve ter? ").strip()
            if qtd.isdigit():
                dados = gerar_base(int(qtd))
                capacidade = registros_por_bloco(dados, bloco_disco)
                blocos = montar_blocos(dados, capacidade)
                indice = montar_indice(blocos)
                tabela = montar_hash(dados)
                salvar_csv(dados, caminho)
                print(f"\nBase com {qtd} alunos gerada.\n")
            else:
                print("Quantidade inválida.\n")

        elif opcao == "5":
            print()
            for aluno in extrair_base(blocos)[:10]:
                print(f"  {aluno['matricula']} - {aluno['cpf']} - {aluno['nome']}")
            print()

        elif opcao == "6":
            outro = input("Digite outro tamanho de bloco para comparar (ex: 512, 8192): ").strip()
            if outro.isdigit():
                base_atual = extrair_base(blocos)
                capacidade2 = registros_por_bloco(base_atual, int(outro))
                blocos2 = montar_blocos(base_atual, capacidade2)
                print(f"\nBloco {bloco_disco} bytes -> {len(blocos)} blocos (capacidade {capacidade})")
                print(f"Bloco {outro} bytes -> {len(blocos2)} blocos (capacidade {capacidade2})\n")
            else:
                print("Valor inválido.\n")

        elif opcao == "7":
            adicionar_aluno(blocos, indice, tabela, capacidade, caminho)

        elif opcao == "8":
            remover_aluno(blocos, indice, tabela, caminho)

        elif opcao == "9":
            qtd = input("Quantos alunos novos chegaram nesse semestre? ").strip()
            if qtd.isdigit():
                novos = gerar_base(int(qtd))
                renumerar_lote(novos, maiores_sequenciais(blocos))
                for aluno in novos:
                    # o sorteio da base nova só evita repetir dentro do próprio
                    # lote; aqui o hash garante que não bate com quem já existe
                    aluno["cpf"] = sortear_cpf_livre(tabela)
                    inserir_hash(tabela, aluno["cpf"], aluno["matricula"])
                sobrando = inserir_lote(blocos, indice, novos)
                if sobrando:
                    print(f"\nOs blocos encheram, sobraram {len(sobrando)} alunos - reconstruindo a tabela...")
                    base = extrair_base(blocos) + sobrando
                    blocos[:] = montar_blocos(base, capacidade)
                    indice[:] = montar_indice(blocos)
                base_atual = extrair_base(blocos)
                if redimensionar_hash(tabela, base_atual):
                    print("Fator de carga passou do limite - tabela hash refeita com mais posições.")
                salvar_csv(base_atual, caminho)
                print(f"\n{qtd} alunos processados. Total agora: {len(base_atual)} alunos.\n")
            else:
                print("Quantidade inválida.\n")

        elif opcao == "10":
            print("Até mais!")
            break

        else:
            print("Opção inválida.\n")


if __name__ == "__main__":
    main()