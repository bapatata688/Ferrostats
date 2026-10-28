flowchart TD
    subgraph ClientLayer["1. Clientes Web & Móvil (POS / Bodega)"]
        UI_POS["Terminal Caja / POS (Móvil & Desktop)"]
        UI_BI["Portal Gerencial (Bodega & Bento BI)"]
    end

    subgraph ServerlessLayer["2. Cloud Run (Scale-to-Zero — $0.00 USD)"]
        FastAPI["API REST FastAPI (Python 3.11)"]
        
        subgraph IngestaOLTP["Motor Transaccional (OLTP)"]
            SQLite["SQLite WAL (/tmp in-memory)<br/>• ACID Atómico (&lt; 5 ms)<br/>• 3ra Forma Normal"]
        end

        subgraph EngineETL["Motor ETL de Ingeniería de Datos"]
            Extract["Extract: Ventas & Movimientos"]
            DQ["6 Data Quality Gates (Validación)"]
            Transform["Transform: Pareto 80/20 ABC, Burn Rate, DOI, ROP"]
            Load["Load: Esquema Estrella OLAP"]
        end

        FastAPI --> IngestaOLTP
        IngestaOLTP --> EngineETL
    end

    subgraph AnalyticsLayer["3. Capa Analítica & Data Warehouse ($0.00 USD)"]
        StarSchema["Esquema Estrella Local<br/>• dw_fact_daily_sales<br/>• dw_mart_product_abc_health"]
        BQ["Google BigQuery Free Tier (Sandbox)<br/>• Dataset: ferrostats_dw<br/>• 10 GB almacenamiento gratis<br/>• 1 TB consultas/mes gratis"]
        Looker["Looker Studio (Embebido)"]
        
        EngineETL --> StarSchema
        EngineETL -.->|"bigquery_sync.py (Micro-Batch)"| BQ
        BQ -.-> Looker
        StarSchema --> UI_BI
    end

    UI_POS --> FastAPI
    UI_BI --> FastAPI
