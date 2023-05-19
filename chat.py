import openai


class Chat:
    def __init__(self, api_key, model, temperature, max_tokens):
        self.api_key = api_key
        self.completion_params = {
            "model": model,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
        }

    def codeReview(self, prompt):
        if not prompt:
            return ""

        # print("Getting response from OpenAI")
        try:
            res = openai.Completion.create(
                engine=self.completion_params["model"],
                prompt=prompt,
                temperature=self.completion_params["temperature"],
                max_tokens=self.completion_params["max_tokens"],
                n=1,
                stop=None,
                api_key=self.api_key,
            )
        except Exception as e:
            print("Error occurred during OpenAI API call:", str(e))
            return ""

        # print("Returning response from OpenAI")
        if res.choices:
            return res.choices[0].text.strip()
        else:
            return ""
