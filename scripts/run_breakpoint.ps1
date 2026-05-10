param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$Path = "/offers",
  [string]$Method = "GET",
  [int]$RequestsPerStep = 1000,
  [string]$Concurrency = "100,150,200,250,300,350",
  [string]$OutPrefix = "ramp",
  [int]$Users = 100
)

# Optional auth (set as env vars):
#   $env:BENCH_EMAIL="you@email"
#   $env:BENCH_PASSWORD="your_password"

uv run python scripts/breakpoint_ramp.py `
  --base-url $BaseUrl `
  --path $Path `
  --method $Method `
  --requests-per-step $RequestsPerStep `
  --concurrency $Concurrency `
  --users $Users `
  --out-prefix $OutPrefix

