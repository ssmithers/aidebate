"""
LM Studio Model Detector

Queries LM Studio to detect which model is currently loaded and updates models.json.
"""
import json
import requests
from pathlib import Path


def detect_loaded_model(endpoint: str = "http://192.168.1.198:5555") -> dict:
    """
    Query LM Studio /v1/models endpoint to detect loaded model.

    Returns:
        dict with keys: success, model_id, model_name, error
    """
    try:
        response = requests.get(f"{endpoint}/v1/models", timeout=5)

        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])

            if models:
                # Get first model (LM Studio usually has only one loaded)
                model = models[0]
                model_id = model.get("id", "unknown")

                # Try to get a friendly name
                model_name = model_id

                # Map known model IDs to friendly names
                name_map = {
                    "zai-org/glm-4.7-flash": "GLM-4.7-Flash 30B",
                    "devstral-small-2-24b-instruct-2512": "Devstral Small 2 24B",
                    "qwen2.5-coder-32b-instruct": "Qwen 2.5 Coder 32B",
                    "qwen3-coder-30b": "Qwen 3 Coder 30B",
                }

                for key, name in name_map.items():
                    if key in model_id.lower():
                        model_name = name
                        break

                return {
                    "success": True,
                    "model_id": model_id,
                    "model_name": model_name,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "model_id": None,
                    "model_name": None,
                    "error": "No models loaded in LM Studio"
                }
        else:
            return {
                "success": False,
                "model_id": None,
                "model_name": None,
                "error": f"LM Studio returned status {response.status_code}"
            }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "model_id": None,
            "model_name": None,
            "error": "Cannot connect to LM Studio - is it running?"
        }
    except Exception as e:
        return {
            "success": False,
            "model_id": None,
            "model_name": None,
            "error": str(e)
        }


def update_models_json(config_path: Path, detected_model: dict):
    """
    Update models.json with detected LM Studio model.

    Args:
        config_path: Path to models.json
        detected_model: Result from detect_loaded_model()
    """
    if not detected_model["success"]:
        print(f"⚠️  LM Studio detection failed: {detected_model['error']}")
        return

    # Load existing config
    with open(config_path) as f:
        config = json.load(f)

    model_id = detected_model["model_id"]
    model_name = detected_model["model_name"]

    # Generate alias from model name (e.g., "GLM-4.7-Flash 30B" → "glm-flash")
    alias = model_id.split("/")[-1].split("-")[0].lower()

    # Check if this model is already in config
    existing = False
    for key, model_config in config["models"].items():
        if model_config.get("id") == model_id:
            existing = True
            print(f"✓ Model already in config: {model_name} (alias: {key})")
            break

    if not existing:
        # Add new model to config
        config["models"][alias] = {
            "id": model_id,
            "type": "lm_studio",
            "temperature": 0.3,
            "max_tokens": 2048,
            "name": model_name
        }

        # Save updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"✓ Added detected model to config: {model_name} (alias: {alias})")


def detect_and_update():
    """Detect LM Studio model and update models.json."""
    print("Detecting LM Studio model...")

    config_path = Path(__file__).parent.parent / "config" / "models.json"
    result = detect_loaded_model()

    if result["success"]:
        print(f"✓ Detected: {result['model_name']}")
        update_models_json(config_path, result)
    else:
        print(f"⚠️  Detection failed: {result['error']}")


if __name__ == "__main__":
    detect_and_update()
