# Generate minimal kedro project (without huge data - only the code and config):
import shutil
from pathlib import Path

# ------------------------
# Configuration
# ------------------------
project_root = Path("../../risk-profile-classifier")
output_archive = project_root / "kedro_risk_profile_classifier.zip"
folders_to_include = ["conf", "src"]
files_to_include = ["pyproject.toml"]

# ------------------------
# Create a temporary folder for minimal project
# ------------------------
temp_dir = project_root / "_minimal_kedro_temp"
temp_dir.mkdir(exist_ok=True)

# Copy folders
for folder_name in folders_to_include:
    src_folder = project_root / folder_name
    dst_folder = temp_dir / folder_name
    if src_folder.exists():
        shutil.copytree(src_folder, dst_folder, dirs_exist_ok=True)
        print(f"Copied folder: {folder_name}")
    else:
        print(f"Warning: folder not found: {folder_name}")

# Copy files
for file_name in files_to_include:
    src_file = project_root / file_name
    dst_file = temp_dir / file_name
    if src_file.exists():
        shutil.copy2(src_file, dst_file)
        print(f"Copied file: {file_name}")
    else:
        print(f"Warning: file not found: {file_name}")

# ------------------------
# Create zip archive
# ------------------------
shutil.make_archive(str(output_archive).replace(".zip", ""), 'zip', root_dir=project_root)
print(f"Minimal Kedro project archived at: {output_archive}")

# Optional: remove temporary folder
shutil.rmtree(temp_dir)
