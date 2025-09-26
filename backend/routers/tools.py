from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from ..deps import require_user
from ..web import render


router = APIRouter()


@router.get('/tools/keygen', response_class=HTMLResponse)
async def keygen_page(request: Request, user: dict = Depends(require_user)):
    return render(
        request,
        'keygen.html',
        page_title='钥匙生成',
        page_description='生成 Ed25519 公钥/私钥，并支持复制与下载'
    )


@router.post('/api/tools/keygen')
async def api_keygen(user: dict = Depends(require_user)):
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode('utf-8')

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode('utf-8')

    return JSONResponse({
        'ok': True,
        'data': {
            'private_pem': private_pem,
            'public_pem': public_pem,
        },
    })
