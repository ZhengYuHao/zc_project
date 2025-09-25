import logging
import numpy as np
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm   # ✅ 新增

from sapperrag.ai_unit.llm.response_getter import GenericResponseGetter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class AttributeEmbedder:
    def __init__(self, max_concurrent=200):
        self.max_concurrent = max_concurrent
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)

    @staticmethod
    def embed_attributes(text_embeder, attributes, api_key, base_url):
        """
        带指数退避重试的嵌入方法 (线程版本)
        """
        max_retries = 3
        backoff_factor = 1

        attributes_text = " ".join(f"{k}: {v}" for k, v in attributes.items())
        for attempt in range(max_retries):
            try:
                response = text_embeder.get_vector(
                    query=attributes_text,
                    api_key=api_key,
                    base_url=base_url
                )
                logger.info(f"嵌入成功: {attributes_text}")
                return np.array(response)
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"嵌入失败: {str(e)}")
                    raise
                time.sleep(backoff_factor * (2 ** attempt))
        return np.array([])

    def _process_single_entity(self, index, entity, embeder, api_key, base_url):
        """
        处理单个实体的任务 (线程版本)
        """
        try:
            attributes = entity.attributes.copy()
            attributes["name"] = entity.name

            vector = AttributeEmbedder.embed_attributes(embeder, attributes, api_key, base_url)

            entity.attributes_embedding = vector.tolist()
            return index, None
        except Exception as e:
            return index, e

    def add_attribute_vectors(self, entities, api_key, base_url):
        """
        多线程并发处理所有实体，带进度条
        """
        embeder = GenericResponseGetter()
        futures = {
            self.executor.submit(self._process_single_entity, idx, entity, embeder, api_key, base_url): (idx, entity)
            for idx, entity in enumerate(entities)
        }

        with tqdm(total=len(futures), desc="嵌入进度", unit="entity") as pbar:
            for future in as_completed(futures):
                idx, entity = futures[future]
                try:
                    _, error = future.result()
                    if error:
                        logger.error(f"处理实体 {idx} 时出错: {str(error)}")
                except Exception as e:
                    logger.error(f"处理实体 {idx} 时异常: {str(e)}")
                finally:
                    pbar.update(1)

        return entities
