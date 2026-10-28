// ==============================================================================
// FERROSTATS: DECLARACIÓN DE FUENTES BRONZE (RAW) EN BIGQUERY
// Lead Architect: Diego Alejandro Escobar Barahona
// ==============================================================================

const bronzeTables = [
  "raw_categories",
  "raw_suppliers",
  "raw_users",
  "raw_products",
  "raw_sales",
  "raw_sale_items",
  "raw_inventory_movements"
];

bronzeTables.forEach((table) => {
  declare({
    database: "ferrostats",
    schema: "ferrostats_bronze",
    name: table,
    description: `Tabla de origen crudo (Capa Bronze): ${table}`
  });
});
