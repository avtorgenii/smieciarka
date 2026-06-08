#!/bin/bash

# Configuration from environment or defaults
DB_USER=${DB_USER:-avtorpetrovich}
DB_NAME=${DB_NAME:-smieciarka_db}
CONTAINER_NAME="smieciarka-db-primary-1"

apply_indexes() {
    echo "Applying performance indexes to Primary ($CONTAINER_NAME)..."
    docker exec $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME -c "
        CREATE INDEX IF NOT EXISTS idx_photos_offer_id ON photos(offer_id);
        CREATE INDEX IF NOT EXISTS idx_reservations_offer_id ON reservations(offer_id);
        CREATE INDEX IF NOT EXISTS idx_offers_created_at ON offers(created_at DESC);
    "
    echo "Done. Changes will replicate to Standby automatically."
}

remove_indexes() {
    echo "Removing performance indexes from Primary ($CONTAINER_NAME)..."
    docker exec $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME -c "
        DROP INDEX IF EXISTS idx_photos_offer_id;
        DROP INDEX IF EXISTS idx_reservations_offer_id;
        DROP INDEX IF EXISTS idx_offers_created_at;
    "
    echo "Done."
}

case "$1" in
    apply)
        apply_indexes
        ;;
    remove)
        remove_indexes
        ;;
    *)
        echo "Usage: $0 {apply|remove}"
        exit 1
esac
