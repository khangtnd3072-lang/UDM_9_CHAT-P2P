from pathlib import Path

from storage.storage_manager import (
    StorageManager
)


def test_load_missing_file():

    result = StorageManager.load_json(
        Path("missing.json"),
        {}
    )

    assert result == {}
    
def test_save_and_load_json():

    path = Path(
        "data/storage/test.json"
    )

    expected = {
        "name": "Tai"
    }

    StorageManager.save_json(
        path,
        expected
    )

    actual = StorageManager.load_json(
        path,
        {}
    )

    assert actual == expected
    
