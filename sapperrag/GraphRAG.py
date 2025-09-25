#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import asyncio
import re

from dotenv import load_dotenv

from sapperrag.service.knowledge_graph_service import knowledge_graph_service
from sapperrag.schema import GetIndexDetail
from sapperrag.utils.serializers import select_as_dict
import os

async def ask_knowledge_graph(query: str):
    # combined_knowledge_graph = GetIndexDetail(
    #     entities=[],
    #     relationships=[],
    #     communities=[],
    #     **{}
    # )
    #
    # for uid in uuid:
    load_dotenv(override=True)
    uuid = os.getenv("graph_uuid")
    api_key = os.getenv("api_key")
    base_url = os.getenv("base_url")
    model = os.getenv("model")
    knowledge_graph = await knowledge_graph_service.get_knowledge_graph(uuid=uuid)
    data = GetIndexDetail(**select_as_dict(knowledge_graph))

        # combined_knowledge_graph.entities.extend(data.entities)
        # combined_knowledge_graph.relationships.extend(data.relationships)
        # combined_knowledge_graph.communities.extend(data.communities)

    # 执行查询
    response = await knowledge_graph_service.query(
        knowledge_graph=data,
        query=query,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
    results = response.get("results")
    context_text = response.get("context_text")

    # 去除答案中的无效字符串
    pattern = r'\[Data: Sources \(\d+\)\]'
    results = re.sub(pattern, '', results)

    # 去除source中的无效字符串
    lines = context_text.split('\n')
    remaining_lines = lines[2:]
    context_text = '\n'.join(remaining_lines)
    return results, context_text


async def main():
    from dotenv import load_dotenv
    import os
    load_dotenv(override=True)
    uuid = os.getenv("graph_uuid")
    api_key = os.getenv("api_key")
    base_url = os.getenv("base_url")
    model = os.getenv("model")
    qurry_list = ["可以发一下相关内容吗？", "是探店吗？"]
    for qurry in qurry_list:
        answer, source = await ask_knowledge_graph(
            uuid=uuid,
            query=qurry,
            api_key=api_key,
            base_url=base_url,
            model=model
        )
        print("Answer:", answer)
        print("Source", source)
        # print("Source:", source)


if __name__ == "__main__":
    asyncio.run(main())
