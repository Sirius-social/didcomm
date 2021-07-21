import json

from databases import Database
from fastapi import APIRouter, Request, Depends, HTTPException, Response

import app.db.crud as crud
from app.settings import templates
from app.dependencies import get_db

from .auth import auth_user, login, logout


router = APIRouter()


@router.get("/")
async def admin_panel(request: Request):
    current_user = await auth_user(request)
    if current_user is None:
        current_step = 1
    else:
        current_step = 2

    base_url = request.base_url
    print('==================')
    print(request.base_url)
    print('==================')

    context = {
        'github': 'https://github.com/Sirius-social/didcomm',
        'issues': 'https://github.com/Sirius-social/didcomm/issues',
        'spec': 'https://identity.foundation/didcomm-messaging/spec/',
        'features': 'https://github.com/Sirius-social/didcomm#features',
        'base_url': '/admin',
        'current_user': current_user,
        'current_step': current_step
    }
    response = templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            **context
        }
    )
    return response


@router.post("/create_user", status_code=201)
async def create_user(request: Request, response: Response, db: Database = Depends(get_db)):
    js = await request.json()
    username, password1, password2 = js.get('username'), js.get('password1'), js.get('password2')
    if not username:
        raise HTTPException(status_code=400, detail='Username must be filled')
    if len(username) < 4:
        raise HTTPException(status_code=400, detail='Username length must not be less than 4 symbols')
    if len(password1) < 6:
        raise HTTPException(status_code=400, detail='Password length must not be less than 6 symbols')
    if password1 != password2:
        raise HTTPException(status_code=400, detail='Passwords are not equal')
    user = await crud.load_user(db, username, mute_errors=True)
    if user:
        raise HTTPException(status_code=400, detail=f'User with username "{username}" already exists')
    else:
        user = await crud.create_user(db, username, password1)
        await login(response, user)
