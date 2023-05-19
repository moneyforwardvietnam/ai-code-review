import os
from github import Github
from chat import Chat


def loadChat():
    if "OPENAI_API_KEY" in os.environ:
        return Chat(os.environ["OPENAI_API_KEY"])

    try:
        github_token = os.environ["GITHUB_TOKEN"]
        g = Github(github_token)
        repo = g.get_repo(os.environ["GITHUB_REPOSITORY"])
        variable = (
            repo.get_workflow_run(os.environ["GITHUB_RUN_ID"])
            .get_workflow()
            .get_variable("OPENAI_API_KEY")
        )
        if variable and variable.value:
            return Chat(variable.value)
    except Exception as e:
        print(f"Error retrieving OPENAI_API_KEY: {str(e)}")

    return None


def robot():
    event_payload = os.environ["GITHUB_EVENT_PATH"]
    with open(event_payload) as file:
        payload = json.load(file)

    action = payload["action"]
    if action not in ["opened", "synchronize"]:
        return "invalid event payload"

    chat = loadChat()
    if not chat:
        return "no chat"

    pull_request = payload["pull_request"]
    if (
        pull_request["state"] == "closed"
        or pull_request["locked"]
        or pull_request["draft"]
    ):
        return "invalid event payload"

    target_label = os.environ.get("TARGET_LABEL")
    if target_label and (
        not pull_request["labels"]
        or all(label["name"] != target_label for label in pull_request["labels"])
    ):
        return "no target label attached"

    github_token = os.environ["GITHUB_TOKEN"]
    g = Github(github_token)
    repo = g.get_repo(os.environ["GITHUB_REPOSITORY"])

    base_sha = pull_request["base"]["sha"]
    head_sha = pull_request["head"]["sha"]
    data = repo.compare(base_sha, head_sha)

    changed_files = data.files
    commits = data.commits

    if action == "synchronize" and len(commits) >= 2:
        prev_commit_sha = commits[-2].sha
        current_commit_sha = commits[-1].sha
        compare_data = repo.compare(prev_commit_sha, current_commit_sha)
        files_names = (
            [file.filename for file in compare_data.files] if compare_data.files else []
        )
        changed_files = [file for file in changed_files if file.filename in files_names]

    if not changed_files:
        return "no change"

    print("gpt cost")

    for file in changed_files:
        if file.status != "modified" and file.status != "added":
            continue

        patch = file.patch or ""
        if not patch or len(patch) > 4000:
            continue

        res = chat.codeReview(patch)

        if res:
            repo.create_pull_comment(
                pull_request["number"],
                res,
                file.filename,
                None,
                file.filename,
                patch.count("\n"),
            )

    print("gpt cost")
    print(f"successfully reviewed {pull_request['html_url']}")
    return "success"


if __name__ == "__main__":
    robot()
