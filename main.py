import argparse
import os
import re
from github import Github
from chat import Chat


def main():
    try:
        # Adding command-line arguments
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
            help="Sampling temperature to use. Higher values mean the model will take more risks. Recommended: 0.5",
        )
        parser.add_argument(
            "--openai_max_tokens",
            default=2048,
            help="The maximum number of tokens to generate in the completion.",
        )
        parser.add_argument(
            "--auto_pr_descriptions",
            default="true",
            help="Enable or disable auto-fill pull request descriptions. Options: true, false",
        )
        parser.add_argument(
            "--auto_code_review",
            default="true",
            help="Enable or disable auto code review for pull requests. Options: true, false",
        )
        args = parser.parse_args()

        # Authenticating with the OpenAI API
        chat = Chat(
            api_key=args.openai_api_key,
            model=args.openai_engine,
            temperature=args.openai_temperature,
            max_tokens=args.openai_max_tokens,
        )

        # Authenticating with the Github API
        g = Github(args.github_token)

        repo = g.get_repo(os.getenv("GITHUB_REPOSITORY"))
        pull_request = repo.get_pull(int(args.github_pr_id))

        # Set to store processed file names
        processed_files = set()

        # Retrieve the current description
        current_description = pull_request.body or ""
        current_description += "\n\n"

        # Loop through the files in the pull request
        for file in pull_request.get_files():
            # Getting the file name and diff content
            file_name = file.filename

            if file_name in processed_files:
                # Skip processing duplicate file names
                continue

            diff_content = file.patch or ""
            if not diff_content or len(diff_content) >= 4000:
                # Skip files without diff content or exceeding the openai tokens limit
                continue

            # Format the diff_content with triple backticks to create a code block
            quoted_diff_content = f"```diff\n{diff_content}\n```"

            if args.auto_code_review == "true":
                # Sending the diff content to ChatGPT for code review
                response = chat.codeReview(
                    f"Below is the code patch. Please help me do a brief review do not include any quote of this code patch. Any bug risks and improvement suggestions are welcome:\n{diff_content}"
                )

                # Adding a comment to the pull request with ChatGPT's response and quoted diff
                pull_request.create_issue_comment(
                    f"\n{response}\n\nDiff of file `{file_name}`:\n{quoted_diff_content}"
                )

            if args.auto_pr_descriptions == "true":
                # Sending the diff content to ChatGPT to summarize the changes
                response = chat.codeReview(
                    f"Summarize what was done in this diff:\n```{diff_content}```"
                )

                # Concatenate the new description with the current one
                current_description += (
                    f"Changes for file: ``{file_name}``:\n{response}\n\n"
                )

            # Add the processed file name to the set
            processed_files.add(file_name)

        # Update the pull request description
        pull_request.edit(body=current_description)

    except Exception as e:
        print("An error occurred:", str(e))


if __name__ == "__main__":
    main()
