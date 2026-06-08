# Configuration
$DB_USER = if ($env:DB_USER) { $env:DB_USER } else { "avtorpetrovich" }
$DB_NAME = if ($env:DB_NAME) { $env:DB_NAME } else { "smieciarka_db" }
$CONTAINER_NAME = "smieciarka-db-primary-1"

function Apply-Indexes {
    Write-Host "Applying performance indexes to Primary ($CONTAINER_NAME)..." -ForegroundColor Green
    docker exec $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME -c "
        CREATE INDEX IF NOT EXISTS idx_photos_offer_id ON photos(offer_id);
        CREATE INDEX IF NOT EXISTS idx_reservations_offer_id ON reservations(offer_id);
        CREATE INDEX IF NOT EXISTS idx_offers_created_at ON offers(created_at DESC);
    "
    Write-Host "Done. Changes will replicate to Standby automatically."
}

function Remove-Indexes {
    Write-Host "Removing performance indexes from Primary ($CONTAINER_NAME)..." -ForegroundColor Yellow
    docker exec $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME -c "
        DROP INDEX IF EXISTS idx_photos_offer_id;
        DROP INDEX IF EXISTS idx_reservations_offer_id;
        DROP INDEX IF EXISTS idx_offers_created_at;
    "
    Write-Host "Done."
}

$action = $args[0]

switch ($action) {
    "apply"  { Apply-Indexes }
    "remove" { Remove-Indexes }
    default  { 
        Write-Host "Usage: .\manage_indexes.ps1 {apply|remove}" -ForegroundColor Cyan 
    }
}
