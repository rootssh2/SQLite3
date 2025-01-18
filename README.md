# SQLite_Dump V3

## Visão Geral
**SQLite_Dump V3** é uma ferramenta em Python projetada para gerenciar credenciais de arquivos de texto para um banco de dados SQLite, realizar buscas e limpar listas de palavras. Esta ferramenta é particularmente útil para lidar com credenciais de login em grandes quantidades, oferecendo funcionalidades para:

- Inserir credenciais de arquivos `.txt` em um banco de dados SQLite.
- Buscar credenciais com base em um termo e salvar os resultados.
- Limpar e filtrar listas de palavras com base em diferentes critérios.

## Recursos

- **Gerenciamento de Banco de Dados**: 
  - Cria automaticamente uma tabela chamada `credentials` no SQLite para armazenar `url`, `login` e `senha`.
  - Inserção em massa de credenciais de arquivos de texto no banco de dados.

- **Funcionalidade de Busca**: 
  - Busca no banco de dados por termos específicos em `url`, `login` ou `senha`.
  - Salva os resultados da pesquisa em um novo arquivo `.txt`.

- **Limpeza de Lista de Palavras**: 
  - Diversos filtros para limpar listas de palavras:
    - **Email** - Extrai pares de email e senha.
    - **IPTV** - Extrai nome de usuário e senha de padrões de URL específicos.
    - **Number** - Combina logins numéricos com senhas.
    - **Login** - Filtro geral para o formato login:senha, excluindo entradas inválidas como `UNKNOWN`, `NOT_SAVED` ou marcadores encriptados.

- **Interface de Usuário**: 
  - Menu baseado em linha de comando para facilidade de uso.

## Uso

Para usar o SQLite_Dump V3, siga estes passos:

1. **Pré-requisitos**:
   - Python 3.x instalado
   - Módulo `sqlite3` (vem com o Python)

2. **Instalação**:
   - Clone este repositório:
     ```bash
     git clone https://github.com/rootssh2/SQLite3_Dump-V3.git
     cd SQLite_Dump-V3
     ```

3. **Executando a Ferramenta**:
   - Navegue até o diretório contendo `SQLite3_Dump-V3.py`:
     ```bash
     python SQLite3_Dump-V3.py
     ```

4. **Opções do Menu**:
   - **1**: Adicionar arquivos `.txt` ao banco de dados
   - **2**: Consultar logins
   - **3**: Limpar wordlist
   - **4**: Sair

   Siga as instruções na tela para selecionar arquivos, escolher filtros ou inserir termos de busca.

## Estrutura de Diretório

- `txt_to_db/` - Armazene seus arquivos `.txt` aqui para serem processados no banco de dados.
- `resultados/` - Diretório onde os resultados de busca são salvos.
- `wordlist/` - Onde as listas de palavras limpas são geradas.

## Notas

- Certifique-se de que seus arquivos `.txt` estão formatados corretamente com credenciais de login separadas por ':' ou '|'.
- A ferramenta não lida com codificações de arquivos diferentes de UTF-8.

## Contribuição

Contribuições são bem-vindas! Por favor, faça um fork deste repositório e envie um pull request com suas mudanças. Aqui estão algumas maneiras de contribuir:

- Correção de bugs
- Solicitações de novos recursos
- Melhoria na documentação
- Melhorias de desempenho ou segurança

## Contato

Para perguntas ou suporte, entre em contato pelo Telegram: @Root2022

---

Feito com 💙 por root.xyz
