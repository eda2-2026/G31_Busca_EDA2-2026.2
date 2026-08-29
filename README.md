# G31_Busca_EDA2-2026.2
Repositório dedicado ao Trabalho 1 de Estruturas de Dados 2 do 2º semestre de 2026.

## Alunos  
| Matrícula | Nome |  
|-----------------------|---------------------|  
| 2X/XXXXXXX | ANA LUISA VIERIA NUNES |  
| 22/2006113 | JOÃO MARCOS MORAES DE ANDRADE |  

## Descrição do projeto

O projeto implementa um sistema de cadastro e busca de alunos combinando duas técnicas de Estruturas de Dados:

- **Busca sequencial indexada (kindex):** a base de alunos é ordenada por matrícula e dividida em blocos, com o mesmo tamanho do bloco de leitura do disco do computador (detectado automaticamente, geralmente 4096 bytes). Um índice (kindex) guarda só a primeira matrícula de cada bloco. Uma busca primeiro faz **busca binária** no kindex para achar o bloco certo, e depois **busca sequencial** só dentro daquele bloco — evitando percorrer a base inteira a cada consulta.
- **Espaço reservado nos blocos:** cada bloco nasce com uma parte vazia (30% de folga), permitindo inserir alunos novos direto no bloco certo sem precisar reordenar a base inteira toda vez. Só quando um bloco enche de verdade é que a estrutura é reconstruída.
- **Tabela hash por chave secundária (CPF):** em andamento — vai permitir buscar um aluno também pelo CPF, usando hashing com tratamento de colisão.

O sistema permite cadastrar, buscar, remover e simular a entrada de novos alunos (ex: matrículas de um novo semestre), persistindo tudo em um arquivo CSV.

## Guia de instalação

### Dependências do projeto

- Python 3.10 ou superior
- Nenhuma biblioteca externa é necessária — o projeto usa apenas módulos padrão do Python (`csv`, `os`, `random`, `statistics`)

### Como executar o projeto

1. Clone este repositório:
   ```
   git clone https://github.com/<usuario>/G31_Busca_EDA2-2026.2.git
   cd G31_Busca_EDA2-2026.2
   ```
2. Execute o programa:
   ```
   python busca.py
   ```
   (no Windows, pode ser necessário usar `py busca.py`)
3. Um menu interativo será exibido no terminal, com as opções de busca, cadastro, remoção e simulação de novos semestres.

## Capturas de tela

*(adicionar aqui prints do menu rodando, de uma busca por matrícula e do relatório de blocos/índice)*

## Conclusões

*(escrever depois de finalizado: o que funcionou bem, dificuldades encontradas, comparação de desempenho entre busca sequencial pura, busca indexada e hash)*

## Referências

- Material e slides da disciplina de Estruturas de Dados 2 (EDA2)
- Documentação oficial do Python: https://docs.python.org/3/