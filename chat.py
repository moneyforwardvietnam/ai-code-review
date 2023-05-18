import os
import openai


class Chat:
    def __init__(self, api_key):
        self.api_key = api_key
        self.completion_params = {
            "model": os.environ.get("MODEL", "text-davinci-003"),
            "temperature": float(os.environ.get("temperature", 0)) or 1,
            "top_p": float(os.environ.get("top_p", 0)) or 1,
        }

    def generatePrompt(self, patch):
        answerLanguage = (
            f"Answer me in {os.environ['LANGUAGE']}, "
            if "LANGUAGE" in os.environ
            else ""
        )
        return f"Bellow is the code patch, please help me do a brief code review, {answerLanguage} if any bug risk and improvement suggestion are welcome\n{patch}\n"

    def codeReview(self, patch):
        if not patch:
            return ""

        print("code-review cost")
        prompt = self.generatePrompt(patch)

        res = openai.Completion.create(
            engine=self.completion_params["model"],
            prompt=prompt,
            temperature=self.completion_params["temperature"],
            max_tokens=200,
            top_p=self.completion_params["top_p"],
            n=1,
            stop=None,
            api_key=self.api_key,
        )

        print("code-review cost")
        return res.choices[0].text.strip()
