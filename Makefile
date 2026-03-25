run-server:
	uvicorn main:app --reload
run-db:
	docker compose up -d
