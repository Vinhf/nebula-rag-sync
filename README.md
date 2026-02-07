## Run locally

docker build -t nebula-rag-sync .

docker run --rm -e OPENAI_API_KEY=sk-... nebula-rag-sync main.py

(Lệnh chạy một lần và exit 0 sau khi hoàn tất sync)