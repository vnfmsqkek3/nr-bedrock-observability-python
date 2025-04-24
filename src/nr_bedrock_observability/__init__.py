"""
New Relic AWS Bedrock 모니터링 라이브러리
"""

# 모듈을 직접 import하면 monitor_bedrock 함수 사용 가능
from .monitor import monitor_bedrock

# 패키지 버전 정보
__version__ = "0.3.3"

# 공개 API
__all__ = ['monitor_bedrock']

# monitor_bedrock이 이미 .monitor에서 import되어 있으므로
# 래퍼는 필요하지 않음

# def monitor_bedrock_wrapper(*args, **kwargs):
#     """
#     monitor_bedrock 함수의 래퍼
#     """
#     return monitor_bedrock(*args, **kwargs)

# monitor_bedrock = monitor_bedrock_wrapper 