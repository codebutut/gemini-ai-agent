import os
import shutil
import json
import zipfile
from pathlib import Path
from core.checkpoint_manager import CheckpointManager

def test_checkpoint_manager():
    test_dir = Path("test_project").resolve()
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir()
    
    # Create some dummy files
    (test_dir / "file1.txt").write_text("Hello World")
    (test_dir / "subdir").mkdir()
    (test_dir / "subdir" / "file2.txt").write_text("Subdir file")
    (test_dir / "env").mkdir()
    (test_dir / "env" / "secret.txt").write_text("Should be excluded")
    
    manager = CheckpointManager(root_dir=str(test_dir))
    
    print("Creating checkpoint...")
    cp = manager.create_checkpoint("Initial State")
    assert cp is not None
    
    checkpoint_path = test_dir / ".checkpoints" / cp['filename']
    assert checkpoint_path.exists()
    
    print(f"Zip contents: {zipfile.ZipFile(checkpoint_path).namelist()}")
    
    print("Listing checkpoints...")
    checkpoints = manager.list_checkpoints()
    assert len(checkpoints) == 1
    assert checkpoints[0]['name'] == "Initial State"
    
    print("Modifying project...")
    (test_dir / "file1.txt").write_text("Modified World")
    (test_dir / "new_file.txt").write_text("New file")
    
    print("Restoring checkpoint...")
    success = manager.restore_checkpoint(cp['id'])
    assert success
    
    print(f"File1 content after restore: '{(test_dir / 'file1.txt').read_text()}'")
    
    print("Verifying restoration...")
    assert (test_dir / "file1.txt").read_text() == "Hello World"
    assert not (test_dir / "new_file.txt").exists()
    assert (test_dir / "subdir" / "file2.txt").exists()
    
    print("Deleting checkpoint...")
    success = manager.delete_checkpoint(cp['id'])
    assert success
    assert not checkpoint_path.exists()
    
    print("Test passed!")
    
    # Cleanup
    shutil.rmtree(test_dir)

if __name__ == "__main__":
    test_checkpoint_manager()
