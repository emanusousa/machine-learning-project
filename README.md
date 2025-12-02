# machine-learning-project

## Como rodar

### 1. Clonar o repositório

### 2. Criar o arquivo `.env`

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

### 3. Editar o `.env`

Preencha com suas credenciais (não faça commit deste arquivo):

```env
AWS_BUCKET=ml-data-storage-bucket
AWS_REGION=sa-east-1
AWS_ACCESS_KEY_ID=SEU_ACCESS_KEY_ID_AQUI
AWS_SECRET_ACCESS_KEY=SEU_SECRET_ACCESS_KEY_AQUI
```

### 4. Rodar o Docker Compose

```bash
docker compose up --build
```

### 5. Acessar a API

A API ficará disponível em:

```
http://localhost:8000/
```

### 6. Acessar o JUPYTER

```
http://127.0.0.1:8888/lab/workspaces/auto-J/tree/work/heart.ipynb

TOKEN = mlproject
```
