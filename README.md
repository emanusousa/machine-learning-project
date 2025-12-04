## Heart Disease – Pipeline de Dados e ML

Este projeto implementa uma pipeline completa para o **dataset de doenças cardíacas**:

- Carrega um CSV com dados de pacientes para o **ThingsBoard** (plataforma de IoT).
- Expõe um serviço **FastAPI** que lê a telemetria do ThingsBoard e salva o resultado em **CSV no S3**.
- Fornece um ambiente **Jupyter Notebook** para análise exploratória e modelagem de Machine Learning.

Tudo é orquestrado com **Docker Compose**, pensado para alguém que nunca viu o projeto antes.

---

## Visão geral da arquitetura

De forma simplificada, a arquitetura é composta por quatro blocos principais:

- **Ingestão IoT (ThingsBoard)**: o CSV de doenças cardíacas (`data/raw/heart.csv`) é enviado como telemetria para um dispositivo no ThingsBoard, simulando dados de sensores.
- **API de ingestão (FastAPI)**: um serviço FastAPI acessa a API do ThingsBoard, baixa toda a telemetria do dispositivo e consolida em um `pandas.DataFrame`.
- **Camada de armazenamento (AWS S3)**: o DataFrame consolidado é salvo como arquivo CSV em um bucket S3, servindo como "data lake" do projeto.
- **Análise e ML (Jupyter Notebooks)**: notebooks em `notebooks/` consomem os dados (via Snowflake/S3 ou localmente) para explorar o dataset e treinar modelos de Machine Learning.

Todos esses componentes são empacotados em containers Docker e orquestrados via `docker compose`, o que facilita subir e derrubar todo o ambiente com um único comando.

---

## 1. Pré‑requisitos

Você precisa ter instalado na sua máquina:

- **Docker** e **Docker Compose**
- **Git**

Para conferir:

```powershell
docker --version
docker compose version
```

---

## 2. Clonar o repositório

No PowerShell (Windows):

```powershell
cd "c:\Users\seu_usuario\Documents\GitHub"
git clone https://github.com/emanusousa/machine-learning-project.git
cd machine-learning-project
```

Se você já tem o repositório, apenas entre na pasta:

```powershell
cd "c:\Users\seu_usuario\Documents\GitHub\machine-learning-project"
```

---

## 3. Configurar variáveis de ambiente (FastAPI)

O serviço `fastapi` precisa de um arquivo `.env` com credenciais da AWS e acesso ao ThingsBoard.

Crie o arquivo `fastapi/.env` com o seguinte conteúdo (exemplo):

```env
AWS_BUCKET=ml-data-storage-bucket
AWS_REGION=sa-east-1
AWS_ACCESS_KEY_ID=SEU_ACCESS_KEY_ID_AQUI
AWS_SECRET_ACCESS_KEY=SEU_SECRET_ACCESS_KEY_AQUI

THINGSBOARD_URL=http://thingsboard:9090
THINGSBOARD_DEVICE_ID=37f2e300-d093-11f0-8a69-fbf8c35e0488
THINGSBOARD_TENANT_USER=tenant@thingsboard.org
THINGSBOARD_TENANT_PASSWORD=tenant
```

> Não faça commit deste arquivo. Use suas credenciais reais de AWS.

---

## 4. Subir toda a stack com Docker

Na raiz do projeto (`machine-learning-project`), execute:

```powershell
docker compose up --build
```

Ou, para rodar em segundo plano:

```powershell
docker compose up --build -d
```

Esse comando sobe os serviços:

- **fastapi** – API em `http://localhost:8000`.
- **jupyter** – ambiente de notebooks em `http://localhost:8888` (token `mlproject`).
- **thingsboard** – plataforma IoT em `http://localhost:8080`.
- **thingsboard-postgres** – banco usado pelo ThingsBoard.
- **tb-loader** – carrega o CSV `data/raw/heart.csv` e envia dados para o ThingsBoard.
- **heart-ingest** – chama a API FastAPI para ler os dados do ThingsBoard e salvar em CSV no S3.

Deixe o comando rodando e acompanhe os logs, especialmente de `tb-loader` e `heart-ingest`.

---

## 5. Acessar os serviços principais

### 5.1. API FastAPI

- URL base: `http://localhost:8000`

Endpoints importantes:

- `GET /` – checa se o serviço está no ar.
- `POST /ingest/heart` – lê a telemetria do ThingsBoard e grava um CSV no S3.

