#!/bin/sh -l
python /main.py --openai_api_key "$1" --github_token "$2" --github_pr_id "$3" --openai_engine "$4" --openai_temperature "$5" --openai_max_tokens "$6" --auto_pr_descriptions "$7" --auto_code_review "$8"
