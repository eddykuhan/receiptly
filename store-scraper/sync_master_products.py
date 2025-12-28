import os
import uuid
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables from current dir or root
load_dotenv()
load_dotenv("../.env")

# Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "receiptly")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DB_CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def main():
    print("Starting master product synchronization...")
    engine = create_engine(DB_CONNECTION_STRING)
    
    # 1. Fetch unique products from scraped data in the gold layer
    # We use DISTINCT ON ("ItemName") to get one record per product name.
    # We prefer the most recent one for category/brand info.
    query = """
    SELECT DISTINCT ON ("ItemName")
        "ItemName", "Category", "Source", "PurchaseDate"
    FROM purchase_analytics_gold
    WHERE "Source" = 'Scraper'
    ORDER BY "ItemName", "PurchaseDate" DESC
    """
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return
        
    print(f"Found {len(df)} unique products in scraped data.")
    
    if df.empty:
        print("No scraped data found to sync.")
        return

    # 2. Extract Brand (Simple heuristic for now)
    def parse_brand(name):
        brands = ["Farm Fresh", "Dutch Lady", "F&N", "Milo", "Nestle", "Anchor", "Fernleaf", "Anlene"]
        for b in brands:
            if b.lower() in name.lower():
                return b
        return None

    df['Brand'] = df['ItemName'].apply(parse_brand)
    
    # 3. Synchronize to master_products table
    print("Syncing to master_products table (Upserting based on Name)...")
    
    count = 0
    with engine.begin() as conn:
        for _, row in df.iterrows():
            # We use Name as a unique identifier for synchronization
            conn.execute(text("""
                INSERT INTO master_products ("Id", "Name", "Category", "Brand", "Source", "CreatedAt")
                VALUES (:Id, :Name, :Category, :Brand, :Source, :CreatedAt)
                ON CONFLICT ("Name") DO UPDATE SET
                    "Category" = EXCLUDED."Category",
                    "Brand" = EXCLUDED."Brand",
                    "Source" = EXCLUDED."Source"
            """), {
                "Id": str(uuid.uuid4()),
                "Name": row["ItemName"],
                "Category": row["Category"],
                "Brand": row["Brand"],
                "Source": row["Source"],
                "CreatedAt": pd.Timestamp.now(tz='UTC')
            })
            count += 1
            
    print(f"Successfully synchronized {count} products!")

if __name__ == "__main__":
    main()
