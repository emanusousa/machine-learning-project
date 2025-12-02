FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libmagic1
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--reload"]
# CMD ["uvicorn", "main:app", "--host=0.0.0.0", "--port=8000", "--reload"]