import uuid
from fastapi import APIRouter, Depends, Query
from src.api.dependencies import get_current_user
from src.models.user import User

router = APIRouter()

@router.get("/presigned-url")
async def get_presigned_url(
    filename: str = Query(..., description="要上传的文件名(含扩展名)"),
    content_type: str = Query(..., description="文件的 MIME 类型 (如 image/jpeg)"),
    current_user: User = Depends(get_current_user)
):
    """
    [新增] 获取附件直传的预签名凭证 (当前为 Mock 实现)
    生产环境中，此处应调用阿里云 OSS STS 或 AWS S3 的 generate_presigned_url。
    客户端收到 uploadUrl 后，直接使用 PUT 请求将文件二进制发往云存储对象。
    """
    # 1. 生成基于用户 ID 隔离的安全文件路径
    ext = filename.split(".")[-1] if "." in filename else "bin"
    unique_filename = f"{current_user.id}/{uuid.uuid4().hex}.{ext}"
    
    # 2. 伪造的 Mock URL 供前端调试打通主流程
    # 实际开发中，uploadUrl 是 PUT 请求的目标，downloadUrl 是上传成功后的回显公网地址
    mock_upload_url = f"https://mock-oss.buddycard.com/upload/{unique_filename}?Signature=mock_sig_123"
    mock_download_url = f"https://mock-oss.buddycard.com/files/{unique_filename}"
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "uploadUrl": mock_upload_url,
            "downloadUrl": mock_download_url,
            "expiresIn": 3600 # 凭证有效期(秒)
        }
    }