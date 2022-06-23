import os
import pickle

from dotenv import load_dotenv
from github_crawler import DeveloperBase

file_path = "developers.pkl"

projects = ["thuyngch/Iris-Recognition", "vturrisi/solo-learn"]

if __name__ == "__main__":
    load_dotenv()
    gh_token = os.getenv("GH_TOKEN")

    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            developer_base = pickle.load(f)
    else:
        developer_base = DeveloperBase(file_path=file_path)

    developer_base.find_developers(gh_token, projects)
