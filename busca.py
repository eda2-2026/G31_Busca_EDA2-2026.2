import csv
import os
import random
import statistics

CAMPOS = ["matricula", "nome", "idade", "curso", "telefone"]

NOMES = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Gabriela", "Hugo",
         "Isabela", "João", "Karina", "Lucas", "Mariana", "Nicolas", "Olivia",
         "Pedro", "Rafael", "Sofia", "Thiago", "Victor"]
SOBRENOMES = ["Silva", "Costa", "Souza", "Alves", "Lima", "Dias", "Martins",
              "Rocha", "Pereira", "Nunes", "Gomes", "Barros", "Teixeira"]
CURSOS = ["Ciência da Computação", "Engenharia de Software", "Engenharia Elétrica",
          "Direito", "Medicina", "Administração", "Psicologia", "Física",
          "Matemática", "Design", "Economia"]

FATOR_ESPACO = 0.3  # 30% de cada bloco nasce vazio, reservado pra inserções futuras


def gerar_matricula(ano, semestre, sequencial):
    aa = str(ano)[-2:].zfill(2)
    seq = str(sequencial).zfill(5)
    return f"{aa}{semestre}0{seq}"


def gerar_base(qtd=400, ano_inicio=2016, ano_fim=2024):
    base = []
    contador = {}
    for _ in range(qtd):
        ano = random.randint(ano_inicio, ano_fim)
        semestre = random.choice([1, 2])
        contador[(ano, semestre)] = contador.get((ano, semestre), 0) + 1

        base.append({
            "matricula": gerar_matricula(ano, semestre, contador[(ano, semestre)]),
            "nome": f"{random.choice(NOMES)} {random.choice(SOBRENOMES)}",
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


def adicionar_aluno(blocos, indice, capacidade, caminho_csv):
    nome = input("Nome: ").strip()
    idade = int(input("Idade: ").strip())
    curso = input("Curso: ").strip()
    telefone = input("Telefone: ").strip()
    ano = int(input("Ano de ingresso: ").strip())
    semestre = int(input("Semestre (1 ou 2): ").strip())

    prefixo = gerar_matricula(ano, semestre, 0)[:4]
    maior = 0
    for bloco in blocos:
        for r in bloco:
            if r is not None and r["matricula"].startswith(prefixo):
                maior = max(maior, int(r["matricula"][-5:]))
    matricula = gerar_matricula(ano, semestre, maior + 1)

    aluno = {"matricula": matricula, "nome": nome, "idade": idade, "curso": curso, "telefone": telefone}

    idx_bloco, _ = busca_binaria(indice, matricula)
    if inserir_no_bloco(blocos[idx_bloco], aluno):
        indice[idx_bloco] = (blocos[idx_bloco][0]["matricula"], idx_bloco)
    else:
        print("Bloco cheio, reconstruindo a tabela...")
        base = extrair_base(blocos) + [aluno]
        blocos[:] = montar_blocos(base, capacidade)
        indice[:] = montar_indice(blocos)

    salvar_csv(extrair_base(blocos), caminho_csv)
    print(f"\nAluno cadastrado com matrícula {matricula}\n")


def remover_aluno(blocos, indice, caminho_csv):
    matricula = input("Matrícula a remover: ").strip()
    idx_bloco, _ = busca_binaria(indice, matricula)
    bloco = blocos[idx_bloco]

    ocupados_antes = [r for r in bloco if r is not None]
    ocupados_depois = [r for r in ocupados_antes if r["matricula"] != matricula]

    if len(ocupados_depois) == len(ocupados_antes):
        print("\nMatrícula não encontrada.\n")
        return

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
    else:
        dados_iniciais = gerar_base(400)
        salvar_csv(dados_iniciais, caminho)

    bloco_disco = tamanho_bloco_disco()
    capacidade = registros_por_bloco(dados_iniciais, bloco_disco)
    blocos = montar_blocos(dados_iniciais, capacidade)
    indice = montar_indice(blocos)

    while True:
        print("=" * 55)
        print("  SISTEMA DE ALUNOS - BUSCA INDEXADA + HASH")
        print("=" * 55)
        print("1. Buscar aluno por matrícula")
        print("2. Buscar aluno(s) por nome")
        print("3. Ver informações do índice/blocos")
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
                print(f"\nAchado: {registro['nome']} | {registro['idade']} anos | {registro['curso']}")
            else:
                print("\nNão encontrado.")
            print(f"Comparações -> binária no índice: {comp_bin} | sequencial no bloco: {comp_seq}\n")

        elif opcao == "2":
            # TODO: sua dupla implementa a busca por nome usando a tabela hash deles aqui
            print("\nAinda não implementado - falta o hash da dupla.\n")

        elif opcao == "3":
            vazios = sum(1 for bloco in blocos for r in bloco if r is None)
            total = len(extrair_base(blocos))
            print(f"\nBloco do disco : {bloco_disco} bytes")
            print(f"Capacidade por bloco: {capacidade}")
            print(f"Quantidade de blocos: {len(blocos)}")
            print(f"Entradas no índice (kindex): {len(indice)}")
            print(f"Espaços vazios reservados: {vazios}")
            print(f"Total de alunos: {total}\n")

        elif opcao == "4":
            qtd = input("Quantos alunos a nova base deve ter? ").strip()
            if qtd.isdigit():
                dados = gerar_base(int(qtd))
                capacidade = registros_por_bloco(dados, bloco_disco)
                blocos = montar_blocos(dados, capacidade)
                indice = montar_indice(blocos)
                salvar_csv(dados, caminho)
                print(f"\nBase com {qtd} alunos gerada.\n")
            else:
                print("Quantidade inválida.\n")

        elif opcao == "5":
            print()
            for aluno in extrair_base(blocos)[:10]:
                print(f"  {aluno['matricula']} - {aluno['nome']}")
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
            adicionar_aluno(blocos, indice, capacidade, caminho)

        elif opcao == "8":
            remover_aluno(blocos, indice, caminho)

        elif opcao == "9":
            qtd = input("Quantos alunos novos chegaram nesse semestre? ").strip()
            if qtd.isdigit():
                novos = gerar_base(int(qtd))
                sobrando = inserir_lote(blocos, indice, novos)
                if sobrando:
                    print(f"\nOs blocos encheram, sobraram {len(sobrando)} alunos - reconstruindo a tabela...")
                    base = extrair_base(blocos) + sobrando
                    blocos[:] = montar_blocos(base, capacidade)
                    indice[:] = montar_indice(blocos)
                salvar_csv(extrair_base(blocos), caminho)
                print(f"\n{qtd} alunos processados. Total agora: {len(extrair_base(blocos))} alunos.\n")
            else:
                print("Quantidade inválida.\n")

        elif opcao == "10":
            print("Até mais!")
            break

        else:
            print("Opção inválida.\n")


if __name__ == "__main__":
    main()