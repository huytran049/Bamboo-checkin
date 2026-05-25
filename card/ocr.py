import os
import time
import logging
import json
import subprocess
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image

# Initialize logger
logger = logging.getLogger("kiosk.card.ocr")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SWIFT_WORKER_PATH = PROJECT_ROOT / "workers_swift" / "ocr_worker.swift"

class SwiftReaderWrapper:
    def __init__(self):
        self.worker_path = str(SWIFT_WORKER_PATH)
        self.engine = self 
        logger.info(f"SwiftReaderWrapper initialized with worker: {self.worker_path}")

    def readtext(self, img, detail=0, paragraph=False):
        """
        Runs OCR and LLM extraction using the Swift worker.
        """
        t_start = time.time()
        
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
            try:
                if isinstance(img, np.ndarray):
                    if len(img.shape) == 3 and img.shape[2] == 3:
                        Image.fromarray(img).save(tmp_path)
                    else:
                        Image.fromarray(img).convert("RGB").save(tmp_path)
                elif isinstance(img, Image.Image):
                    img.save(tmp_path)
                else:
                    logger.error(f"Unsupported image type: {type(img)}")
                    return []
            except Exception as e:
                logger.error(f"Failed to save temporary image: {e}")
                return []

        try:
            cmd = ["swift", self.worker_path, tmp_path]
            logger.info(f"Calling Swift worker: {' '.join(cmd)}")
            
            # Use subprocess.run with timeout
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            # Log stderr regardless of success for debugging
            if result.stderr:
                logger.info(f"Swift worker stderr:\n{result.stderr}")

            if result.returncode != 0:
                logger.error(f"Swift worker failed with return code {result.returncode}")
                return []

            output = result.stdout.strip()
            
            # Robust JSON extracting from stdout
            start_idx = output.find('{')
            end_idx = output.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                logger.error(f"No JSON found in Swift worker output: {output}")
                return []
            
            json_str = output[start_idx:end_idx+1]
            
            try:
                data = json.loads(json_str)
                
                # Compatibility: Map 'name' to 'full_name' if needed
                if "name" in data and "full_name" not in data:
                    data["full_name"] = data.pop("name")
                
                # Ensure all values are strings (fix for SQLite dict binding error)
                for k, v in data.items():
                    if isinstance(v, (dict, list)):
                        data[k] = json.dumps(v, ensure_ascii=False)
                    else:
                        data[k] = str(v) if v is not None else ""
                
                logger.info(f"Swift worker extracted: {data}")
            except json.JSONDecodeError as je:
                logger.error(f"Failed to parse Swift worker output as JSON: {json_str}")
                logger.error(f"JSON Error: {je}")
                # Try simple cleaning of literal newlines if it failed
                try:
                    cleaned_json = json_str.replace('\n', '\\n').replace('\r', '\\r')
                    # But wait, we shouldn't replace newlines between keys/values.
                    # This is complex. For now, let's just log and return empty.
                    return []
                except:
                    return []

            if "error" in data and not any(k in data for k in ["name", "company"]):
                logger.error(f"Swift worker reported error: {data['error']}")
                return []

            if detail == 0:
                return [str(v) for v in data.values() if v]
            
            return data

        except subprocess.TimeoutExpired:
            logger.error("Swift worker timed out")
            return []
        except Exception as e:
            logger.exception(f"Error running Swift worker: {e}")
            return []
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass
            logger.info(f"OCR total time: {time.time() - t_start:.3f}s")

    def text_det(self, img):
        return [[ [0,0],[10,0],[10,10],[0,10] ]], None

_READER = None

def get_reader():
    global _READER
    if _READER is None:
        _READER = SwiftReaderWrapper()
    return _READER

def warmup_ocr(enable_llm=True, skip_llm_warmup=False):
    logger.info("Swift OCR worker is ready (no warmup needed)")
    pass

def _lazy_llm():
    return True
