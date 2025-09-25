import os
from abc import ABC, abstractmethod

from openai import AsyncOpenAI, OpenAI


# semaphore = asyncio.Semaphore(100)  # 控制最大并发任务数为 100


class ResponseGetter(ABC):
    @abstractmethod
    def get_response(self, **kwargs):
        pass

    @abstractmethod
    def get_vector(self, **kwargs):
        pass


class GenericResponseGetter(ResponseGetter):
    @staticmethod
    async def get_response(
            api_key: str,
            base_url: str,
            query: str,
            model: str,
            **kwargs
    ) -> str:
        """
        聊天式API接口
        :param api_key: API密钥
        :param base_url: API地址
        :param query: 查询内容
        :param model: 模型名称
        :return: 返回结果
        """
        # 初始化异步客户端
        async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        # async with semaphore:
        completion = await async_client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "你是知识图谱领域专家。"
                },
                {
                    "role": "user",
                    "content": query
                },
            ],
            temperature=0
        )
        return completion.choices[0].message.content

    @staticmethod
    async def aget_vector(
            query: str,
            model: str = "doubao-embedding-large-text-250515",
            api_key: str = "",
            base_url: str = "",
    ) -> list[float]:
        """
        向量嵌入API接口
        :param query: 查询内容
        :param model: 模型名称
        :param api_key: API密钥
        :param base_url: API地址
        """
        api_key = os.getenv("api_key")
        base_url = os.getenv("base_url")
        model = os.getenv("embedding_model")
        # 初始化异步Embedding客户端
        async_embedding_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        # async with semaphore:
        completion = await async_embedding_client.embeddings.create(
            model=model,
            input=[query]
        )
        return completion.data[0].embedding

    @staticmethod
    def get_vector(
            query: str,
            model: str = "doubao-embedding-large-text-250515",
            api_key: str = "",
            base_url: str = "",
    ) -> list[float]:
        """
        向量嵌入API接口
        :param query: 查询内容
        :param model: 模型名称
        :param api_key: API密钥
        :param base_url: API地址
        """
        api_key = os.getenv("api_key")
        # 初始化异步Embedding客户端
        embedding_client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        # async with semaphore:
        completion = embedding_client.embeddings.create(
            model=model,
            input=[query]
        )
        return completion.data[0].embedding


class ResponseGetterFactory:
    @staticmethod
    def create() -> GenericResponseGetter:
        # 替换使用模型
        return GenericResponseGetter()
