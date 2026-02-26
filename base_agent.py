import os
from dotenv import load_dotenv

load_dotenv()

# print("[BASE AGENT] Hello, World!")

class BaseAgent:
    
    '''
    
    Supported Providers:
    - gemini (gemini-2.0-flash)
    - cerebras (llama3.1-8b, gpt-oss-120b) [RECOMMENDED]
    - nvidia [UNTESTED]
    - openrouter [UNTESTED]
    - ollama [UNTESTED]
    
    '''
    PROVIDER = 'cerebras'
    MODEL = 'llama3.1-8b'
    
    def __init__(self, id_, provider_=PROVIDER, model_=MODEL):
        self.id = id_
        self.model = model_
        self.provider = provider_
        
        print(f"[AGENT {self.id} ({self.provider}/{self.model})] Hello, World!")
        
    def __str__(self):
        return f"[AGENT {self.id} ({self.provider}/{self.model})]"
        
    def query(self, prompt, json_mode=False):
        dispatch = {
            'gemini':     self._query_gemini,
            'cerebras':   self._query_cerebras,
            'nvidia':     self._query_nvidia,
            'openrouter': self._query_openrouter,
            'ollama':     self._query_ollama,
        }
        fn = dispatch.get(self.provider)
        if fn is None:
            raise ValueError(f"Unsupported provider: '{self.provider}'")
        return fn(prompt, json_mode)

    # -------------------------------------------------------------------------

    def _query_gemini(self, prompt, json_mode):
        from google import genai
        from google.genai import types
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(
            response_mime_type="application/json" if json_mode else "text/plain"
        )
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        return response.text

    def _query_openai_compat(self, prompt, json_mode, base_url, api_key):
        from openai import OpenAI
        client = OpenAI(base_url=base_url, api_key=api_key)
        kwargs = dict(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def _query_cerebras(self, prompt, json_mode):
        return self._query_openai_compat(
            prompt, json_mode,
            base_url="https://api.cerebras.ai/v1",
            api_key=os.getenv("CEREBRAS_API_KEY"),
        )

    def _query_nvidia(self, prompt, json_mode):
        return self._query_openai_compat(
            prompt, json_mode,
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("NVIDIA_API_KEY"),
        )

    def _query_openrouter(self, prompt, json_mode):
        return self._query_openai_compat(
            prompt, json_mode,
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

    def _query_ollama(self, prompt, json_mode):
        return self._query_openai_compat(
            prompt, json_mode,
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        )