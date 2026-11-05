// ==============================================================================
// FERROSTATS: BRONZE LAYER SOURCE DECLARATIONS (Google BigQuery)
// Lead Architect: Diego Alejandro Escobar Barahona
// Cost Policy: $0.00 USD (Google Cloud Free Tier)
// ==============================================================================

declare({
  database: "ferrostats",
  schema: "ferrostats_bronze",
  name: "raw_sales",
  description: "Immutable raw POS sales header stream ingested from the SQLite WAL edge engine."
});

declare({
  database: "ferrostats",
  schema: "ferrostats_bronze",
  name: "raw_sale_items",
  description: "Immutable raw POS line-item breakdown with historical unit cost and price snapshots."
});

declare({
  database: "ferrostats",
  schema: "ferrostats_bronze",
  name: "raw_products",
  description: "Master hardware SKU catalog synchronized from the operational store."
});

declare({
  database: "ferrostats",
  schema: "ferrostats_bronze",
  name: "raw_categories",
  description: "Hardware product categories and target gross margin thresholds."
});

declare({
  database: "ferrostats",
  schema: "ferrostats_bronze",
  name: "raw_suppliers",
  description: "Hardware suppliers and replenishment lead times in days."
});

declare({
  database: "ferrostats",
  schema: "ferrostats_bronze",
  name: "raw_inventory_movements",
  description: "Immutable ledger of physical stock movements and warehouse aisle audit adjustments."
});
