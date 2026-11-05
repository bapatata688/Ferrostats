flowchart TD
    subgraph ClientLayer["1. Edge Event Producers (SDD Web / POS Simulators)"]
        UI_POS["POS Cashier Terminal (/pos)\nSynthetic Transaction Producer"]
        UI_BI["Warehouse & BI Portal (/)\nAisle Audit & Embedded Looker BI"]
    end

    subgraph ServerlessLayer["2. Cloud Run Serverless Edge (Scale-to-Zero — $0.00 USD)"]
        FastAPI["FastAPI Ingestion & REST API (Python 3.11)"]
        
        subgraph IngestaOLTP["Local Edge OLTP Engine"]
            SQLite["SQLite WAL\n• BEGIN IMMEDIATE ACID (< 50 ms)\n• 3NF Operational Schema"]
        end

        subgraph EngineETL["Hybrid Data Engineering Pipeline"]
            Extract["Extract & Stream: Sales & Movements"]
            DQ["6 Data Quality Gates (Assertions)"]
            Transform["Transform: 80/20 Pareto ABC, Burn Rate, DOI, ROP"]
            Load["Load: Star Schema OLAP Marts"]
        end

        FastAPI --> IngestaOLTP
        IngestaOLTP --> EngineETL
    end

    subgraph AnalyticsLayer["3. Google Cloud Medallion Lakehouse ($0.00 USD Free Tier)"]
        Bronze["BigQuery Bronze (ferrostats_bronze)\n• raw_sales, raw_sale_items\n• raw_products, raw_inventory_movements"]
        Silver["Dataform Silver Views (ferrostats_silver)\n• stg_sales, stg_sale_items, stg_products\n• uniqueKey, nonNull, rowConditions"]
        Gold["BigQuery Gold Star Marts (ferrostats_gold)\n• fct_daily_sales\n• mart_inventory_pareto_abc\n• dim_products"]
        Looker["Google Looker Studio (3-Page Executive BI)"]
        
        EngineETL -.->|"bigquery_sync.py (Async REST Stream)"| Bronze
        Bronze --> Silver
        Silver --> Gold
        Gold --> Looker
        Looker -.-> UI_BI
    end

    UI_POS --> FastAPI
    UI_BI --> FastAPI
