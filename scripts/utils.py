from supabase import create_client, Client
from openai import OpenAI
import anthropic as ant


class ChatHistory:
    def __init__(self, api_key, db_url):
        url: str = db_url
        key: str = api_key
        self.supabase: Client = create_client(url, key)
    def add_message(self, message, user_id, session_id, role):
        self.supabase.table("ChatHistory").insert({"session_id": session_id, "role": role, "user_id": user_id, "message": message}).execute()
    def retrieve_history(self, session_id, user_id, limit=None):
        if limit is None:
            res = self.supabase.table("ChatHistory").select("*").eq("session_id", session_id).eq("user_id", user_id).order("timestamp", desc=False).execute()
            data = res.data
            message_history = [{"role": d["role"], "content": d["message"]} for d in data]
            return message_history
        else:
            if type(limit) == int:
                res = self.supabase.table("ChatHistory").select("*").eq("session_id", session_id).eq("user_id", user_id).order("timestamp", desc=True).limit(limit).execute()
                data = res.data
                data.reverse()
                message_history = [{"role": d["role"], "content": d["message"]} for d in data]
                return message_history
            else:
                raise TypeError("Variable `limit` must be an integer")

class Summarizer:
    def __init__(self, api_key):
        self.openai_client = OpenAI(api_key=api_key)
    def invoke(self, message, system_prompt="You are an helpful assistant whose job is to summarize the text you are given in less than 900 charachters (including spaces) in such a way that it would constitute a good prompt for image generation."):
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ]
        )
        res = response.choices[0].message.content
        return res

class ImageGen:
    def __init__(self, api_key, num_igs):
        self.openai_client = OpenAI(api_key=api_key)
        self.summ = Summarizer(api_key=api_key)
        self.num_imgs = num_igs
    def generate_img(self, prompt):
        real_prompt = self.summ.invoke(prompt)
        response = self.openai_client.images.generate(
            model="dall-e-2",
            prompt="Generate theme images for this pitch presentation, based on its content hereby provided:\n\n"+real_prompt,
            size="1024x1024",
            quality="standard",
            n=self.num_imgs,
            )
        images = response.data
        urls = [img.url for img in images]
        return urls

class ChatAnthropic:
    def __init__(self, ant_api_key, sup_api_key, sup_api_url, user_id, session_id, summarizer: Summarizer):
        self.ant_client = ant.Anthropic(api_key=ant_api_key)
        self.chat_history = ChatHistory(sup_api_key, sup_api_url)
        self.user_id = user_id
        self.session_id = session_id
        self.system_prompt = """You are a talented pitcher whose role is to produce the best pitch presentation based on the argument and on the context provided by the users with their prompts. Do not assume extra information: if in doubt, ask for more context. Always refuse to produce harmful, offensive or unethical content. You must always structure your output in YAML-like format, as follows:
             - slide-1:
                 - Point 1: 
                 - Point 2: 
             etc.
        """
        self.summarizer = summarizer
    def invoke(self, message, limit_history=None):
        self.chat_history.add_message(message, self.user_id, self.session_id, "user")
        mexes = self.chat_history.retrieve_history(self.session_id, self.user_id, limit=limit_history)
        resp = self.ant_client.messages.create(
            model = "claude-3-5-sonnet-20240620",
            system=self.system_prompt,
            max_tokens = 900,
            messages = mexes,
        )
        summ = self.summarizer.invoke(str(resp.content[0].text), "You are an helpful assistant pitcher whose job is to summarize the text you are given in less than 1000 charachters (including spaces) in order to convey the best ideas in the most impressive 'pitch speech'.")
        self.chat_history.add_message(summ, self.user_id, self.session_id, "assistant")
        return summ

class SessionHistory:
    def __init__(self, api_key, db_url):
        url: str = db_url
        key: str = api_key
        self.supabase: Client = create_client(url, key)
    def generate_session_id(self):
        res = self.supabase.table("ChatHistory").select("*").order("session_id", desc=True).limit(1).execute()
        data = res.data
        if len(data) > 0:
            session_id = data[0]["session_id"]+1
        else:
            session_id = 0
        return session_id

def read_config(config_file=".config"):
    f = open(config_file, "r")
    lines = f.readlines()
    configdict = {}
    for l in lines:
        if l!="\n":
            exp = l.replace("\n", "")
            splitexp = exp.split("=")
            k = splitexp[0]
            v = eval(splitexp[1])
            configdict.update({k: v})
        else:
            continue
    return configdict


def chat_completion(chatter: ChatAnthropic, imagegen: ImageGen, prompt: str, limit_history=None):
    starting_prompt = chatter.invoke(prompt, limit_history)
    urls = imagegen.generate_img(starting_prompt)
    return starting_prompt, urls
