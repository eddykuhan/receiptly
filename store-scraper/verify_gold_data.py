import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "receiptly")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DB_CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def main():
    print(f"Connecting to {DB_NAME} at {DB_HOST}...")
    try:
        engine = create_engine(DB_CONNECTION_STRING)
        with engine.connect() as conn:
            # Check total count
            result = conn.execute(text('SELECT COUNT(*) FROM purchase_analytics_gold'))
            total = result.scalar()
            print(f"Total rows in purchase_analytics_gold: {total}")
            
            # Check count by Source
            print("\nRows by Source:")
            result = conn.execute(text('SELECT "Source", COUNT(*) FROM purchase_analytics_gold GROUP BY "Source"'))
            for row in result:
                print(f"  {row[0] or 'NULL'}: {row[1]}")
                
            # Check count by StoreName for Scraper
            print("\nTop 10 Stores (Scraper):")
            query = """
                SELECT "StoreName", COUNT(*) 
                FROM purchase_analytics_gold 
                WHERE "Source" = 'Scraper'
                GROUP BY "StoreName"
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """
            result = conn.execute(text(query))
            for row in result:
                print(f"  {row[0]}: {row[1]}")
                
    except Exception as e:
        print(f"Error verification: {e}")

if __name__ == "__main__":
    main()
