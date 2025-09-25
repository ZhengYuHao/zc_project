import inspect
import logging
from typing import Any

import numpy as np
import json

from sklearn.metrics.pairwise import cosine_similarity

from sapperrag.ai_unit.llm.response_getter import GenericResponseGetter
# from ........app.core.config import settings
from ..structured_search.local_search.system_prompt import EXTRACT_ENTITIES_FROM_QUERY

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def extract_entities_from_query(query, llm, api_key, base_url, model, max_retries=3) -> Any:
    """
    从查询中抽取实体

    :param query: 用户输入的问题
    :param llm: 大语言模型
    :param max_retries: 最大重试次数
    :return: 抽取的实体列表
    """
    extract_prompt = EXTRACT_ENTITIES_FROM_QUERY.render(query=query)
    print("query:", query)
    for attempt in range(max_retries):
        try:
            extract_entities = await llm.get_response(query=extract_prompt, api_key=api_key, base_url=base_url, model=model)
            logger.debug(f"尝试 {attempt}: LLM 返回的响应 - {extract_entities}")
            extract_entities_list = json.loads(extract_entities)
            return extract_entities_list
        except json.JSONDecodeError as e:
            logger.error(f"尝试 {attempt}: 解析 JSON 响应失败 - {e}")
            if attempt < max_retries - 1:
                continue
    return [f"{query}"]


def _where() -> str:
    """返回调用处的文件行号，便于定位"""
    frame = inspect.currentframe().f_back
    return f"{frame.f_code.co_filename}:{frame.f_lineno}"


async def map_query_to_entities(extracted_entities, all_entities, api_key, base_url, k=300):
    embeder = GenericResponseGetter()
    if not extracted_entities:
        return []

    entities_list = []

    for idx_e, extracted_entity in enumerate(extracted_entities, 1):
        # ---------- 第 1 处：抽取实体向量 ----------
        extracted_entity_embed = await embeder.aget_vector(
            query=extracted_entity,
            api_key="fb1a7bd2-fca4-47e0-9ea4-ef8661f01b7e",
            base_url="https://ark.cn-beijing.volces.com/api/v3/"
        )

        if extracted_entity_embed is None or len(extracted_entity_embed) == 0:
            # print(f"[{_where()}] 空向量 => 跳过 extracted_entity='{extracted_entity}'")
            continue

        extracted_entity_embed = np.asarray(extracted_entity_embed, dtype=float)
        if np.isnan(extracted_entity_embed).any():
            # print(f"[{_where()}] NaN 向量 => 跳过 extracted_entity='{extracted_entity}' 值={extracted_entity_embed}")
            continue

        if extracted_entity_embed.ndim == 1:
            extracted_entity_embed = extracted_entity_embed.reshape(1, -1)

        # ---------- 第 2 处：逐个实体向量 ----------
        for idx_f, entity in enumerate(all_entities, 1):
            entity_embed = entity.attributes_embedding
            if entity_embed is None or len(entity_embed) == 0:
                # print(f"[{_where()}] 空向量 => 跳过 entity.id={entity.id}")
                continue

            entity_embed = np.asarray(entity_embed, dtype=float)
            if np.isnan(entity_embed).any():
                # print(f"[{_where()}] NaN 向量 => 跳过 entity.id={entity.id} 值={entity_embed}")
                continue

            if entity_embed.ndim == 1:
                entity_embed = entity_embed.reshape(1, -1)

            similarity = cosine_similarity(extracted_entity_embed, entity_embed)[0, 0]
            entities_list.append((entity, similarity))

    entities_list.sort(key=lambda x: x[1], reverse=True)
    top_k_entities = [e for e, _ in entities_list[:k]]
    unique_top_k_entities = list({e.id: e for e in top_k_entities}.values())

    return unique_top_k_entities



# async def map_query_to_entities(extracted_entities, all_entities, api_key, base_url, k=10):
#     """
#     将抽取出的实体列表与全量实体做向量相似度匹配，返回 Top-k 唯一实体。
#     已加入 NaN 检测与调试打印。
#     """
#     embeder = GenericResponseGetter()
#     if not extracted_entities:
#         return []
#
#     entities_list = []
#
#     for extracted_entity in extracted_entities:
#         # 1. 获取抽取实体的向量
#         extracted_entity_embed = await embeder.aget_vector(
#             query=extracted_entity,
#             api_key=api_key,
#             base_url=base_url
#         )
#
#         # 空向量或空列表直接跳过
#         if not extracted_entity_embed or len(extracted_entity_embed) == 0:
#             print(f"[跳过] 提取实体“{extracted_entity}”向量为空")
#             continue
#
#         extracted_entity_embed = np.array(extracted_entity_embed, dtype=float)
#
#         # NaN 检测
#         if np.isnan(extracted_entity_embed).any():
#             print(f"[跳过] 提取实体“{extracted_entity}”向量为 NaN: {extracted_entity_embed}")
#             continue
#
#         # 确保 2D
#         if extracted_entity_embed.ndim == 1:
#             extracted_entity_embed = extracted_entity_embed.reshape(1, -1)
#
#         # 2. 与全量实体逐一计算余弦相似度
#         for entity in all_entities:
#             entity_embed = entity.attributes_embedding
#
#             # 空向量跳过
#             if not entity_embed or len(entity_embed) == 0:
#                 continue
#
#             entity_embed = np.array(entity_embed, dtype=float)
#
#             # NaN 检测
#             if np.isnan(entity_embed).any():
#                 print(f"[跳过] 实体 ID={entity.id} 向量为 NaN: {entity_embed}")
#                 continue
#
#             # 确保 2D
#             if entity_embed.ndim == 1:
#                 entity_embed = entity_embed.reshape(1, -1)
#
#             # 计算相似度
#             similarity = cosine_similarity(extracted_entity_embed, entity_embed)[0, 0]
#             entities_list.append((entity, similarity))
#
#     # 3. 排序并去重
#     entities_list.sort(key=lambda x: x[1], reverse=True)
#     top_k_entities = [ent for ent, _ in entities_list[:k]]
#     unique_top_k_entities = list({ent.id: ent for ent in top_k_entities}.values())
#
#     return unique_top_k_entities
