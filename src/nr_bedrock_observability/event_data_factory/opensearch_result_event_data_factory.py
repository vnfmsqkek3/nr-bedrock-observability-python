import json
import logging
import uuid
import time
from typing import Dict, Any, Optional, Union, List

from ..event_types import (
    EventType, EventData, EventAttributes, 
    OpenSearchResultAttributes
)

logger = logging.getLogger(__name__)

class OpenSearchResultEventDataFactoryOptions:
    """
    OpenSearch 결과 이벤트 데이터 팩토리 옵션
    """
    def __init__(
        self,
        query: str,
        results: List[Dict[str, Any]],
        index_name: Optional[str] = None,
        response_time: int = 0,
        trace_id: Optional[str] = None,
        total_results: Optional[int] = None
    ):
        self.query = query
        self.results = results
        self.index_name = index_name
        self.response_time = response_time
        self.trace_id = trace_id
        self.total_results = total_results or len(results)


class OpenSearchResultEventDataFactory:
    """
    OpenSearch 검색 결과에 대한 이벤트 데이터 생성
    """
    def __init__(self, application_name: str):
        self.application_name = application_name
        
    def create_event_data_list(
        self, 
        options: Union[OpenSearchResultEventDataFactoryOptions, Dict[str, Any]]
    ) -> List[EventData]:
        """
        OpenSearch 검색 결과에 대한 이벤트 데이터 리스트 생성
        """
        if isinstance(options, dict):
            factory_options = OpenSearchResultEventDataFactoryOptions(
                query=options['query'],
                results=options['results'],
                index_name=options.get('index_name'),
                response_time=options.get('response_time', 0),
                trace_id=options.get('trace_id'),
                total_results=options.get('total_results')
            )
        else:
            factory_options = options
        
        # 트레이스 ID가 없으면 생성
        trace_id = factory_options.trace_id or str(uuid.uuid4())
        
        # 결과 가져오기
        results = factory_options.results
        query = factory_options.query
        index_name = factory_options.index_name
        response_time = factory_options.response_time
        total_results = factory_options.total_results
        
        # 결과가 없으면 빈 리스트 반환
        if not results:
            return []
        
        # 이벤트 데이터 리스트 생성
        event_data_list = []
        
        # 각 결과에 대한 이벤트 생성
        for i, result in enumerate(results):
            result_content = result.get('content', '')
            result_title = result.get('title', '')
            score = result.get('score', 0.0)
            
            # 결과 속성 생성
            result_attrs = OpenSearchResultAttributes(
                id=str(uuid.uuid4()),
                applicationName=self.application_name,
                query=query,
                index_name=index_name,
                result_content=result_content[:4095],  # 텍스트 길이 제한
                result_title=result_title[:255] if result_title else None,
                score=score,
                sequence=i,
                trace_id=trace_id,
                timestamp=int(time.time() * 1000),
                total_results=total_results,
                response_time=response_time
            )
            
            # 이벤트 데이터 생성
            event_data_list.append(
                EventData(
                    event_type=EventType.LLM_OPENSEARCH_RESULT,
                    attributes=result_attrs
                )
            )
        
        return event_data_list 