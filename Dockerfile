FROM python:3.9.5

RUN apt-get update && apt-get install -y wait-for-it

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY api_server /app/api_server

EXPOSE 8000

WORKDIR /app/api_server

CMD ["wait-for-it", "db:5432", "--", "./spin-up.sh"]