Exemplos rápidos (PowerShell):

```powershell
curl http://localhost:8000/
curl -X POST http://localhost:8000/ingest/heart
```

### 5.2. ThingsBoard

- URL: `http://localhost:8080`

Login padrão do tenant (se você não alterou):

- Usuário: `tenant@thingsboard.org`
- Senha: `tenant`

Por aqui você visualiza o dispositivo, telemetria e dashboards.

#### Configurando o dispositivo e tokens no ThingsBoard

Para que o serviço `tb-loader` envie corretamente os dados do CSV para o ThingsBoard, siga estes passos:

1. **Arquivos de ambiente**
  - Garanta que você tenha o `.env` da FastAPI configurado (seção 3 deste README), com as variáveis:
    - `THINGSBOARD_URL`
    - `THINGSBOARD_TENANT_USER`
    - `THINGSBOARD_TENANT_PASSWORD`
    - `THINGSBOARD_DEVICE_ID` (vamos preencher no passo 3).
  - Crie um arquivo `.env` na pasta `thingsboard/` para o loader, onde ficará o token do dispositivo:

  ```env
  THINGSBOARD_DEVICE_ACCESS_TOKEN=SEU_TOKEN_DO_DEVICE_AQUI
  ```

2. **Criar o Device no ThingsBoard**
  - Acesse `http://localhost:8080` e faça login como tenant.
  - Menu lateral → **Devices** → **Add new device**.
  - Dê um nome ao dispositivo (por exemplo, `heart-device`) e salve.

3. **Copiar Device ID e Access Token**
  - Ainda na tela do dispositivo recém-criado, vá em **Details**:
    - Copie o **Device ID** e cole no `.env` da FastAPI na variável `THINGSBOARD_DEVICE_ID`.
    - Copie o **Access token** do dispositivo e cole no `.env` da pasta `thingsboard/` na variável `THINGSBOARD_DEVICE_ACCESS_TOKEN`.

4. **Reiniciar os containers**
  - Depois de atualizar os arquivos `.env`, volte para a raiz do projeto e reinicie a stack:

  ```powershell
  docker compose down
  docker compose up --build
  ```

5. **Verificar a telemetria no ThingsBoard**
  - Com tudo rodando, acesse novamente o ThingsBoard.
  - Vá em **Devices**, clique no dispositivo que você criou.
  - Abra a aba **Latest telemetry**: ali você verá os dados do CSV `data/raw/heart.csv` sendo enviados pelo serviço `tb-loader`.

### 5.3. Jupyter Notebook

- URL: `http://127.0.0.1:8888`
- Token: `mlproject`

O notebook principal do projeto é:

- `notebooks/heart.ipynb`

Você pode abrir diretamente pelo navegador ou usar o link aproximado:

```text
http://127.0.0.1:8888/lab/tree/work/heart.ipynb
```

Depois, basta executar as células em ordem para reproduzir a análise e os modelos.

---

## 6. Fluxo resumido de dados

1. O Docker Compose sobe ThingsBoard, PostgreSQL, FastAPI, Jupyter e serviços auxiliares.
2. O serviço **tb-loader** lê `data/raw/heart.csv` e publica os dados como telemetria em um dispositivo no ThingsBoard.
3. O serviço **heart-ingest** faz uma chamada `POST` para `http://fastapi:8000/ingest/heart`.
4. O **FastAPI**:
	- Faz login no ThingsBoard.
	- Busca toda a telemetria do dispositivo.
	- Converte para `pandas.DataFrame`.
	- Salva um CSV no bucket S3 configurado no `.env`.
5. No **Jupyter**, você pode usar esses dados para análise e para treinar modelos de Machine Learning.

---

## 7. O que acontece automaticamente

Depois que você roda:

```powershell
docker compose up --build
```

e espera alguns minutos:

- O **ThingsBoard** e o banco **PostgreSQL** são iniciados e conectados.
- O container **`tb-loader`** instala as dependências do diretório `thingsboard/`, espera o ThingsBoard iniciar e executa automaticamente o script `csv_to_thingsboard.py`, que envia o CSV `data/raw/heart.csv` como telemetria para um dispositivo no ThingsBoard.
- Assim que o `tb-loader` termina com sucesso e os serviços **fastapi** e **thingsboard** estão de pé, o container **`heart-ingest`** roda automaticamente um `curl` para `http://fastapi:8000/ingest/heart`.
- A rota `/ingest/heart` do **FastAPI** faz o login no ThingsBoard, baixa toda a telemetria do dispositivo, converte para `pandas.DataFrame` e grava um novo CSV no bucket S3 configurado no seu `.env`.

