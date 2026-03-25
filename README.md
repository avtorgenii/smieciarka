# Setup

To create uv environment
```bash
uv sync
```

# Run
Init database, you need to have `.env` for it
```dotenv
DB_NAME=<>
DB_USER=<>
DB_PASSWORD=<>
```


```bash
make run-db
```

Run FastAPI server
```bash
make run-server
```