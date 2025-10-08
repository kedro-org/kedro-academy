from pathlib import Path

from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project

current_dir = Path(__file__).resolve().parent
bootstrap_project(current_dir)

client_ids = ["client_1", "client_2", "client_3"]

for client_id in client_ids:
    print(f"Running Kedro pipeline for {client_id}")
    print("-" * 40)
    with KedroSession.create(
        project_path=current_dir, runtime_params={"client_name": client_id}
    ) as session:
        session.run()
