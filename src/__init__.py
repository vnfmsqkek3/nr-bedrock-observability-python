"""New Relic observability for AWS Bedrock."""

# 모듈을 직접 import하면 monitor_bedrock 함수 사용 가능
from .monitor import monitor_bedrock

# 패키지 버전 정보
__version__ = "1.0.1"

# 공개 API
__all__ = ['monitor_bedrock']

# 직접 import를 위한 최상위 레벨 참조는 필요하지 않음
# monitor_bedrock이 이미 .monitor에서 import되어 있으므로
# 아래의 코드 제거

# # 직접 import할 수 있도록 최상위 레벨에 노출
# def monitor_bedrock_wrapper(*args, **kwargs):
#     """
#     monitor_bedrock 함수의 래퍼
#     """
#     return monitor_bedrock(*args, **kwargs)

# # 호환성을 위해 기존 이름도 유지
# monitor_bedrock = monitor_bedrock_wrapper 