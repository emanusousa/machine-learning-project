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

Se também quiser remover os volumes (apagando dados persistidos como o banco do ThingsBoard):

```powershell
docker compose down -v
```

---

## 10. Problemas comuns

- **Porta em uso (8000, 8080 ou 8888)**: feche o processo que está usando a porta ou altere as portas no `docker-compose.yml`.
- **Erro de credenciais AWS**: confira `AWS_BUCKET`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` em `fastapi/.env`.
- **Login no ThingsBoard falha**: verifique se o container `thingsboard` está saudável e se usuário/senha do tenant estão corretos.

