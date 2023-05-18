# Automated Code Review using the ChatGPT language model

## Import statements
import argparse
import openai
import os
import requests
import re
from github import Github
from chat import Chat
import json

## Adding command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--openai_api_key", help="Your OpenAI API Key")
parser.add_argument("--github_token", help="Your Github Token")
parser.add_argument("--github_pr_id", help="Your Github PR ID")
parser.add_argument(
    "--openai_engine",
    default="text-davinci-002",
    help="GPT-3 model to use. Options: text-davinci-003, text-davinci-002, text-babbage-001, text-curie-001, text-ada-001",
)
parser.add_argument(
    "--openai_temperature",
    default=0.5,
    help="Sampling temperature to use. Higher values means the model will take more risks. Recommended: 0.5",
)
parser.add_argument(
    "--openai_max_tokens",
    default=2048,
    help="The maximum number of tokens to generate in the completion.",
)
parser.add_argument(
    "--mode", default="files", help="PR interpretation form. Options: files, patch"
)
parser.add_argument(
    "--lang",
    default="terraform",
    help="The programming language that you need to review.",
)
args = parser.parse_args()

## Authenticating with the OpenAI API
openai.api_key = args.openai_api_key

## Authenticating with the Github API
g = Github(args.github_token)


def robot():
    event_payload = os.environ["GITHUB_EVENT_PATH"]
    with open(event_payload) as file:
        payload = json.load(file)

    action = payload["action"]
    if action not in ["opened", "synchronize"]:
        return "invalid event payload"

    chat = Chat(args.openai_api_key)
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

    repo = g.get_repo(os.getenv("GITHUB_REPOSITORY"))
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
        print(pull_request["number"])
        pull_requestObj = repo.get_pull(int(pull_request["number"]))
        if res:
            pull_requestObj.create_issue_comment(f"`{file.filename}`:\n {res}")

    print("gpt cost")
    print(f"successfully reviewed {pull_request['html_url']}")
    return "success"


def files():
    repo = g.get_repo(os.getenv("GITHUB_REPOSITORY"))
    pull_request = repo.get_pull(int(args.github_pr_id))

    # Set to store processed file names
    processed_files = set()

    # Loop through the commits in the pull request
    commits = pull_request.get_commits()
    for commit in commits:
        # Getting the modified files in the commit
        files = commit.files
        lang = args.lang
        for file in files:
            # Getting the file name and content
            file_name = file.filename
            if file_name in processed_files:
                # Skip processing duplicate file names
                continue
            else:
                if re.search(r"\.(md|DS_Store|png|gitignore)$", file_name):
                    continue
                else:
                    try:
                        content = repo.get_contents(
                            file_name, ref=commit.sha
                        ).decoded_content

                        # Sending the code to ChatGPT
                        response = openai.Completion.create(
                            engine=args.openai_engine,
                            prompt=(
                                f"Review the following {lang} code snippet, give me maximum 10 unique important suggestions to improve and optimize this code without give corrected code snippets:\n```{content}```"
                                f"Bellow is the code patch, please help me do a brief code review, {answerLanguage} if any bug risk and improvement suggestion are welcome\n{patch}\n"
                            ),
                            temperature=float(args.openai_temperature),
                            max_tokens=int(args.openai_max_tokens),
                        )

                        # Adding a comment to the pull request with ChatGPT's response
                        pull_request.create_issue_comment(
                            f"I have compiled a few suggestions for this file `{file.filename}`:\n {response['choices'][0]['text']}"
                        )

                        # Add the processed file name to the set
                        processed_files.add(file_name)
                    except Exception as e:
                        error_message = str(e)
                        print(error_message)
                        # Post a comment instead of throwing an exception
                        pull_request.create_issue_comment(
                            f"This file `{file_name}` has exceeded the maximum token limit that ChatGPT can process, so no suggestions can be provided."
                        )


def patch():
    repo = g.get_repo(os.getenv("GITHUB_REPOSITORY"))
    pull_request = repo.get_pull(int(args.github_pr_id))
    content = get_content_patch()

    # Set to store processed file names
    processed_files = set()

    if len(content) == 0:
        pull_request.create_issue_comment(f"Patch file does not contain any changes")
        return

    parsed_text = content.split("diff")

    for diff_text in parsed_text:
        if len(diff_text) == 0:
            continue

        try:
            file_name = diff_text.split("b/")[1].splitlines()[0]

            if re.search(r"\.(md|DS_Store|png|gitignore)$", file_name):
                continue
            elif file_name in processed_files:
                # Skip processing duplicate file names
                continue
            else:
                response = openai.Completion.create(
                    engine=args.openai_engine,
                    prompt=(
                        f"Summarize what was done in this diff:\n```{diff_text}```"
                    ),
                    temperature=float(args.openai_temperature),
                    max_tokens=int(args.openai_max_tokens),
                )
                # print(response)
                print(response["choices"][0]["text"])

                # Retrieve the current description
                current_description = pull_request.body
                if current_description is None:
                    current_description = ""
                else:
                    current_description = current_description + "\n\n"
                # Concatenate the new description with the current one
                combined_description = (
                    current_description
                    + f"Changes for file: ``{file_name}``:\n {response['choices'][0]['text']}"
                )
                pull_request.edit(body=combined_description)

                # Add the processed file name to the set
                processed_files.add(file_name)
        except Exception as e:
            error_message = str(e)
            print(error_message)
            # Post a comment instead of throwing an exception
            pull_request.create_issue_comment(
                f"This file `{file_name}` have over maximum tokens that ChatGPT can process so cannot give any suggestions"
            )


def get_content_patch():
    url = f"https://api.github.com/repos/{os.getenv('GITHUB_REPOSITORY')}/pulls/{args.github_pr_id}"
    print(url)

    headers = {
        "Authorization": f"token {args.github_token}",
        "Accept": "application/vnd.github.v3.diff",
    }

    response = requests.request("GET", url, headers=headers)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.text


if args.mode == "files" or args.mode == "files,patch":
    robot()

if args.mode == "patch" or args.mode == "files,patch":
    patch()
