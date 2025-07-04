import json
import logging
import uuid
from typing import Dict, Any, Optional, Union
import time

from ..event_types import EventType, EventData, CompletionAttributes, BedrockModelMapping

logger = logging.getLogger(__name__)

class BedrockCompletionEventDataFactoryOptions:
    """
    Bedrock 완성 이벤트 데이터 팩토리 옵션
    """
    def __init__(
        self,
        application_name: str,
        bedrock_configuration: Optional[Dict[str, Any]] = None
    ):
        self.application_name = application_name
        self.bedrock_configuration = bedrock_configuration

class BedrockCompletionEventDataFactory:
    """
    invoke_model API 호출에 대한 이벤트 데이터 생성
    """
    def __init__(self, options: Union[BedrockCompletionEventDataFactoryOptions, Dict[str, Any]]):
        if isinstance(options, dict):
            self.application_name = options['application_name']
            self.bedrock_configuration = options.get('bedrock_configuration')
        else:
            self.application_name = options.application_name
            self.bedrock_configuration = options.bedrock_configuration
        
    def create_event_data(self, options: Dict[str, Any]) -> Optional[EventData]:
        """
        Bedrock invoke_model 호출에 대한 이벤트 데이터 생성
        
        :param options: 이벤트 데이터 생성 옵션
        :return: 이벤트 데이터 또는 None
        """
        # 요청 및 응답 데이터 추출
        request = options.get('request', {})
        response_data = options.get('response_data', {})
        response_time = options.get('response_time', 0)
        response_error = options.get('response_error')
        
        # 모델 ID 추출
        model_id = self._extract_model_id(request)
        if not model_id:
            logger.warning("Model ID not found in request")
            return None
            
        # 응답 및 요청 본문 처리
        parsed_request_body = self._extract_request_body(request)
        parsed_response_body = self._extract_response_body(response_data)
        
        # 스트리밍 호출 확인
        is_streaming = request.get('is_streaming', False)
        stream_event_type = request.get('stream_event_type', None)
        
        # RAG API 호출 확인
        is_rag = request.get('api_type') == 'rag'
        
        # 완성 텍스트 추출
        input_text = self._extract_prompt(parsed_request_body, model_id)
        output_text = self._extract_completion_text(parsed_response_body, model_id, is_rag)
        
        # completion_id 결정 - context_data에서 제공된 ID가 있으면 사용, 없으면 새로 생성
        completion_id = str(uuid.uuid4())
        # options에서 context_data 확인
        if 'context_data' in options and options['context_data'] and 'completion_id' in options['context_data']:
            completion_id = options['context_data']['completion_id']
        
        # 완성 속성 생성
        attributes: CompletionAttributes = {
            "id": completion_id,
            "applicationName": self.application_name,
            "request_model": model_id,
            "response_model": BedrockModelMapping.normalize_model_id(model_id),
            "response_time": response_time,
            "timestamp": int(time.time() * 1000),
            "vendor": "bedrock",
            "input": input_text[:4095] if input_text else "",  # 길이 제한
            "output": output_text[:4095] if output_text else "",  # 길이 제한
            "ingest_source": "python-bedrock-sdk"
        }
        
        # 스트리밍 관련 속성 추가
        if is_streaming:
            attributes["is_streaming"] = True
            if stream_event_type:
                attributes["stream_event_type"] = stream_event_type
                
        # RAG 관련 속성 추가
        if is_rag:
            attributes["api_type"] = "rag"
            
            # 인용 정보 추가
            citations = response_data.get('citations', [])
            if citations and isinstance(citations, list) and len(citations) > 0:
                attributes["citation_count"] = len(citations)
                
        # AWS 리전 정보 추가
        if self.bedrock_configuration and 'region_name' in self.bedrock_configuration:
            attributes["region"] = self.bedrock_configuration['region_name']
            
        # 토큰 사용량 정보 추가
        self._add_token_usage(attributes, parsed_response_body, model_id)
        
        # 오류 정보 추가
        if response_error:
            self._add_error_info(attributes, response_error)
            
        # 완료 이유 추가
        finish_reason = self._extract_finish_reason(parsed_response_body, model_id)
        if finish_reason:
            attributes["finish_reason"] = finish_reason
            
        return {
            "eventType": EventType.LLM_COMPLETION,
            "attributes": attributes
        }
        
    def _extract_model_id(self, request: Dict[str, Any]) -> str:
        """
        요청에서 모델 ID 추출
        """
        # modelId 직접 추출
        if 'modelId' in request:
            return request['modelId']
            
        # 파싱된 요청 본문에서 추출
        if 'parsed_body' in request and isinstance(request['parsed_body'], dict):
            if 'modelId' in request['parsed_body']:
                return request['parsed_body']['modelId']
                
        return ""
        
    def _extract_request_body(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        요청에서 본문 데이터 추출
        """
        # 이미 파싱된 본문이 있는 경우
        if 'parsed_body' in request and isinstance(request['parsed_body'], dict):
            return request['parsed_body']
            
        # 본문을 직접 파싱
        if 'body' in request:
            body = request['body']
            if isinstance(body, dict):
                return body
                
            try:
                if hasattr(body, 'read'):
                    # StreamingBody 객체인 경우
                    content = body.read()
                    if isinstance(content, bytes):
                        return json.loads(content.decode('utf-8'))
                    else:
                        return json.loads(content)
                elif isinstance(body, str):
                    return json.loads(body)
                elif isinstance(body, bytes):
                    return json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                logger.warning("Failed to parse request body as JSON")
                
        return {}
        
    def _extract_response_body(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        응답에서 본문 데이터 추출
        """
        # 이미 파싱된 본문이 있는 경우
        if 'parsed_body' in response_data and isinstance(response_data['parsed_body'], dict):
            return response_data['parsed_body']
            
        # 직접 generation 필드가 있는 경우 (RAG API)
        if 'generation' in response_data:
            return {'generation': response_data['generation']}
        
        # 본문을 직접 파싱
        if 'body' in response_data:
            body = response_data['body']
            
            if isinstance(body, dict):
                return body
                
            try:
                if hasattr(body, 'read'):
                    # StreamingBody 객체인 경우
                    content = body.read()
                    if isinstance(content, bytes):
                        return json.loads(content.decode('utf-8'))
                    else:
                        return json.loads(content)
                elif isinstance(body, str):
                    return json.loads(body)
                elif isinstance(body, bytes):
                    return json.loads(body.decode('utf-8'))
            except (json.JSONDecodeError, AttributeError) as e:
                logger.warning(f"Failed to parse response body: {e}")
                
        return {}
        
    def _extract_completion_text(self, response_body: Dict[str, Any], model_id: str, is_rag: bool = False) -> str:
        """
        모델별 응답에서 완성 텍스트 추출
        """
        model_id = model_id.lower()
        
        # RAG API 응답 처리
        if is_rag and 'generation' in response_body:
            return response_body['generation']
        
        # Amazon Titan 모델
        if 'amazon.titan' in model_id:
            # Titan V2 모델
            if 'v2' in model_id:
                if 'output' in response_body:
                    return response_body['output']
                    
            # Titan V1 모델
            if 'results' in response_body and isinstance(response_body['results'], list) and len(response_body['results']) > 0:
                return response_body['results'][0].get('outputText', '')
                
        # Anthropic Claude 모델
        elif 'anthropic.claude' in model_id:
            # Claude 3.5 모델
            if '3-5' in model_id or '3.5' in model_id:
                if 'content' in response_body and isinstance(response_body['content'], list) and len(response_body['content']) > 0:
                    content_list = []
                    for content_item in response_body['content']:
                        if content_item.get('type') == 'text':
                            content_list.append(content_item.get('text', ''))
                        elif 'text' in content_item:
                            content_list.append(content_item['text'])
                    return ' '.join(content_list)
                
            # Claude 3 모델
            elif '-3-' in model_id:
                if 'content' in response_body and len(response_body.get('content', [])) > 0:
                    content_list = []
                    for content_item in response_body['content']:
                        if content_item.get('type') == 'text':
                            content_list.append(content_item.get('text', ''))
                        elif 'text' in content_item:
                            content_list.append(content_item['text'])
                    return ' '.join(content_list)
            
            # Claude 1/2 모델
            if 'completion' in response_body:
                return response_body['completion']
                
        # Cohere 모델
        elif 'cohere' in model_id:
            # Command R 모델
            if 'command-r' in model_id:
                if 'text' in response_body:
                    return response_body['text']
                
            # 기존 모델    
            if 'generations' in response_body and isinstance(response_body['generations'], list) and len(response_body['generations']) > 0:
                return response_body['generations'][0].get('text', '')
                
        # AI21 모델
        elif 'ai21' in model_id:
            # Jamba 모델
            if 'jamba' in model_id:
                if 'text' in response_body:
                    return response_body['text']
                    
            # Jurassic 모델    
            if 'completions' in response_body and isinstance(response_body['completions'], list) and len(response_body['completions']) > 0:
                return response_body['completions'][0].get('data', {}).get('text', '')
                
        # Meta Llama 모델
        elif 'meta.llama' in model_id:
            # Llama 3
            if 'llama3' in model_id or 'llama-3' in model_id:
                if 'content' in response_body and isinstance(response_body['content'], list) and len(response_body['content']) > 0:
                    return ' '.join([item.get('text', '') for item in response_body['content'] if 'text' in item])
                
            # Llama 2
            if 'generation' in response_body:
                return response_body['generation']
                
        # Mistral 모델
        elif 'mistral' in model_id:
            # Mistral Large
            if 'large' in model_id:
                if 'outputs' in response_body and isinstance(response_body['outputs'], list) and len(response_body['outputs']) > 0:
                    return response_body['outputs'][0].get('text', '')
                elif 'text' in response_body:
                    return response_body['text']
                    
            # 기존 Mistral 모델
            if 'outputs' in response_body and isinstance(response_body['outputs'], list) and len(response_body['outputs']) > 0:
                return response_body['outputs'][0].get('text', '')
                
        # 일반적인 응답 형식 시도
        if 'text' in response_body:
            return response_body['text']
        elif 'generated_text' in response_body:
            return response_body['generated_text']
        elif 'output' in response_body:
            return response_body['output']
            
        return ""
        
    def _extract_prompt(self, request_body: Dict[str, Any], model_id: str) -> str:
        """
        모델별 요청에서 프롬프트 추출
        """
        model_id = model_id.lower()
        
        # Amazon Titan 모델
        if 'amazon.titan' in model_id:
            # Titan V2 모델
            if 'v2' in model_id:
                return request_body.get('input', '')
                
            # Titan V1 모델
            return request_body.get('inputText', '')
            
        # Anthropic Claude 모델
        elif 'anthropic.claude' in model_id:
            # Claude 3/3.5 모델
            if '-3-' in model_id or '3.5' in model_id or '3-5' in model_id:
                prompt = request_body.get('prompt', '')
                if prompt:
                    return prompt
                    
                # messages 배열 형식 처리
                if 'messages' in request_body and isinstance(request_body['messages'], list):
                    user_messages = []
                    for msg in request_body['messages']:
                        if msg.get('role') == 'user':
                            if isinstance(msg.get('content'), str):
                                user_messages.append(msg.get('content', ''))
                            elif isinstance(msg.get('content'), list):
                                # 멀티모달 컨텐츠 처리
                                for content_part in msg.get('content', []):
                                    if content_part.get('type') == 'text':
                                        user_messages.append(content_part.get('text', ''))
                    return ' '.join(user_messages)
            
            # Claude 1/2 모델
            return request_body.get('prompt', '')
                
        # Cohere 모델
        elif 'cohere' in model_id:
            # Command R 모델
            if 'command-r' in model_id:
                if 'message' in request_body:
                    return request_body['message']
                    
            # 기존 모델
            return request_body.get('prompt', '')
            
        # AI21 모델
        elif 'ai21' in model_id:
            # Jamba 모델
            if 'jamba' in model_id:
                if 'prompt' in request_body:
                    return request_body['prompt']
                    
                # messages 배열 형식 처리
                if 'messages' in request_body and isinstance(request_body['messages'], list):
                    user_messages = [msg.get('content', '') for msg in request_body['messages'] if msg.get('role') == 'user']
                    return ' '.join(user_messages)
                    
            # Jurassic 모델
            return request_body.get('prompt', '')
            
        # Meta Llama 모델
        elif 'meta.llama' in model_id:
            # Llama 3
            if 'llama3' in model_id or 'llama-3' in model_id:
                if 'messages' in request_body and isinstance(request_body['messages'], list):
                    user_messages = [msg.get('content', '') for msg in request_body['messages'] if msg.get('role') == 'user']
                    return ' '.join(user_messages)
                    
            # Llama 2
            return request_body.get('prompt', '')
            
        # Mistral 모델
        elif 'mistral' in model_id:
            # messages 형식
            if 'messages' in request_body and isinstance(request_body['messages'], list):
                user_messages = [msg.get('content', '') for msg in request_body['messages'] if msg.get('role') == 'user']
                return ' '.join(user_messages)
                
            # 기존 형식
            return request_body.get('prompt', '')
            
        # 일반적인 요청 형식 시도
        if 'prompt' in request_body:
            return request_body['prompt']
        elif 'text' in request_body:
            return request_body['text']
        elif 'input' in request_body:
            return request_body['input']
        elif 'inputs' in request_body:
            inputs = request_body['inputs']
            if isinstance(inputs, str):
                return inputs
            elif isinstance(inputs, list) and len(inputs) > 0:
                return str(inputs[0])
                
        return ""
        
    def _add_token_usage(self, attributes: Dict[str, Any], response_body: Dict[str, Any], model_id: str) -> None:
        """
        토큰 사용량 정보 추가
        """
        # Bedrock 공통 토큰 카운트 형식
        if 'usage' in response_body:
            usage = response_body['usage']
            if 'inputTokenCount' in usage:
                attributes['prompt_tokens'] = usage.get('inputTokenCount', 0)
            if 'outputTokenCount' in usage:
                attributes['completion_tokens'] = usage.get('outputTokenCount', 0)
            if 'totalTokenCount' in usage:
                attributes['total_tokens'] = usage.get('totalTokenCount', 0)
            elif 'inputTokenCount' in usage and 'outputTokenCount' in usage:
                # 합계 계산
                attributes['total_tokens'] = usage.get('inputTokenCount', 0) + usage.get('outputTokenCount', 0)
                
        # Anthropic Claude 3 토큰 카운트
        elif 'anthropic.claude-3' in model_id.lower() and 'usage' not in response_body:
            if 'input_tokens' in response_body:
                attributes['prompt_tokens'] = response_body.get('input_tokens', 0)
            if 'output_tokens' in response_body:
                attributes['completion_tokens'] = response_body.get('output_tokens', 0)
            # 합계 계산 (있는 경우에만)
            if 'prompt_tokens' in attributes and 'completion_tokens' in attributes:
                attributes['total_tokens'] = attributes['prompt_tokens'] + attributes['completion_tokens']
                
        # Mistral 토큰 카운트
        elif 'mistral' in model_id.lower() and 'usage' not in response_body:
            if 'input_token_count' in response_body:
                attributes['prompt_tokens'] = response_body.get('input_token_count', 0)
            if 'output_token_count' in response_body:
                attributes['completion_tokens'] = response_body.get('output_token_count', 0)
            if 'prompt_tokens' in attributes and 'completion_tokens' in attributes:
                attributes['total_tokens'] = attributes['prompt_tokens'] + attributes['completion_tokens']
        
    def _add_error_info(self, attributes: Dict[str, Any], error: Any) -> None:
        """
        오류 정보 추가
        """
        # 오류 메시지
        if hasattr(error, 'message'):
            attributes['error_message'] = str(error.message)
        else:
            attributes['error_message'] = str(error)
            
        # 오류 유형
        if hasattr(error, 'type'):
            attributes['error_type'] = error.type
            # 속도 제한 확인
            if error.type == 'RateLimitExceeded':
                attributes['rate_limit_exceeded'] = True
        else:
            attributes['error_type'] = error.__class__.__name__
            
        # 오류 코드
        if hasattr(error, 'code'):
            attributes['error_code'] = error.code
            
        # 상태 코드
        if hasattr(error, 'status'):
            attributes['error_status'] = error.status
            
        # 요청 ID
        if hasattr(error, 'request_id'):
            attributes['error_request_id'] = error.request_id
            
    def _extract_finish_reason(self, response_body: Dict[str, Any], model_id: str) -> Optional[str]:
        """
        모델별 응답에서 완료 이유 추출
        """
        model_id = model_id.lower()
        
        # Amazon Titan 모델
        if 'amazon.titan' in model_id:
            # Titan V2
            if 'v2' in model_id and 'stop_reason' in response_body:
                return response_body['stop_reason']
                
            # Titan V1
            if 'results' in response_body and isinstance(response_body['results'], list) and len(response_body['results']) > 0:
                return response_body['results'][0].get('completionReason')
                
        # Anthropic Claude 모델
        elif 'anthropic.claude' in model_id:
            # Claude 3/3.5
            if '-3-' in model_id or '3.5' in model_id or '3-5' in model_id:
                return response_body.get('stop_reason')
                
            # Claude 1/2
            return response_body.get('stop_reason')
            
        # Cohere 모델
        elif 'cohere' in model_id:
            # Command R
            if 'command-r' in model_id:
                return response_body.get('finish_reason')
                
            # 기존 모델
            if 'generations' in response_body and isinstance(response_body['generations'], list) and len(response_body['generations']) > 0:
                return response_body['generations'][0].get('finish_reason')
                
        # Meta Llama 모델
        elif 'meta.llama' in model_id:
            return response_body.get('stop_reason')
            
        # Mistral 모델
        elif 'mistral' in model_id:
            return response_body.get('stop_reason')
                
        # 일반적인 응답 필드 시도
        if 'finish_reason' in response_body:
            return response_body['finish_reason']
        elif 'stop_reason' in response_body:
            return response_body['stop_reason']
        elif 'completionReason' in response_body:
            return response_body['completionReason']
        elif 'stopReason' in response_body:
            return response_body['stopReason']
            
        return None 