Ou seja, ao final da subida da stack, você já terá:

- Dados carregados no ThingsBoard.
- Um CSV consolidado com a telemetria salvo no S3.
- A API FastAPI e o Jupyter prontos para serem usados sem rodar scripts manuais adicionais.

---

## 8. Monitorar experimentos com MLflow

O projeto utiliza **MLflow** nos notebooks para registrar métricas, parâmetros e modelos treinados. Os artefatos são salvos na pasta `mlruns/` na raiz do projeto.

Para visualizar esses experimentos em uma interface web, rode no PowerShell (a partir da raiz do projeto):

```powershell
cd "c:\Users\seu_usuario\Documents\GitHub\machine-learning-project"
mlflow ui --backend-store-uri "file://c:/Users/seu_usuario/Documents/GitHub/machine-learning-project/mlruns" --port 5000
```

> Observação: ajuste o caminho `c:\Users\seu_usuario\...` para o diretório em que o repositório foi clonado na sua máquina. O exemplo acima usa o caminho local do autor do projeto.

Depois abra no navegador:

```text
http://localhost:5000
```

Ali você poderá ver:

- Experimentos criados pelos notebooks (por exemplo, `heart_naive_bayes`).
- Runs com métricas (accuracy, F1, AUC, etc.), parâmetros testados e artifacts como matrizes de confusão e modelos salvos.

---

## 9. Parar os containers

Para desligar todos os serviços:

```powershell
docker compose down
```


---

## 10. Problemas comuns

- **Porta em uso (8000, 8080 ou 8888)**: feche o processo que está usando a porta ou altere as portas no `docker-compose.yml`.
- **Erro de credenciais AWS**: confira `AWS_BUCKET`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` em `fastapi/.env`.
- **Login no ThingsBoard falha**: verifique se o container `thingsboard` está saudável e se usuário/senha do tenant estão corretos.

## Membros
- **Disciplina**: Aprendizado de Máquina - 2025.2.
- **Instituição**: CESAR School.
<table>
  <tr>
    <td align="center">
      <a href="https://github.com/emanusousa">
        <img src="https://avatars.githubusercontent.com/emanusousa" width="100px;" alt="Foto de Emanuel Eduardo"/>
        <br />
        <sub><b>Emanuel Eduardo </b></sub>
      </a>
      <br />
      <sub><b>✉️ eess2@cesar.school</b></sub>
    </td>
    <td align="center">
      <a href="https://github.com/TalitaFraga">
        <img src="https://avatars.githubusercontent.com/u/69424132?v=4" width="100px;" alt="Foto de Talita"/>
        <br />
        <sub><b>Talita Fraga</b></sub>
      </a>
      <br />
      <sub><b>✉️ tdlf@cesar.school</b></sub>
    </td>
    <td align="center">
      <a href="https://github.com/brunoribeirol">
        <img src="https://avatars.githubusercontent.com/u/89156916?v=4" width="100px;" alt="Foto de Bruno"/>
        <br />
        <sub><b>Bruno Ribeiro</b></sub>
      </a>
      <br />
      <sub><b>✉️ brlla@cesar.school</b></sub>
    </td>
     <td align="center">
        <a href="https://github.com/igoralvesa">
           <img src="https://avatars.githubusercontent.com/u/101803586?v=4" width="100px;" alt="Foto de Igor"/>
           <br />
           <sub><b>Igor Alves</b></sub>
        </a>
        <br />
        <sub><b>✉️ iaa@cesar.school</b></sub>
     </td>
	<td align="center">
        <a href="https://github.com/juliafelixcor">
           <img src="https://avatars.githubusercontent.com/u/98843736?v=4" width="100px;" alt="Foto de Julia"/>
           <br />
           <sub><b>Julia Felix</b></sub>
        </a>
        <br />
        <sub><b>✉️  jfc@cesar.school</b></sub>
     </td>
	<td align="center">
        <a href="https://github.com/Victorgalves">
           <img src="https://avatars.githubusercontent.com/u/99843784?v=4" width="100px;" alt="Foto de Victor"/>
           <br />
           <sub><b>Victor Guilherme</b></sub>
        </a>
        <br />
        <sub><b>✉️  jfc@cesar.school</b></sub>
     </td>
  </tr>
</table>


