"""New Relic observability for AWS Bedrock."""

# 모니터링 함수 직접 노출
from .monitor import monitor_bedrock

# 현재 버전을 업데이트하여 일관성 유지
__version__ = "0.3.0"
__all__ = ["monitor_bedrock"]

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