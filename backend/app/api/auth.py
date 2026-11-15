"""Demo sign-in. Checks a username and password against config/demo_users.yaml.

This is a prototype control, not security: the accounts are made up, the other endpoints are not protected by it,
and nothing here is connected to the bank's staff directory.
"""
import hmac
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

USERS_FILE = Path(__file__).resolve().parents[3] / 'config' / 'demo_users.yaml'
ROLES = ('CA', 'Credit Head')


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=200)


def auth_router(users_file=USERS_FILE):
    router = APIRouter(prefix='/auth', tags=['auth'])

    @router.post('/login')
    def login(body: LoginRequest):
        try:
            users = (yaml.safe_load(Path(users_file).read_text(encoding='utf-8')) or {}).get('users') or []
        except (OSError, yaml.YAMLError, AttributeError):
            raise HTTPException(503, 'Sign-in accounts are not set up. Check config/demo_users.yaml.')
        wanted = body.username.strip().lower()
        found = None
        for user in users:  # every entry is compared, so timing does not show which usernames exist
            same_name = hmac.compare_digest(str(user.get('username', '')).lower().encode(), wanted.encode())
            same_password = hmac.compare_digest(str(user.get('password', '')).encode(), body.password.encode())
            if same_name and same_password:
                found = user
        if found is None or found.get('role') not in ROLES:
            raise HTTPException(401, 'The username or password is not correct.')
        return {'username': str(found['username']), 'name': str(found.get('name') or found['username']), 'role': found['role']}

    return router
