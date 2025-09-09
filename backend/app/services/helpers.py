import numpy as np
import warnings

def patched_array(obj, copy=None, **kwargs):
    if copy is False:
        warnings.warn("copy=False is deprecated in NumPy 2.0, using np.asarray instead")
        return np.asarray(obj, **kwargs)
    return original_array(obj, copy=copy, **kwargs)

np.array = patched_array

import fasttext

model = fasttext.load_model("lid.176.bin")


def detect_language(text: str) -> str | None:
    """
    Detect if text is English or Indonesian.
    Returns 'english', 'indonesian', or None.
    """
    print("Detecting language...", text)
    # Normalize text
    IGNORE = {"hi", "hello", "yes"}
    cleaned = text.strip().lower()

    # Check ignored words
    if cleaned in IGNORE:
        return None

    # Predict language
    labels, probs = model.predict(text, k=3)
    print(f"Detected labels: {labels} with probabilities {probs}")

    for label, prob in zip(labels, probs):
        if label == "__label__en":
            return "english"
        elif label in ("__label__id", "__label__min"):  # treat Minangkabau as Indonesian
            return "indonesian"

    return None