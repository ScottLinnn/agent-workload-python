import os
import sys
import json
import lancedb
from lancedb.pydantic import LanceModel, Vector

# Add repo root to path to import from agentic_rag
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_PATH not in sys.path:
    sys.path.append(ROOT_PATH)

from agentic_rag.adk.tools import _get_embedding, get_db_dir

def generate_mock_data():
    import shutil
    db_dir = get_db_dir()
    print(f"=== Generating LanceDB Data at {db_dir} ===")
    
    print(f"Cleaning up data in {db_dir} before creating new data...")
    if db_dir.startswith("gs://"):
        try:
            from google.cloud import storage
            parts = db_dir[5:].split("/", 1)
            bucket_name = parts[0]
            prefix = parts[1] if len(parts) > 1 else ""
            if bucket_name:
                client = storage.Client()
                bucket = client.bucket(bucket_name)
                blobs = bucket.list_blobs(prefix=prefix)
                count = 0
                for blob in blobs:
                    blob.delete()
                    count += 1
                print(f"Cleaned up {count} blobs from GCS directory {db_dir}")
        except Exception as e:
            print(f"ERROR: Failed to clean up GCS directory {db_dir}: {e}")
            raise e
    else:
        if os.path.exists(db_dir):
            shutil.rmtree(db_dir, ignore_errors=True)
            
    if not db_dir.startswith("gs://"):
        os.makedirs(db_dir, exist_ok=True)
    db = lancedb.connect(db_dir)
    
    table_name = "documents"
    
    # Define schema
    class Document(LanceModel):
        vector: Vector(768)
        content: str
        metadata: str
        
    sample_texts = [
        "Tactical Deployment: Operation Night Owl. Operation Night Owl will commence on Tuesday at 0200 hours. The primary objective is to survey the northern perimeter of the facility without alerting ground patrols. To achieve the required stealth and altitude, the reconnaissance team will not use the standard Alpha-series drones. Instead, they will be deploying the newly acquired AeroScout X-4 drone, which has been cleared for all nocturnal stealth operations.",
        "AeroScout X-4 UAV Specifications. The AeroScout X-4 is a lightweight reconnaissance UAV designed for silent, high-altitude surveillance. It features dual 4K night-vision cameras, a carbon-fiber chassis, and a proprietary silent-propulsion system. To maintain its low weight profile while powering the advanced optics, the X-4 relies on a customized lithium-sulfur power cell (designated as Model LS-900), completely bypassing traditional lithium-ion architecture.",
        "Q3 Power Cell and Battery Inventory Specs. Hardware specifications for active field power cells: * Standard Li-Ion Pack (Model B-20): Provides 4000mAh, used in Alpha-series drones. * Heavy Duty Li-Ion Pack (Model B-40): Provides 6000mAh, used in ground rovers. * Model LS-900 (Lithium-Sulfur): This experimental power cell is currently exclusive to X-series aerial vehicles. It boasts an impressive capacity of 8500mAh and provides a maximum continuous flight time of 45 minutes under standard atmospheric conditions."
    ]
    
    data = []
    for i, text in enumerate(sample_texts):
        print(f"Generating embedding for: {text}")
        try:
            vector = _get_embedding(text)
        except Exception as e:
            print(f"Failed to get real embedding, using dummy: {e}")
            vector = [0.1] * 768
            
        data.append({
            "vector": vector,
            "content": text,
            "metadata": json.dumps({"source": f"sample_{i}.txt"})
        })
        
    print(f"Creating table '{table_name}' (overwriting if exists)...")
    table = db.create_table(table_name, data=data, mode="overwrite")

    print(f"Table '{table_name}' created with {len(sample_texts)} rows.")

if __name__ == "__main__":
    generate_mock_data()
